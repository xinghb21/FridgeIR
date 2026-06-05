# Fridge2Recipe Search MVP

这是一个基于 `xiachufang` 处理后 JSONL 数据的反向食材搜索引擎基础框架。

当前版本采用非 Docker 运行方式：

- FastAPI 后端直接运行在 Python 虚拟环境中
- PostgreSQL 作为主数据库，需要在本机或服务器系统中安装
- OpenSearch 仅用于可选的索引重建接口，当前搜索主链路可只依赖 PostgreSQL 跑通
- 支持 `xiachufang` JSONL 真实子集数据导入
- 支持食材解析、数量单位提取、alias 归一
- 支持 PostgreSQL 兜底搜索、matched / missing / bucket / reason 解释
- 支持可选 DeepSeek 大模型 rerank 精排和智能改良版菜谱生成

项目目录和关键代码说明见 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。
远程服务器运行后端的完整步骤见 [docs/SERVER_RUNBOOK.md](docs/SERVER_RUNBOOK.md)。
前端接口和后端运行结果示例见 [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md)。

当前默认数据位于 `data/xiachufang/recipes_subset.jsonl`，包含 2500 条真实子集菜谱。`data/xiachufang/recipes.jsonl` 保留为 12 条小规模测试数据。

## 需要安装的工具

Windows 本机推荐使用 WSL 运行后端。本地或服务器都需要：

- WSL2 + Ubuntu，Windows 本机推荐
- Anaconda 或 Miniconda
- PostgreSQL 16，PostgreSQL 14+ 通常也可运行当前 MVP
- Git

可选：

- OpenSearch 2.x，仅在调用 `/api/v1/admin/reindex` 时需要
- DeepSeek API Key，仅在开启 rerank 或智能改良版菜谱生成时需要

Conda 环境文件见 [environment.yml](environment.yml)。
如果不用 Conda，也可以参考 [backend/requirements.txt](backend/requirements.txt) 通过 pip 安装。

## Windows + WSL 本地非 Docker 启动

在 Windows PowerShell 中确认 WSL 可用：

```powershell
wsl --status
```

如果尚未安装 WSL，可在管理员 PowerShell 中安装 Ubuntu：

```powershell
wsl --install -d Ubuntu-24.04
```

进入 WSL Ubuntu 后，安装系统依赖：

```bash
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

确认 WSL 内 Conda 是否可用：

```bash
conda --version
```

如果 WSL 中提示 `conda: command not found`，说明 Windows 里的 Anaconda 没有进入 WSL 环境。WSL 是独立的 Linux 系统，需要在 WSL 内单独安装 Anaconda 或 Miniconda。推荐安装轻量的 Miniconda：

```bash
cd /tmp
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version
```

安装过程中建议接受默认安装路径，并在提示是否初始化 shell 时选择 `yes`。

进入项目目录。你可以直接使用 Windows 目录：

```bash
cd /mnt/d/Fridge2Recipe
```

如果追求更好的 WSL 文件性能，也可以把项目放到 WSL home 目录，例如 `~/Fridge2Recipe`。

启动 PostgreSQL：

```bash
sudo service postgresql start
```

创建数据库：

```bash
sudo -u postgres psql
```

在 PostgreSQL 命令行中执行：

```sql
CREATE USER fridge WITH PASSWORD 'fridge_dev_password';
CREATE DATABASE fridge2recipe OWNER fridge;
\q
```

创建 Conda 环境：

```bash
conda env create -f environment.yml
conda activate fridge2recipe
```

如果访问 `repo.anaconda.com` 超时，可以先切换 Conda 镜像：

```bash
conda config --set show_channel_urls yes
conda config --remove-key channels 2>/dev/null || true
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
conda clean -i
conda env create -f environment.yml
conda activate fridge2recipe
```

复制环境变量文件：

```bash
cp .env.example .env
```

确认 `.env` 中的数据库连接和 WSL 里的 PostgreSQL 一致：

```env
DATABASE_URL=postgresql+psycopg://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe
```

如果要开启 DeepSeek rerank 或智能改良版菜谱生成，在 `.env` 中填写：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=60
RERANK_ENABLED=true
LLM_ENHANCE_ENABLED=true
```

如果不开启这两个开关，后端仍按 v2 的规则排序在本机正常运行。

启动后端：

```bash
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

在 WSL 或 Windows PowerShell 中检查服务：

```powershell
curl http://localhost:8000/health
```

## 导入真实子集数据

服务启动后，后端会自动创建数据表。执行导入：

```powershell
curl -X POST http://localhost:8000/api/v1/admin/reset-data `
  -H "X-Admin-Token: dev-token"

curl -X POST http://localhost:8000/api/v1/admin/import `
  -H "Content-Type: application/json" `
  -H "X-Admin-Token: dev-token" `
  -d "{}"
```

真实子集首次导入成功时，响应类似：

```json
{"rows":2500,"imported":2500,"skipped":0,"source_records":2500,"recipe_ingredients":20135,"recipe_steps":17784,"skipped_ingredients":1}
```

默认数据位置：

```text
data/xiachufang/recipes_subset.jsonl
```

## 测试食材解析

```powershell
curl -X POST http://localhost:8000/api/v1/ingredients/parse `
  -H "Content-Type: application/json" `
  -d "{\"items\":[\"超市罐头装半盒金枪鱼\",\"5个圣女果\",\"不想吃香菜\"]}"
```

## 测试搜索

```powershell
curl -X POST http://localhost:8000/api/v1/search/by-ingredients `
  -H "Content-Type: application/json" `
  -d "{\"items\":[\"西红柿\",\"鸡蛋\"],\"excluded_items\":[],\"filters\":{},\"page\":1,\"page_size\":5}"
```

## 查看详情

搜索结果中的 `recipe_id` 可用于详情接口：

```powershell
curl http://localhost:8000/api/v1/recipes/1
```

## 可选：测试智能改良版菜谱生成

需要先在 `.env` 中配置 `DEEPSEEK_API_KEY` 并设置 `LLM_ENHANCE_ENABLED=true`。

```powershell
curl -X POST http://localhost:8000/api/v1/recipes/1/enhance `
  -H "Content-Type: application/json" `
  -d "{\"user_items\":[\"西红柿\",\"鸡蛋\"],\"excluded_items\":[\"香菜\"],\"preferences\":{\"spice\":\"not_spicy\",\"complexity\":\"simple\",\"for_children\":true}}"
```

## 可选：全流程测试排序并生成 5 个菜谱

需要先开启 `RERANK_ENABLED=true` 和 `LLM_ENHANCE_ENABLED=true`，并保持后端运行。

```bash
python scripts/full_flow_generate_top5.py \
  --items "西红柿,鸡蛋,黄瓜" \
  --excluded "香菜" \
  --spice not_spicy \
  --for-children \
  --methods "炒,拌" \
  --limit 5 \
  --timeout 180 \
  --retries 1
```

脚本会先搜索排序前 5 个菜谱，再逐个调用智能生成接口，最终输出完整 JSON。单个生成请求失败时不会中断整体流程，会在该条结果的 `generation_error` 中记录原因。

## 可选：重建 OpenSearch 索引

当前搜索接口先使用 PostgreSQL 兜底匹配。安装并启动 OpenSearch 后，可以通过下面命令重建索引：

```powershell
curl -X POST http://localhost:8000/api/v1/admin/reindex `
  -H "X-Admin-Token: dev-token"
```

## 后续实现重点

1. 将 `data/xiachufang/recipes_subset.jsonl` 扩充到完整数据。
2. 根据真实数据补充 `DEFAULT_ALIAS_MAP` 或改为 CSV 种子导入。
3. 将 `/api/v1/search/by-ingredients` 的召回从 PostgreSQL 切到 OpenSearch。
4. 增加黄金查询集和 Recall@20 评测脚本。
5. 增加前端搜索页和详情抽屉。
