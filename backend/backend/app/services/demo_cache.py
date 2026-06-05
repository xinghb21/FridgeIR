import copy
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.schemas.api import DemoFullFlowRequest, DemoFullFlowResponse, SearchFilters


def _clean_items(items: list[str]) -> list[str]:
    """去掉空白项，并排序，使同一组食材不同输入顺序也能命中演示缓存。"""
    return sorted({item.strip() for item in items if item.strip()})


def _clean_filters(filters: SearchFilters | dict[str, Any]) -> dict[str, Any]:
    """把前端偏好归一成稳定的缓存匹配键。"""
    if isinstance(filters, SearchFilters):
        data = filters.model_dump()
    else:
        data = dict(filters)

    cleaned: dict[str, Any] = {
        "count_seasonings_as_ingredients": bool(data.get("count_seasonings_as_ingredients", False))
    }
    for key in (
        "spice",
        "complexity",
        "diet",
        "serving_size",
        "seasoning_amount",
        "max_minutes",
        "difficulty_lte",
    ):
        value = data.get(key)
        if value is not None:
            cleaned[key] = value

    for key in ("cuisine", "methods"):
        values = data.get(key)
        if values:
            cleaned[key] = _clean_items(list(values))

    if data.get("for_children") is True:
        cleaned["for_children"] = True

    return cleaned


def demo_cache_key(
    items: list[str],
    excluded_items: list[str],
    filters: SearchFilters | dict[str, Any],
) -> dict[str, Any]:
    """生成演示缓存的匹配键。"""
    return {
        "items": _clean_items(items),
        "excluded_items": _clean_items(excluded_items),
        "filters": _clean_filters(filters),
    }


def _load_cases(path: str) -> list[dict[str, Any]]:
    cache_path = Path(path)
    if not cache_path.exists():
        raise FileNotFoundError(path)

    data = json.loads(cache_path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("演示缓存文件缺少 cases 列表")
    return cases


def _dedupe_and_trim_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[int] = set()
    cleaned_items: list[dict[str, Any]] = []
    for item in items:
        recipe_id = item.get("search_result", {}).get("recipe_id")
        if recipe_id in seen:
            continue
        seen.add(recipe_id)
        copied = copy.deepcopy(item)
        copied["rank"] = len(cleaned_items) + 1
        cleaned_items.append(copied)
        if len(cleaned_items) >= limit:
            break
    return cleaned_items


def get_demo_full_flow_response(
    payload: DemoFullFlowRequest,
    settings: Settings,
) -> DemoFullFlowResponse | None:
    """命中固定演示输入时，返回清洗后的全流程缓存结果。"""
    request_key = demo_cache_key(payload.items, payload.excluded_items, payload.filters)

    for case in _load_cases(settings.demo_cache_path):
        case_key = demo_cache_key(
            case.get("match", {}).get("items", []),
            case.get("match", {}).get("excluded_items", []),
            case.get("match", {}).get("filters", {}),
        )
        if case_key != request_key:
            continue

        if not isinstance(case.get("response"), dict):
            raise ValueError(f"演示缓存 case 缺少 response: {case.get('case_id', '<unknown>')}")

        response = copy.deepcopy(case["response"])
        response["items"] = _dedupe_and_trim_items(response.get("items", []), payload.limit)
        response["input"] = {
            "items": list(payload.items),
            "excluded_items": list(payload.excluded_items),
            "filters": payload.filters.model_dump(exclude_none=True),
            "limit": payload.limit,
        }
        response["cache_hit"] = True
        response["case_id"] = case["case_id"]
        response["strict_rerank_hit"] = bool(case.get("strict_rerank_hit", False))
        response["cache_note"] = case.get("response", {}).get("cache_note", "")
        return DemoFullFlowResponse.model_validate(response)

    return None
