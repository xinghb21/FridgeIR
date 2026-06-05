from sqlalchemy.orm import Session

from app.schemas.api import ParsedIngredient, ParseResponse
from app.services.ingredients import load_alias_map
from app.services.normalizer import has_exclude_intent, normalize_ingredient, split_items, strip_exclude_intent


def parse_ingredients(db: Session, items: list[str]) -> ParseResponse:
    """把用户原始输入解析为规范食材。

    输入既可以是 ["番茄", "鸡蛋"] 这样的干净列表，也可以是
    ["西红柿2个 鸡蛋3枚", "不想吃香菜"] 这样的混合文本。当前解析器优先使用
    简单规则和别名表，因为 MVP 的搜索质量更依赖稳定的规范食材，而不是复杂 NLP。
    """
    alias_map = load_alias_map(db)
    parsed: list[ParsedIngredient] = []
    excluded: list[str] = []
    need_confirmation: list[str] = []

    for chunk in split_items(items):
        exclude_intent = has_exclude_intent(chunk)
        normalized = normalize_ingredient(strip_exclude_intent(chunk) if exclude_intent else chunk, alias_map)

        # “不吃香菜”“不要猪肉”这类文本会被转入排除列表。
        # 搜索时会过滤包含这些规范食材名的菜谱。
        if exclude_intent:
            excluded.append(normalized.canonical)
            continue

        parsed.append(
            ParsedIngredient(
                raw=normalized.raw,
                canonical=normalized.canonical,
                quantity=normalized.quantity,
                unit=normalized.unit,
                confidence=normalized.confidence,
            )
        )

        # 低置信度食材仍会返回，但前端可以把它们展示为待用户确认的候选项。
        if normalized.confidence < 0.9:
            need_confirmation.append(normalized.canonical)

    return ParseResponse(ingredients=parsed, excluded_ingredients=excluded, need_confirmation=need_confirmation)
