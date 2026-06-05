# 项目目录说明

本文档按目录解释当前 Fridge2Recipe MVP 框架中每一部分的职责。

## 根目录

```text
.
├── .env.example
├── README.md
├── backend/
├── data/
└── docs/
```

- `.env.example`：环境变量模板，复制为 `.env` 后按需修改数据库连接、管理 token、CORS 来源。
- `README.md`：启动、导入、测试命令。
- `backend/`：FastAPI 后端代码。
- `data/`：样例数据和后续种子数据。
- `docs/`：项目说明文档。

## backend

```text
backend/
├── requirements.txt
└── app/
```

- `requirements.txt`：后端依赖，包括 FastAPI、SQLAlchemy、psycopg、OpenSearch client。
- `app/`：后端应用主体。

## backend/app/main.py

FastAPI 入口文件。

主要逻辑：

- 创建 `FastAPI` 实例。
- 根据 `.env` 中的 `CORS_ALLOWED_ORIGINS` 可选启用 CORS。
- 注册 `api/routes.py` 中的所有接口。
- 启动时调用 `init_db()` 自动创建数据库表。

注意：自动建表适合 MVP 和演示，正式项目建议换成 Alembic 迁移。

## backend/app/api/routes.py

接口路由层。只负责接收请求、调用 service/worker、返回响应。

当前接口：

- `GET /health`：健康检查。
- `POST /api/v1/admin/init-db`：手动建表。
- `POST /api/v1/admin/import`：导入 xiachufang JSONL 数据。
- `POST /api/v1/admin/reset-data`：清空已导入数据，便于切换数据集后重新导入。
- `POST /api/v1/admin/reindex`：重建 OpenSearch 索引。
- `POST /api/v1/ingredients/parse`：食材解析与归一。
- `POST /api/v1/search/by-ingredients`：按已有食材搜索菜谱。
- `GET /api/v1/recipes/{recipe_id}`：查询菜谱详情。

管理接口通过 `X-Admin-Token` 保护，对应 `.env` 中的 `ADMIN_TOKEN`。

## backend/app/core/config.py

配置读取层。

主要配置：

- `DATABASE_URL`：FastAPI 连接 PostgreSQL 的地址。
- `OPENSEARCH_URL`：OpenSearch 地址。
- `ADMIN_TOKEN`：管理接口 token。
- `CORS_ALLOWED_ORIGINS`：允许浏览器跨域访问 API 的前端地址。
- `SAMPLE_DATA_PATH`：默认导入的 JSONL 文件路径。

## backend/app/db

数据库连接和初始化。

- `session.py`：创建 SQLAlchemy engine、SessionLocal，并提供 `get_db()` 依赖。
- `init_db.py`：调用 `Base.metadata.create_all()` 创建表。

## backend/app/models/tables.py

数据库表模型。

核心表：

- `Ingredient`：规范食材，如 `番茄`、`鸡蛋`。
- `IngredientAlias`：食材别名，如 `西红柿 -> 番茄`。
- `Recipe`：菜谱主表。
- `RecipeIngredient`：菜谱食材明细，保留 raw 文本和 canonical 食材。
- `RecipeStep`：菜谱步骤。
- `SourceRecord`：原始导入记录快照。
- `SearchEvent`：搜索日志，用于后续评测。

## backend/app/schemas/api.py

接口请求和响应模型。

FastAPI 会用这些 Pydantic 模型完成：

- 请求体校验。
- API 文档生成。
- 响应字段约束。

## backend/app/services/normalizer.py

食材文本归一的基础规则。

当前做了：

- 全半角规范化。
- 去括号说明。
- 拆分输入。
- 识别排除意图。
- 提取前置或后置数量单位，如 `5个圣女果`、`鸡蛋3枚`。
- 去掉包装、成熟度、形态描述，如 `罐头装`、`七成熟`。
- 使用 alias 映射 canonical 食材。

这是搜索质量最关键的模块之一。

## backend/app/services/parser.py

用户输入解析服务。

它调用 `normalizer.py` 和数据库 alias 表，把用户输入变成：

```json
{
  "ingredients": [],
  "excluded_ingredients": [],
  "need_confirmation": []
}
```

搜索接口和单独的解析接口都复用这里的逻辑。

## backend/app/services/ingredients.py

食材词典操作。

主要职责：

- 从数据库加载 alias 映射。
- 创建 canonical 食材。
- 创建 alias。
- 把代码里的默认 alias 种子写入数据库。

## backend/app/services/search.py

搜索和重排服务。

当前版本使用 PostgreSQL 兜底搜索，流程是：

1. 解析用户食材。
2. 读取可搜索菜谱。
3. 排除包含禁用食材的菜谱。
4. 计算 `matched` 和 `missing`。
5. 计算覆盖率、质量分、文本弱相关分。
6. 生成 `bucket` 和 `reason`。
7. 记录 `search_events`。

后续 OpenSearch 接入完成后，可以只替换候选召回部分，保留重排和解释逻辑。

## backend/app/services/opensearch_indexer.py

OpenSearch 索引构建服务。

当前提供：

- `recipes_v1` mapping。
- 从 PostgreSQL 菜谱生成 OpenSearch 文档。
- bulk 写入。
- `recipes_current` alias 切换。

当前搜索接口还没有使用 OpenSearch 做召回。

## backend/app/workers/import_xiachufang.py

下厨房处理后 JSONL 导入器。

导入流程：

1. 逐行读取 JSONL。
2. 计算 payload hash。
3. 写入 `source_records`。
4. 创建或复用食材 canonical 和 alias。
5. 写入 `recipes`。
6. 写入 `recipe_ingredients`。
7. 写入 `recipe_steps`。

同一个 `source_name + source_recipe_id` 重复导入会跳过，方便反复执行。

## data

```text
data/
└── xiachufang/
    ├── recipes.jsonl
    └── recipes_subset.jsonl
```

- `data/xiachufang/recipes_subset.jsonl`：当前默认真实子集数据，一行一条 JSON。
- `data/xiachufang/recipes.jsonl`：小规模测试数据，便于快速验证导入和搜索流程。
- 后续完整数据可以追加到 `recipes_subset.jsonl`，或通过 `.env` 中的 `SAMPLE_DATA_PATH` 指向新的 JSONL 文件。

## 当前请求链路

导入链路：

```text
JSONL -> SourceRecord -> Recipe -> RecipeIngredient -> RecipeStep
                  -> Ingredient / IngredientAlias
```

搜索链路：

```text
用户输入 -> parse_ingredients -> canonical 食材
        -> PostgreSQL 候选菜谱
        -> matched/missing/score/bucket/reason
        -> API 响应
```
