import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_json(base_url: str, path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    """向后端发送 JSON POST 请求，并返回 JSON 响应。"""
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"POST {path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"POST {path} failed: {exc}") from exc


def parse_csv(value: str) -> list[str]:
    """解析逗号分隔参数。"""
    return [item.strip() for item in value.split(",") if item.strip()]


def build_filters(args: argparse.Namespace) -> dict[str, Any]:
    """根据命令行参数构造搜索和生成共用的偏好 filters。"""
    filters: dict[str, Any] = {
        "count_seasonings_as_ingredients": args.count_seasonings,
    }
    if args.spice:
        filters["spice"] = args.spice
    if args.complexity:
        filters["complexity"] = args.complexity
    if args.diet:
        filters["diet"] = args.diet
    if args.for_children:
        filters["for_children"] = True
    if args.serving_size:
        filters["serving_size"] = args.serving_size
    if args.seasoning_amount:
        filters["seasoning_amount"] = args.seasoning_amount
    if args.methods:
        filters["methods"] = parse_csv(args.methods)
    return filters


def run_full_flow(args: argparse.Namespace) -> dict[str, Any]:
    """搜索排序前 N 个菜谱，再为每个菜谱生成智能改良版。"""
    items = parse_csv(args.items)
    excluded_items = parse_csv(args.excluded)
    filters = build_filters(args)

    search_payload = {
        "items": items,
        "excluded_items": excluded_items,
        "filters": filters,
        "page": 1,
        "page_size": args.limit,
    }
    demo_payload = {
        "items": items,
        "excluded_items": excluded_items,
        "filters": filters,
        "limit": args.limit,
    }
    if not args.skip_demo_cache:
        try:
            return post_json(args.base_url, "/api/v1/demo/full-flow", demo_payload, args.timeout)
        except RuntimeError:
            if args.require_demo_cache:
                raise

    search_data = post_json(args.base_url, "/api/v1/search/by-ingredients", search_payload, args.timeout)

    generated_items: list[dict[str, Any]] = []
    for rank, item in enumerate(search_data.get("items", []), start=1):
        recipe_id = item["recipe_id"]
        enhance_payload = {
            "user_items": items,
            "excluded_items": excluded_items,
            "preferences": filters,
        }
        enhanced: dict[str, Any] | None = None
        generation_error: str | None = None
        for attempt in range(args.retries + 1):
            try:
                enhanced = post_json(
                    args.base_url,
                    f"/api/v1/recipes/{recipe_id}/enhance",
                    enhance_payload,
                    args.timeout,
                )
                generation_error = None
                break
            except RuntimeError as exc:
                generation_error = str(exc)
                if attempt >= args.retries:
                    break

        generated_items.append(
            {
                "rank": rank,
                "search_result": item,
                "generated_recipe": enhanced,
                "generation_error": generation_error,
            }
        )

    return {
        "input": {
            "items": items,
            "excluded_items": excluded_items,
            "filters": filters,
            "limit": args.limit,
        },
        "rerank_status": search_data.get("facets", {}).get("rerank"),
        "search_total": search_data.get("total", 0),
        "items": generated_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="搜索排序并生成前 5 个智能菜谱。")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端地址")
    parser.add_argument("--items", required=True, help="已有食材，逗号分隔，例如：西红柿,鸡蛋")
    parser.add_argument("--excluded", default="", help="不需要食材，逗号分隔，例如：香菜")
    parser.add_argument("--limit", type=int, default=5, help="生成前 N 个搜索结果")
    parser.add_argument("--timeout", type=int, default=120, help="单个 HTTP 请求超时时间，秒")
    parser.add_argument("--retries", type=int, default=1, help="单个菜谱生成失败后的重试次数")
    parser.add_argument("--spice", choices=["spicy", "not_spicy"], default=None)
    parser.add_argument("--complexity", choices=["simple", "complex"], default=None)
    parser.add_argument("--diet", choices=["meat", "vegetarian"], default=None)
    parser.add_argument("--for-children", action="store_true", help="偏好适合小孩")
    parser.add_argument("--serving-size", choices=["large", "small"], default=None)
    parser.add_argument("--seasoning-amount", choices=["many", "few"], default=None)
    parser.add_argument("--methods", default="", help="烹饪手法，逗号分隔，例如：炒,蒸,炸")
    parser.add_argument("--count-seasonings", action="store_true", help="把基础调味品计入缺失食材")
    parser.add_argument("--skip-demo-cache", action="store_true", help="跳过演示缓存，强制实时搜索和生成")
    parser.add_argument("--require-demo-cache", action="store_true", help="演示缓存未命中时直接失败，不回退实时流程")

    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be >= 1")

    try:
        result = run_full_flow(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
