import json
import re
from typing import Any

from app.core.config import Settings
from app.models.tables import Recipe
from app.schemas.api import RecipeEnhanceRequest, RecipeEnhanceResponse
from app.services.deepseek_client import DeepSeekError, chat_json, deepseek_available
from app.services.normalizer import is_basic_seasoning, normalize_ingredient
from app.services.preferences import extract_recipe_features, recipe_tags


NON_COUNTING_INGREDIENTS = {"水", "清水", "开水", "温水", "凉水", "纯净水"}
AMOUNT_WORDS = ("适量", "少量", "少许", "若干", "一点点", "一小撮")


def _string_list(value: Any) -> list[str]:
    """把模型输出中的列表字段规整为字符串列表。"""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bucket_for_missing(missing_count: int) -> str:
    """沿用搜索结果的 bucket 语义。"""
    if missing_count == 0:
        return "马上能做"
    if missing_count == 1:
        return "再买 1 样"
    if missing_count <= 3:
        return "还差几样"
    return "灵感参考"


def _compact_ingredient_text(raw: str) -> str:
    """清理生成食材文本中的空格和模糊用量词。"""
    text = re.sub(r"\s+", "", raw.strip())
    text = re.sub(r"^[\-•·\d.、]+", "", text)
    changed = True
    while changed:
        changed = False
        for word in AMOUNT_WORDS:
            if text.startswith(word):
                text = text.removeprefix(word)
                changed = True
            if text.endswith(word):
                text = text.removesuffix(word)
                changed = True
    return text.strip()


def _canonical_name(raw: str) -> str:
    """把生成食材或用户食材归一为可比较名称。"""
    return normalize_ingredient(_compact_ingredient_text(raw)).canonical


def _countable_ingredient(name: str) -> bool:
    """判断是否应计入可用性 bucket 的主要食材。"""
    return bool(name and name not in NON_COUNTING_INGREDIENTS and not is_basic_seasoning(name))


def _dedupe(items: list[str]) -> list[str]:
    """按出现顺序去重。"""
    return list(dict.fromkeys(items))


def _availability_for_generated_recipe(ingredients: list[str], user_items: list[str]) -> tuple[str, str, list[str], list[str]]:
    """根据生成食材和用户已有食材生成可用性标签。"""
    required_names = _dedupe(
        [name for name in (_canonical_name(item) for item in ingredients) if _countable_ingredient(name)]
    )
    user_names = {name for name in (_canonical_name(item) for item in user_items) if name}

    matched = [name for name in required_names if name in user_names]
    missing = [name for name in required_names if name not in user_names]
    bucket = _bucket_for_missing(len(missing))

    if not required_names:
        reason = "生成菜谱没有识别出需要额外准备的主要食材，基础调味品和清水不计入缺失。"
    elif not missing:
        reason = "生成菜谱所需主要食材已被已有食材覆盖，基础调味品和清水不计入缺失。"
    elif len(missing) == 1:
        reason = f"还需要补充 1 个主要食材：{missing[0]}。基础调味品和清水不计入缺失。"
    else:
        preview = "、".join(missing[:5])
        suffix = "等" if len(missing) > 5 else ""
        reason = f"还需要补充 {len(missing)} 个主要食材：{preview}{suffix}。基础调味品和清水不计入缺失。"

    return bucket, reason, matched, missing


def enhance_recipe_with_llm(
    recipe: Recipe,
    request: RecipeEnhanceRequest,
    settings: Settings,
) -> RecipeEnhanceResponse:
    """调用 DeepSeek 生成面向用户偏好的改良菜谱。"""
    if not settings.llm_enhance_enabled:
        raise DeepSeekError("LLM_ENHANCE_ENABLED 未开启")
    if not deepseek_available(settings):
        raise DeepSeekError("未配置 DEEPSEEK_API_KEY")

    original = {
        "title": recipe.title,
        "dish": recipe.dish,
        "description": recipe.description,
        "recipe_tags": recipe_tags(extract_recipe_features(recipe)),
        "ingredients": [
            {
                "raw_text": item.raw_text,
                "canonical_name": item.canonical_name,
                "required": item.required and not is_basic_seasoning(item.canonical_name),
            }
            for item in recipe.ingredients
        ],
        "steps": [step.text for step in recipe.steps],
    }
    user_need = {
        "owned_ingredients": request.user_items,
        "excluded_ingredients": request.excluded_items,
        "preferences": request.preferences.model_dump(exclude_none=True),
    }

    system_prompt = (
        "你是一个中文家庭菜谱改良助手。请基于原始菜谱和用户偏好，生成一个更适合用户的做法。"
        "必须尊重用户不想要的食材，不要包含 excluded_ingredients。"
        "不要声称这是原始来源菜谱；它是智能改良版。步骤要可执行、简洁、有生活感。"
        "返回严格 JSON/json，格式为："
        '{"generated_title":"标题","summary":"一句摘要","ingredients":["食材"],'
        '"steps":["步骤"],"tips":["小贴士"]}。'
    )
    user_prompt = (
        "用户需求：\n"
        f"{json.dumps(user_need, ensure_ascii=False)}\n\n"
        "原始菜谱：\n"
        f"{json.dumps(original, ensure_ascii=False)}"
    )

    response = chat_json(
        settings,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=1800,
    )

    generated_title = str(response.get("generated_title") or recipe.title).strip()
    summary = str(response.get("summary") or "根据你的食材和偏好生成的智能改良做法。").strip()
    ingredients = _string_list(response.get("ingredients"))
    steps = _string_list(response.get("steps"))
    tips = _string_list(response.get("tips"))

    if not ingredients:
        ingredients = [item.raw_text for item in recipe.ingredients]
    if not steps:
        steps = [step.text for step in recipe.steps]

    bucket, bucket_reason, matched, missing = _availability_for_generated_recipe(ingredients, request.user_items)

    return RecipeEnhanceResponse(
        recipe_id=recipe.id,
        source_recipe_id=recipe.source_recipe_id,
        original_title=recipe.title,
        generated_title=generated_title,
        summary=summary,
        bucket=bucket,
        bucket_reason=bucket_reason,
        matched=matched,
        missing=missing,
        ingredients=ingredients,
        steps=steps,
        tips=tips,
        model=settings.deepseek_model,
        disclaimer="该结果由大模型根据原始菜谱和用户偏好生成，适合作为改良建议，请以实际烹饪情况调整。",
    )
