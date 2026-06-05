# FoodieIR 数据与检索流水线

从食材出发的中文菜谱检索。本目录是 Python 侧的数据处理与检索代码，分两个子包：

```
src/
├── cleaning/              数据清洗 / 提取
│   ├── config.py          字段映射、单位词典、质量阈值
│   ├── ingredient_parser.py  从食材文本提取食材名（"2大片生菜"→生菜）
│   └── clean.py           流式提取 CLI：原始语料 → recipes.jsonl
└── retrieval/             检索
    ├── config.py          同义词词表 + 常备调料词表
    ├── index.py           构建食材倒排索引 → index.pkl
    ├── search.py          食材弹性检索 CLI
    └── subset.py          抽取"种类丰富"的小子集
```

所有命令都在**项目根目录**用 `python3 -m` 运行（这样 `data/` 相对路径才正确）。

## 依赖

```bash
pip install -r requirements.txt   # 仅 pandas
```

## 数据流水线

```bash
# 1. 清洗：原始 XiaChuFang 语料(JSONL,2GB) → data/processed/recipes.jsonl
python3 -m src.cleaning.clean
#   产物：recipes.jsonl(148.7万条) / recipes_preview.csv / quality_report.json

# 2.（可选）抽一个种类丰富的小子集，便于快速迭代
python3 -m src.retrieval.subset --target 2500
#   产物：data/processed/recipes_subset.jsonl

# 3. 建食材倒排索引
python3 -m src.retrieval.index
#   或对子集建索引：
python3 -m src.retrieval.index --input data/processed/recipes_subset.jsonl --out data/index/sub.pkl

# 4. 食材弹性检索
python3 -m src.retrieval.search 西红柿 鸡蛋
python3 -m src.retrieval.search 五花肉 土豆 --max-missing 1 --topk 10
```

## 检索的"弹性"

- **近似召回**：查询词按"精确 + 子串"扩展，"木耳"能命中"黑木耳"。
- **调料默认有**：常备调料（盐/油/生抽…）不计入"还差的食材"。
- **容缺匹配**：`--max-missing N` 允许菜谱还差 N 样非调料食材。

## 数据字段（recipes.jsonl 每行一条）

`id / name / dish / description / ingredients(原文+食材名) / ingredient_names / steps / n_ingredients / n_steps`

> 注：原始语料没有 时间/难度/菜系 字段，故未合成；这些标签由后端服务在导入时另行推断。
