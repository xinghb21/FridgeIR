"""从食材文本里提取纯食材名（去掉用量）。

XiaChuFang 语料的食材是"用量在前"：
  "2大片生菜" -> 生菜   "半根黄瓜" -> 黄瓜   "1kg羊肉" -> 羊肉   "适量盐" -> 盐
也兼容"名称在前"（"西红柿 2个" -> 西红柿）与无用量的纯名称。
"""
import html
import re
import unicodedata

from .config import UNITS, QUALITATIVE_AMOUNTS, CN_NUMERALS

# 单位按长度降序，长单位优先（"千克"先于"克"）。
_UNITS_SORTED = sorted(UNITS, key=len, reverse=True)
_UNIT_ALT = "|".join(re.escape(u) for u in _UNITS_SORTED)
_QUAL_ALT = "|".join(re.escape(q) for q in QUALITATIVE_AMOUNTS)

_NUM_CHARS = r"0-9０-９一二两三四五六七八九十半零"
# 行首用量：定性词，或 数字(+大/小/中/整 修饰)+单位
_LEAD_QUAL_RE = re.compile(rf"^\s*(?:{_QUAL_ALT})")
_LEAD_AMOUNT_RE = re.compile(
    rf"^\s*[{_NUM_CHARS}][{_NUM_CHARS}./~\-－—]*\s*[大小中整]?\s*(?:{_UNIT_ALT})"
)
# 行尾用量（名称在前的写法）：数字+单位，或定性词
_END_AMOUNT_RE = re.compile(
    rf"\s*(?:[{_NUM_CHARS}][{_NUM_CHARS}./~\-－—]*\s*(?:{_UNIT_ALT})|(?:{_QUAL_ALT}))$"
)
# 末尾括注（中英文）："(in spring water)" / "（可选）"
_PAREN_RE = re.compile(r"[\(（][^\)）]*[\)）]\s*$")
# 行首连接/噪声符号 与 约数词
_LEAD_PUNCT_RE = re.compile(r"^[\s,，、.。:：;；+\-/~|]+")
_LEAD_APPROX_RE = re.compile(r"^(?:约|大约|大概)")


def normalize_text(s) -> str:
    """解码 HTML 实体、全角转半角、合并空白、去首尾空格。"""
    if not s:
        return ""
    s = html.unescape(str(s))
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("　", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def extract_ingredient_name(raw) -> str:
    """从一条食材文本中提取食材名，提不出有效名则返回空串。"""
    line = normalize_text(raw)
    if not line:
        return ""
    if line[0] in "【「":
        return ""

    line = _PAREN_RE.sub("", line).strip()   # 先去末尾括注

    # 反复剥离行首：定性词 / 约数词 / 数字+单位 / 连接符
    # （应对"120克+-10克牛奶"这类复合写法，循环到不再变化为止）
    prev = None
    while line and line != prev:
        prev = line
        for pat in (_LEAD_QUAL_RE, _LEAD_APPROX_RE, _LEAD_AMOUNT_RE):
            m = pat.match(line)
            if m:
                line = line[m.end():]
        line = _LEAD_PUNCT_RE.sub("", line)

    # 兼容名称在前："西红柿 2个" -> 西红柿
    m = _END_AMOUNT_RE.search(line)
    if m and m.start() > 0:
        line = line[: m.start()].strip()

    return line.strip()


def extract_ingredient_names(raw_ingredients) -> list:
    """把整条菜谱的食材字段（list 或多行字符串）提成 [(原文, 食材名)] 列表。"""
    if raw_ingredients is None:
        return []
    if isinstance(raw_ingredients, str):
        items = re.split(r"[\n;；,，、]+", raw_ingredients)
    elif isinstance(raw_ingredients, (list, tuple)):
        items = list(raw_ingredients)
    else:
        items = [raw_ingredients]

    out = []
    for it in items:
        raw = normalize_text(it)
        name = extract_ingredient_name(it)
        if name:
            out.append((raw, name))
    return out
