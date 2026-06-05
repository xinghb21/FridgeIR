import re
import unicodedata
from dataclasses import dataclass


# 早期阶段先用代码内置的人工别名表。导入器也会把这些别名写入
# ingredient_aliases，后续可以逐步迁移到 CSV 种子或管理后台。
DEFAULT_ALIAS_MAP: dict[str, str] = {
    "西红柿": "番茄",
    "蕃茄": "番茄",
    "番茄": "番茄",
    "圣女果": "小番茄",
    "小番茄": "小番茄",
    "鸡旦": "鸡蛋",
    "鸡蛋": "鸡蛋",
    "蛋": "鸡蛋",
    "七成熟水煮蛋": "鸡蛋",
    "水煮蛋": "鸡蛋",
    "超市罐头装半盒金枪鱼": "金枪鱼",
    "罐头金枪鱼": "金枪鱼",
    "金枪鱼": "金枪鱼",
    "红柿椒": "红椒",
    "红椒": "红椒",
    "紫洋葱": "紫洋葱",
    "洋葱": "洋葱",
    "生菜": "生菜",
    "黄瓜": "黄瓜",
    "红酒醋": "红酒醋",
    "黑胡椒": "胡椒",
    "胡椒": "胡椒",
    "橄榄油": "橄榄油",
}

EXCLUDE_INTENT_WORDS = ("不吃", "不要", "排除", "过敏", "不想吃", "别放", "去掉")
LOOSE_UNIT_WORDS = ("适量", "少许", "若干")

# MVP 阶段默认认为这些是“基础调味品/基础辅料”。
# 它们仍会保留在菜谱详情中，但不计入搜索 missing，也不会影响 bucket。
BASIC_SEASONINGS = {
    "盐",
    "白糖",
    "糖",
    "食用油",
    "油",
    "橄榄油",
    "香油",
    "生抽",
    "老抽",
    "酱油",
    "蚝油",
    "陈醋",
    "米醋",
    "香醋",
    "红酒醋",
    "胡椒",
    "黑胡椒",
    "白胡椒",
    "淀粉",
    "料酒",
}

# 这些词描述包装、形态或状态，而不是食材本身。
# 去掉它们可以把较嘈杂的 xiachufang 食材名映射到规范名。
DESCRIPTOR_WORDS = (
    "超市",
    "罐头装",
    "罐头",
    "七成熟",
    "水煮",
    "新鲜",
    "大片",
)

CHINESE_NUMBER_MAP = {
    "半": 0.5,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

QUANTITY_RE = re.compile(
    r"^(?P<quantity>\d+(?:\.\d+)?|半|一|二|两|三|四|五|六|七|八|九|十)"
    r"(?P<unit>大片|小片|片|个|根|盒|勺|克|g|G|斤|枚|瓣|颗|只|条|碗|杯)?"
)
TRAILING_QUANTITY_RE = re.compile(
    r"^(?P<name>.+?)(?P<quantity>\d+(?:\.\d+)?|半|一|二|两|三|四|五|六|七|八|九|十)"
    r"(?P<unit>大片|小片|片|个|根|盒|勺|克|g|G|斤|枚|瓣|颗|只|条|碗|杯)$"
)
QUANTITY_ONLY_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?|半|一|二|两|三|四|五|六|七|八|九|十)"
    r"(?:大片|小片|片|个|根|盒|勺|克|g|G|斤|枚|瓣|颗|只|条|碗|杯)$"
)


@dataclass(frozen=True)
class NormalizedIngredient:
    """导入器和请求解析器共用的食材归一结果。"""

    raw: str
    candidate: str
    canonical: str
    quantity: float | None
    unit: str | None
    confidence: float


def normalize_text(text: str) -> str:
    """规范文本形态，并移除括号中的补充说明。"""
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"[（(].*?[）)]", "", text)
    text = text.replace("，", ",").replace("、", ",").replace("；", ",").replace(";", ",")
    return text.strip()


def split_items(items: list[str]) -> list[str]:
    """把列表或混合文本输入拆成候选食材片段。"""
    chunks: list[str] = []
    for item in items:
        text = normalize_text(item)
        for chunk in re.split(r"[,，、\n\r\t+\s]+", text):
            chunk = chunk.strip()
            if chunk:
                # 用户输入“鸡蛋 3枚”时，空格拆分会产生只有数量的片段。
                # 这里把数量片段拼回前一个食材。
                if chunks and QUANTITY_ONLY_RE.match(chunk):
                    chunks[-1] = f"{chunks[-1]}{chunk}"
                else:
                    chunks.append(chunk)
    return chunks


def has_exclude_intent(text: str) -> bool:
    """识别“不吃香菜”“不要猪肉”这类排除意图。"""
    return any(word in text for word in EXCLUDE_INTENT_WORDS)


def strip_exclude_intent(text: str) -> str:
    """移除排除意图词，只保留真正的食材名。"""
    cleaned = text.strip()
    for word in EXCLUDE_INTENT_WORDS:
        cleaned = cleaned.replace(word, "")
    return cleaned.strip() or text.strip()


def parse_quantity_and_unit(text: str) -> tuple[float | None, str | None, str]:
    """提取食材文本中的数量和单位，并返回剩余食材文本。"""
    text = text.strip()
    for word in LOOSE_UNIT_WORDS:
        if text.startswith(word):
            return None, word, text.removeprefix(word).strip()

    match = QUANTITY_RE.match(text)
    if not match:
        for word in LOOSE_UNIT_WORDS:
            if text.endswith(word):
                return None, word, text.removesuffix(word).strip()

        trailing_match = TRAILING_QUANTITY_RE.match(text)
        if trailing_match:
            quantity_text = trailing_match.group("quantity")
            unit = trailing_match.group("unit")
            if quantity_text in CHINESE_NUMBER_MAP:
                quantity = CHINESE_NUMBER_MAP[quantity_text]
            else:
                quantity = float(quantity_text)
            return quantity, unit, trailing_match.group("name").strip()

        return None, None, text

    quantity_text = match.group("quantity")
    unit = match.group("unit")
    if quantity_text in CHINESE_NUMBER_MAP:
        quantity = CHINESE_NUMBER_MAP[quantity_text]
    else:
        quantity = float(quantity_text)

    rest = text[match.end() :].strip()
    return quantity, unit, rest


def strip_descriptors(text: str) -> str:
    """移除会让食材名过于具体的常见描述词。"""
    text = text.strip()
    for word in DESCRIPTOR_WORDS:
        text = text.replace(word, "")
    text = re.sub(r"^(适量|少许|若干)", "", text)
    text = re.sub(r"^(?:半|\d+(?:\.\d+)?)(?:大片|小片|片|个|根|盒|勺|克|g|G|斤|枚|瓣|颗|只|条|碗|杯)?", "", text)
    return text.strip()


def normalize_ingredient(raw: str, alias_map: dict[str, str] | None = None) -> NormalizedIngredient:
    """把单条原始食材文本归一为规范食材名。"""
    alias_map = alias_map or {}
    cleaned = normalize_text(raw)
    quantity, unit, rest = parse_quantity_and_unit(cleaned)
    candidate = strip_descriptors(rest or cleaned)
    candidate = candidate or cleaned

    canonical = alias_map.get(candidate) or DEFAULT_ALIAS_MAP.get(candidate) or candidate
    confidence = 1.0 if canonical != candidate or candidate in DEFAULT_ALIAS_MAP else 0.85

    return NormalizedIngredient(
        raw=raw,
        candidate=candidate,
        canonical=canonical,
        quantity=quantity,
        unit=unit,
        confidence=confidence,
    )


def is_basic_seasoning(canonical_name: str | None) -> bool:
    """判断规范食材名是否属于默认不计缺失的基础调味品。"""
    return bool(canonical_name and canonical_name in BASIC_SEASONINGS)
