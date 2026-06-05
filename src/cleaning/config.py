"""清洗/提取流水线的配置：字段映射、单位词典、质量阈值。

XiaChuFang recipe_corpus_full.json 的每条记录字段：
  name / dish / description / recipeIngredient / recipeInstructions / author / keywords
该语料没有 时间/难度/菜系 等字段，故这里只保留真实存在、能直接提取的部分。
"""

# 原始字段名 -> 标准字段名。
FIELD_MAP = {
    "name": "name",
    "dish": "dish",
    "description": "description",
    "recipeIngredient": "ingredients",
    "recipeInstructions": "steps",
}

# 计量单位（用于把"用量"从食材文本里切掉，提取纯食材名）。
# 按长度降序匹配，避免"千克"被"克"截断。
UNITS = [
    "千克", "公斤", "毫升", "毫克", "茶匙", "汤匙", "大勺", "小勺", "厘米",
    "克", "斤", "两", "g", "kg", "ml", "L", "l", "升",
    "个", "只", "条", "根", "片", "瓣", "块", "段", "朵", "颗", "粒",
    "张", "把", "勺", "杯", "碗", "盆", "听", "罐", "盒", "包", "袋",
    "份", "滴", "撮", "节", "棵", "枚", "支", "扎", "粬",
]

# 定性用量词（无法量化）。
QUALITATIVE_AMOUNTS = ["适量", "少许", "若干", "随意", "酌量", "按口味", "适当", "些许"]

# 中文数字 -> 阿拉伯数字。
CN_NUMERALS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "半": 0.5,
}

# 质量过滤阈值。
MIN_INGREDIENTS = 2   # 食材少于此数视为无效
MIN_STEPS = 1         # 步骤少于此数视为无效
