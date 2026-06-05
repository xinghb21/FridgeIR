from dataclasses import dataclass

from app.models.tables import Recipe
from app.schemas.api import SearchFilters
from app.services.normalizer import is_basic_seasoning


SPICY_KEYWORDS = (
    "辣",
    "麻辣",
    "香辣",
    "酸辣",
    "小米椒",
    "辣椒",
    "泡椒",
    "剁椒",
    "郫县",
    "豆瓣酱",
    "花椒",
    "麻椒",
)
MEAT_SEAFOOD_KEYWORDS = (
    "猪",
    "牛",
    "羊",
    "肉",
    "排骨",
    "鸡肉",
    "鸡腿",
    "鸡翅",
    "鸡胸",
    "鸡爪",
    "鸡块",
    "鸡丁",
    "鸡丝",
    "鸡排",
    "鸭肉",
    "鸭腿",
    "鹅肉",
    "火腿",
    "培根",
    "腊肉",
    "香肠",
    "鱼",
    "虾",
    "蟹",
    "贝",
    "蛤",
    "蚬",
    "金枪鱼",
    "三文鱼",
    "鳕鱼",
)
CHILD_UNFRIENDLY_KEYWORDS = ("酒", "料酒", "白酒", "黄酒", "咖啡")
LARGE_SERVING_KEYWORDS = ("大份", "一锅", "全家", "家庭", "聚餐", "多人", "宴客")
SMALL_SERVING_KEYWORDS = ("小份", "一人食", "单人", "宝宝", "儿童", "迷你")
COOKING_METHODS = ("炒", "蒸", "煎", "拌", "炖", "炸")


@dataclass(frozen=True)
class RecipePreferenceFeatures:
    is_spicy: bool
    has_meat_or_seafood: bool
    step_count: int
    is_simple: bool
    seasoning_count: int
    seasoning_ratio: float
    inferred_serving_size: str
    methods: set[str]
    is_child_friendly: bool


def recipe_text(recipe: Recipe) -> str:
    ingredient_text = " ".join(
        f"{item.raw_text or ''} {item.canonical_name or ''}" for item in recipe.ingredients
    )
    step_text = " ".join(step.text or "" for step in recipe.steps)
    return f"{recipe.title or ''} {recipe.dish or ''} {recipe.description or ''} {ingredient_text} {step_text}"


def has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def infer_serving_size(text: str, ingredient_count: int) -> str:
    if has_any(text, LARGE_SERVING_KEYWORDS) or ingredient_count >= 10:
        return "large"
    if has_any(text, SMALL_SERVING_KEYWORDS) or ingredient_count <= 5:
        return "small"
    return "normal"


def extract_recipe_features(recipe: Recipe) -> RecipePreferenceFeatures:
    text = recipe_text(recipe)
    ingredient_count = len(recipe.ingredients)
    seasoning_count = sum(1 for item in recipe.ingredients if is_basic_seasoning(item.canonical_name))
    step_count = len(recipe.steps)
    is_spicy = has_any(text, SPICY_KEYWORDS)
    has_meat_or_seafood = has_any(text, MEAT_SEAFOOD_KEYWORDS)
    methods = {method for method in COOKING_METHODS if method in text}
    seasoning_ratio = seasoning_count / ingredient_count if ingredient_count else 0.0
    is_child_friendly = not is_spicy and not has_any(text, CHILD_UNFRIENDLY_KEYWORDS) and step_count <= 8

    return RecipePreferenceFeatures(
        is_spicy=is_spicy,
        has_meat_or_seafood=has_meat_or_seafood,
        step_count=step_count,
        is_simple=step_count <= 5,
        seasoning_count=seasoning_count,
        seasoning_ratio=seasoning_ratio,
        inferred_serving_size=infer_serving_size(text, ingredient_count),
        methods=methods,
        is_child_friendly=is_child_friendly,
    )


def recipe_tags(features: RecipePreferenceFeatures) -> list[str]:
    tags = [
        "辣" if features.is_spicy else "不辣",
        "荤菜" if features.has_meat_or_seafood else "素菜",
        "简单" if features.is_simple else "复杂",
        "调料多" if has_many_seasonings(features) else "调料少",
    ]
    if features.inferred_serving_size == "large":
        tags.append("分量多")
    elif features.inferred_serving_size == "small":
        tags.append("分量少")
    if features.is_child_friendly:
        tags.append("适合小孩")
    tags.extend(sorted(features.methods))
    return tags


def add_preference(
    selected: bool,
    label: str,
    match_score: float,
    mismatch_score: float,
    matches: list[str],
    mismatches: list[str],
) -> float:
    if selected:
        matches.append(label)
        return match_score
    mismatches.append(label)
    return mismatch_score


def score_preferences(
    features: RecipePreferenceFeatures, filters: SearchFilters
) -> tuple[float, list[str], list[str]]:
    score = 0.0
    matches: list[str] = []
    mismatches: list[str] = []

    if filters.diet == "vegetarian":
        score += add_preference(not features.has_meat_or_seafood, "素菜", 0.12, -0.18, matches, mismatches)
    elif filters.diet == "meat":
        score += add_preference(features.has_meat_or_seafood, "荤菜", 0.12, -0.10, matches, mismatches)

    if filters.spice == "not_spicy":
        score += add_preference(not features.is_spicy, "不辣", 0.10, -0.16, matches, mismatches)
    elif filters.spice == "spicy":
        score += add_preference(features.is_spicy, "辣", 0.10, -0.08, matches, mismatches)

    if filters.complexity == "simple":
        score += add_preference(features.is_simple, "简单", 0.06, -0.06, matches, mismatches)
    elif filters.complexity == "complex":
        score += add_preference(not features.is_simple, "复杂", 0.06, -0.06, matches, mismatches)

    if filters.for_children is True:
        score += add_preference(features.is_child_friendly, "适合小孩", 0.06, -0.10, matches, mismatches)

    if filters.serving_size == "large":
        score += add_preference(features.inferred_serving_size == "large", "分量多", 0.04, -0.03, matches, mismatches)
    elif filters.serving_size == "small":
        score += add_preference(features.inferred_serving_size == "small", "分量少", 0.04, -0.03, matches, mismatches)

    many_seasonings = has_many_seasonings(features)
    if filters.seasoning_amount == "many":
        score += add_preference(many_seasonings, "调料多", 0.04, -0.03, matches, mismatches)
    elif filters.seasoning_amount == "few":
        score += add_preference(not many_seasonings, "调料少", 0.04, -0.03, matches, mismatches)

    selected_methods = set(filters.methods)
    if selected_methods:
        matched_methods = sorted(selected_methods & features.methods)
        if matched_methods:
            matches.extend(matched_methods)
            score += min(0.10, 0.04 * len(matched_methods))
        else:
            mismatches.extend(sorted(selected_methods))
            score -= 0.04

    return round(score, 3), matches, mismatches


def has_many_seasonings(features: RecipePreferenceFeatures) -> bool:
    """判断调味料是否偏多，避免少量食材菜谱因比例高被误判。"""
    return features.seasoning_count >= 4 or (
        features.seasoning_count >= 3 and features.seasoning_ratio >= 0.6
    )
