from collections import Counter
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.tables import Recipe, SearchEvent
from app.schemas.api import ParseResponse, SearchFilters, SearchItem, SearchRequest, SearchResponse
from app.services.parser import parse_ingredients
from app.services.normalizer import is_basic_seasoning
from app.services.preferences import extract_recipe_features, recipe_tags, score_preferences
from app.services.reranker import rerank_search_items


def bucket_for_missing(missing_count: int) -> str:
    """把缺少食材数量映射为面向用户的结果分组。"""
    if missing_count == 0:
        return "马上能做"
    if missing_count == 1:
        return "再买 1 样"
    if missing_count <= 3:
        return "还差几样"
    return "灵感参考"


def reason_text(
    matched: list[str],
    missing: list[str],
    recipe: Recipe,
    preference_matches: list[str],
) -> str:
    """根据透明排序特征生成推荐原因文案。"""
    parts = [f"命中 {len(matched)} 个已有食材"]
    if missing:
        parts.append(f"缺少 {len(missing)} 个食材")
    else:
        parts.append("必需食材已覆盖")
    if preference_matches:
        parts.append(f"偏好匹配：{'、'.join(preference_matches[:4])}")
    return "，".join(parts)


def lexical_score(recipe: Recipe, query_names: set[str]) -> float:
    """当查询食材出现在标题或 dish 文本中时给少量加分。

    MVP 排序以结构化食材为主。这个文本分只作为弱平分项，
    不是主要召回或排序信号。
    """
    text = f"{recipe.title or ''} {recipe.dish or ''} {recipe.description or ''}"
    if not query_names:
        return 0.0
    hits = sum(1 for name in query_names if name and name in text)
    return min(hits / len(query_names), 1.0)


def load_candidates(db: Session, filters: SearchFilters) -> list[Recipe]:
    """从 PostgreSQL 加载可搜索菜谱。

    这是计划里提到的临时 PostgreSQL 兜底方案。在 OpenSearch 召回完全接入前，
    它能保证端到端 API 先跑通。`selectinload` 可以避免读取食材和步骤时
    对每道菜谱额外查询一次。
    """
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
        .where(Recipe.rights_status == "clear", Recipe.takedown_status == "active")
    )

    # 当前 xiachufang 样例数据没有时间、难度、菜系。
    # 对 NULL 值保持可搜索，保证早期不完整数据也能工作。
    if filters.max_minutes is not None:
        stmt = stmt.where((Recipe.total_minutes == None) | (Recipe.total_minutes <= filters.max_minutes))  # noqa: E711
    if filters.difficulty_lte is not None:
        stmt = stmt.where((Recipe.difficulty == None) | (Recipe.difficulty <= filters.difficulty_lte))  # noqa: E711
    if filters.cuisine:
        stmt = stmt.where(Recipe.cuisine.in_(filters.cuisine))

    return list(db.scalars(stmt).all())


def search_by_ingredients(db: Session, request: SearchRequest) -> SearchResponse:
    """按用户已有食材搜索菜谱。

    端到端流程：
    1. 解析并归一用户输入。
    2. 加载可搜索菜谱。
    3. 移除包含排除食材的菜谱。
    4. 计算命中/缺失食材和排序特征。
    5. 保存轻量搜索事件，供后续评测使用。
    """
    started = perf_counter()
    settings = get_settings()

    # 普通食材和排除食材走同一套归一路径，
    # 这样“西红柿”和“番茄”在任何位置都会变成同一个规范食材。
    parsed = parse_ingredients(db, request.items)
    parsed_excluded = parse_ingredients(db, request.excluded_items)

    user_names = {item.canonical for item in parsed.ingredients}
    excluded_names = (
        set(parsed.excluded_ingredients)
        | set(parsed_excluded.excluded_ingredients)
        | {item.canonical for item in parsed_excluded.ingredients}
    )
    all_excluded = sorted(excluded_names)
    parsed = ParseResponse(
        ingredients=parsed.ingredients,
        excluded_ingredients=all_excluded,
        need_confirmation=parsed.need_confirmation + parsed_excluded.need_confirmation,
    )

    scored: list[SearchItem] = []
    for recipe in load_candidates(db, request.filters):
        include_seasonings = request.filters.count_seasonings_as_ingredients
        recipe_names = [
            item.canonical_name
            for item in recipe.ingredients
            if item.canonical_name
            and (item.required or include_seasonings)
            and (include_seasonings or not is_basic_seasoning(item.canonical_name))
        ]
        recipe_name_set = set(recipe_names)
        all_recipe_name_set = {
            item.canonical_name
            for item in recipe.ingredients
            if item.canonical_name
        }

        # 硬过滤：如果菜谱包含用户排除的食材，就完全不展示。
        if excluded_names & all_recipe_name_set:
            continue

        matched = sorted(user_names & recipe_name_set)
        missing = [name for name in recipe_names if name not in user_names]
        unique_missing = list(dict.fromkeys(missing))

        coverage_user = len(matched) / len(user_names) if user_names else 0.0
        coverage_recipe = len(matched) / len(recipe_name_set) if recipe_name_set else 0.0
        missing_penalty = min(len(set(missing)), 5) / 5

        # 简化版 MVP 排序分。当前 xiachufang 样例数据缺少总时长、
        # 难度和热度，所以先用覆盖率、质量分和弱文本分组合。
        # 后续可以用黄金查询集继续调权重。
        ingredient_score = (
            0.45 * coverage_recipe
            + 0.25 * coverage_user
            + 0.20 * float(recipe.quality_score)
            + 0.10 * lexical_score(recipe, user_names)
            - 0.20 * missing_penalty
        )
        features = extract_recipe_features(recipe)
        preference_score, preference_matches, preference_mismatches = score_preferences(features, request.filters)
        score = ingredient_score + preference_score

        # 零食材重合的菜谱保留为灵感参考，但给少量惩罚，
        # 让真正命中的结果排在前面。
        if not matched and user_names:
            score -= 0.15

        scored.append(
            SearchItem(
                recipe_id=recipe.id,
                source_recipe_id=recipe.source_recipe_id,
                title=recipe.title,
                dish=recipe.dish,
                quality_score=float(recipe.quality_score),
                matched=matched,
                missing=unique_missing,
                bucket=bucket_for_missing(len(set(missing))),
                score=round(score, 3),
                reason=reason_text(matched, unique_missing, recipe, preference_matches),
                recipe_tags=recipe_tags(features),
                preference_matches=preference_matches,
                preference_mismatches=preference_mismatches,
                preference_score=preference_score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    scored, rerank_status = rerank_search_items(scored, request, settings)
    total = len(scored)
    start = (request.page - 1) * request.page_size
    end = start + request.page_size

    bucket_counts = Counter(item.bucket for item in scored)
    db.add(
        SearchEvent(
            query_text=",".join(request.items),
            parsed_ingredients=parsed.model_dump(),
            filters=request.filters.model_dump(),
            result_count=total,
            latency_ms=int((perf_counter() - started) * 1000),
        )
    )
    db.commit()

    return SearchResponse(
        parsed=parsed,
        total=total,
        items=scored[start:end],
        facets={
            "bucket": [{"name": name, "count": count} for name, count in bucket_counts.items()],
            "rerank": rerank_status,
        },
    )
