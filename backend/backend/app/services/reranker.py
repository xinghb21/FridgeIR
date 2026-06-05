import json
from typing import Any

from app.core.config import Settings
from app.schemas.api import SearchItem, SearchRequest
from app.services.deepseek_client import DeepSeekError, chat_json, deepseek_available


def _call_rerank_model(
    settings: Settings,
    *,
    system_prompt: str,
    user_prompt: str,
    use_response_format: bool,
) -> dict:
    """调用 rerank 模型，并允许 JSON mode / 普通文本模式复用同一套参数。"""
    return chat_json(
        settings,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=900,
        timeout_seconds=max(settings.deepseek_timeout_seconds, 60),
        use_response_format=use_response_format,
    )


def _parse_rerank_map(response: dict[str, Any]) -> dict[int, tuple[float, str | None]]:
    """把批量精排响应规整为 recipe_id -> 模型分数。"""
    rerank_map: dict[int, tuple[float, str | None]] = {}
    raw_items = response.get("items", [])
    if not isinstance(raw_items, list):
        return rerank_map

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        try:
            recipe_id = int(raw["recipe_id"])
            score = max(0.0, min(1.0, float(raw["rerank_score"])))
        except (KeyError, TypeError, ValueError):
            continue
        reason = raw.get("rerank_reason")
        if not isinstance(reason, str):
            reason = None
        rerank_map[recipe_id] = (score, reason)
    return rerank_map


def _call_single_candidate_rerank(
    settings: Settings,
    *,
    user_need: dict,
    candidate: dict,
) -> tuple[float, str | None]:
    """批量 JSON 失败时，对单个候选使用更短提示词做兜底精排。"""
    system_prompt = (
        "你是中文菜谱搜索精排器。只输出 JSON 对象，不要 Markdown，不要解释。"
        "食材匹配最重要，其次考虑荤素和辣不辣，再考虑是否适合小孩等偏好。"
        "输出格式固定为："
        '{"rerank_score":0.0,"rerank_reason":"一句中文原因"}。'
    )
    user_prompt = (
        "请只返回 JSON 对象，不要 Markdown，不要解释。\n"
        "输出格式："
        '{"rerank_score":0.0,"rerank_reason":"一句中文原因"}。\n'
        "rerank_score 是 0 到 1 的数字。\n\n"
        "用户需求 JSON：\n"
        f"{json.dumps(user_need, ensure_ascii=False)}\n\n"
        "候选菜谱 JSON：\n"
        f"{json.dumps(candidate, ensure_ascii=False)}"
    )
    response = chat_json(
        settings,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=300,
        timeout_seconds=max(settings.deepseek_timeout_seconds, 60),
        use_response_format=False,
    )
    if isinstance(response.get("items"), list) and response["items"]:
        first_item = response["items"][0]
        if isinstance(first_item, dict):
            response = first_item
    try:
        score = max(0.0, min(1.0, float(response["rerank_score"])))
    except (KeyError, TypeError, ValueError) as exc:
        raise DeepSeekError("单条精排响应缺少可用 rerank_score") from exc
    reason = response.get("rerank_reason")
    if not isinstance(reason, str):
        reason = None
    return score, reason


def rerank_search_items(
    items: list[SearchItem],
    request: SearchRequest,
    settings: Settings,
) -> tuple[list[SearchItem], dict]:
    """使用 DeepSeek 对规则排序后的前若干结果做轻量精排。

    规则排序仍是主排序，模型只在候选集合中补充语义理解，避免把不相关菜谱
    因为生成式判断拉到最前面。
    """
    status = {
        "enabled": settings.rerank_enabled,
        "configured": deepseek_available(settings),
        "attempted": False,
        "applied": False,
        "candidate_count": 0,
        "applied_count": 0,
        "model": settings.deepseek_model,
        "fallback": None,
        "warning": None,
        "error": None,
    }
    if not settings.rerank_enabled:
        status["error"] = "RERANK_ENABLED 未开启"
        return items, status
    if not deepseek_available(settings):
        status["error"] = "未配置 DEEPSEEK_API_KEY"
        return items, status
    if not items:
        status["error"] = "没有可精排候选"
        return items, status

    top_k = max(1, min(settings.rerank_top_k, len(items)))
    candidates = items[:top_k]
    status["candidate_count"] = len(candidates)
    candidate_payload = [
        {
            "recipe_id": item.recipe_id,
            "title": item.title,
            "dish": item.dish,
            "bucket": item.bucket,
            "matched": item.matched,
            "missing": item.missing,
            "tags": item.recipe_tags,
            "pref": item.preference_matches,
            "score": item.score,
        }
        for item in candidates
    ]
    user_need = {
        "owned_ingredients": request.items,
        "excluded_ingredients": request.excluded_items,
        "filters": request.filters.model_dump(exclude_none=True),
    }

    system_prompt = (
        "你是中文菜谱搜索精排器。只输出 JSON 对象，不要 Markdown，不要解释，不要前后缀。"
        "必须保留候选 recipe_id，不能新增候选。食材匹配最重要，其次考虑荤素和辣不辣，"
        "再考虑是否适合小孩等偏好。JSON 格式："
        '{"items":[{"recipe_id":1,"rerank_score":0.0,"rerank_reason":"一句中文原因"}]}。'
        "rerank_score 是 0 到 1 的数字。"
    )
    user_prompt = (
        "请只返回 JSON 对象，不要输出自然语言说明。\n"
        "用户需求 JSON：\n"
        f"{json.dumps(user_need, ensure_ascii=False)}\n\n"
        "候选菜谱 JSON：\n"
        f"{json.dumps(candidate_payload, ensure_ascii=False)}"
    )

    batch_error: str | None = None
    response: dict[str, Any] | None = None
    rerank_map: dict[int, tuple[float, str | None]] = {}

    try:
        status["attempted"] = True
        response = _call_rerank_model(
            settings,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_response_format=True,
        )
    except DeepSeekError as exc:
        first_error = str(exc)
        try:
            response = _call_rerank_model(
                settings,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                use_response_format=False,
            )
        except DeepSeekError as retry_exc:
            batch_error = f"{first_error}; 重试失败: {retry_exc}"

    if response is not None:
        rerank_map = _parse_rerank_map(response)
        if not rerank_map:
            batch_error = "模型未返回可用 rerank 结果"

    if not rerank_map:
        status["fallback"] = "single_candidate"
        single_errors: list[str] = []
        for candidate in candidate_payload:
            try:
                recipe_id = int(candidate["recipe_id"])
                rerank_map[recipe_id] = _call_single_candidate_rerank(
                    settings,
                    user_need=user_need,
                    candidate=candidate,
                )
            except (DeepSeekError, KeyError, TypeError, ValueError) as exc:
                single_errors.append(f"{candidate.get('recipe_id')}: {exc}")

        if not rerank_map:
            retry_summary = "；".join(single_errors[:3]) or "无可用单条结果"
            status["error"] = f"{batch_error or '批量精排失败'}；逐条兜底失败：{retry_summary}"
            print(f"DeepSeek rerank skipped: {status['error']}")
            return items, status
        status["warning"] = batch_error

    applied_count = 0
    for item in candidates:
        rerank = rerank_map.get(item.recipe_id)
        if rerank is None:
            continue
        rerank_score, rerank_reason = rerank
        item.rerank_score = round(rerank_score, 3)
        item.rerank_reason = rerank_reason
        item.score = round(float(item.score) + settings.rerank_weight * rerank_score, 3)
        applied_count += 1
        if rerank_reason:
            item.reason = f"{item.reason}，模型判断：{rerank_reason}"

    status["applied"] = applied_count > 0
    status["applied_count"] = applied_count
    if applied_count == 0:
        status["error"] = "模型返回的 recipe_id 未命中候选"
    return sorted(items, key=lambda item: item.score, reverse=True), status
