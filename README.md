# FridgeIR / Fridge2Recipe

从食材出发的中文菜谱搜索引擎（信息检索课程项目）。输入手头食材 + 约束（不要的食材、辣度、荤素、难度、分量、调料、烹饪手法、是否给小孩…），返回"马上能做 / 再买一样 / 还差几样 / 灵感参考"的菜谱，并可一键生成 AI 改良做法。

## 目录结构

```
FridgeIR/
├── src/          数据清洗 + 检索流水线（Python，详见 src/README.md）
│   ├── cleaning/   原始语料 → 结构化 recipes.jsonl
│   └── retrieval/  食材倒排索引 + 弹性检索 + 子集抽取
├── data/         数据（单一来源）
│   ├── raw/        原始 XiaChuFang 语料（2GB，git 忽略）
│   ├── processed/  recipes.jsonl(全量148.7万) / recipes_subset.jsonl(2500) / 报告
│   └── index/      食材倒排索引 index.pkl
├── backend/      后端服务 Fridge2Recipe（克隆仓库，独立 git）
│   ├── backend/app/   FastAPI（PostgreSQL + 可选 OpenSearch / DeepSeek）
│   └── data/xiachufang/  → 软链到 ../../../data/processed/（不重复存数据）
└── frontend/     前端 Vite + React + TS（对接后端接口）
```

数据只存一份在 `data/processed/`，后端通过软链引用，不重复占空间。

## 跑起来

本机已用 venv（非 conda）跑通；PostgreSQL 里已建库 `fridge2recipe` 并导入 2500 条数据（持久化，重启无需重导）。

```bash
# 1) 后端（在 backend/ 仓库根目录运行）
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r backend/requirements.txt   # 仅首次
PYTHONPATH="$PWD/backend" ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
#   .env 已配好（DATABASE_URL 指向本机 PostgreSQL）。
#   首次导入数据（已做过一次，DB 里已有数据，可跳过）：
#   curl -X POST http://127.0.0.1:8000/api/v1/admin/import -H "X-Admin-Token: dev-token" -H "Content-Type: application/json" -d '{}'

# 2) 前端
cd frontend && npm install && npm run dev    # http://localhost:5173
```

前端通过 Vite 代理 `/api → 127.0.0.1:8000`，无需配置后端 CORS。
开启 AI 改良做法需在 `backend/.env` 填 `DEEPSEEK_API_KEY`（已设 `LLM_ENHANCE_ENABLED=true`）。

## 接口对接情况

前端已覆盖后端全部面向用户的能力：食材/排除项/全部偏好筛选、分页、解析回显、bucket 标签、
匹配/缺失食材、推荐原因、（可选）重排说明、菜谱详情、以及 **AI 改良做法**
（`POST /api/v1/recipes/{id}/enhance`，需后端开启 `LLM_ENHANCE_ENABLED` + DeepSeek key）。

## 数据流水线

见 [src/README.md](src/README.md)。简要：
`python3 -m src.cleaning.clean` → `python3 -m src.retrieval.subset` → `python3 -m src.retrieval.index` → `python3 -m src.retrieval.search 西红柿 鸡蛋`
