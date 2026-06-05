# v3 非 Docker 运行后端步骤

本文档用于在 Windows + WSL 本机或远程 Linux 服务器运行 Fridge2Recipe 后端。

当前版本仍然不依赖 Docker：

- PostgreSQL 是必需数据库。
- 搜索主链路可以只依赖 PostgreSQL 跑通。
- DeepSeek 是可选能力，用于搜索结果 rerank 和智能改良版菜谱生成。
- OpenSearch 仍是可选能力，只在调用 `/api/v1/admin/reindex` 时需要。

默认后端地址：

```text
http://127.0.0.1:8000
```

## 1. v3 功能开关

v3 新增两个可选模型能力，并提供一个用于课堂 / 展示的快速演示缓存：

| 功能 | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| 搜索结果 rerank 精排 | `RERANK_ENABLED` | `false` | 开启后，搜索接口会把规则排序后的前若干结果交给 DeepSeek 重新打分 |
| 智能改良版菜谱生成 | `LLM_ENHANCE_ENABLED` | `false` | 开启后，可以调用 `/api/v1/recipes/{recipe_id}/enhance` 生成更适合用户偏好的做法 |
| 快速演示缓存 | `DEMO_CACHE_ENABLED` | `false` | 开启后，命中固定三组输入时，`/api/v1/demo/full-flow` 直接返回清洗好的搜索、rerank 和智能生成结果 |

没有配置 DeepSeek Key 或关闭开关时，后端仍可正常运行，只是回到 v2 的规则排序和原始详情接口。演示缓存只用于减少展示时等待模型返回的时间，不影响正式搜索接口。

## 2. Windows + WSL 本机运行

推荐把 Python、Conda、PostgreSQL 都安装在 WSL Ubuntu 内。Windows 浏览器和 PowerShell 可以直接访问 WSL 中的后端。

### 2.1 安装 WSL

在 Windows PowerShell 中检查：

```powershell
wsl --status
```

如果尚未安装 WSL，可在管理员 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装完成后重启电脑，打开 Ubuntu 终端完成用户名和密码初始化。

### 2.2 安装系统依赖

在 WSL Ubuntu 中执行：

```bash
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

确认工具可用：

```bash
git --version
curl --version
psql --version
```

如果 `sudo apt install` 找不到 PostgreSQL 包，见本文末尾“常见问题”。

### 2.3 确认或安装 Conda

先确认 WSL 内能否使用 Conda：

```bash
conda --version
```

如果提示 `conda: command not found`，说明 Windows 里的 Anaconda 没有进入 WSL。WSL 是独立 Linux 系统，需要在 WSL 内单独安装 Anaconda 或 Miniconda。

推荐安装 Miniconda：

```bash
cd /tmp
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version
```

如果你确认 WSL 内已经安装 Anaconda，但 shell 没初始化：

```bash
conda init bash
source ~/.bashrc
conda --version
```

### 2.4 进入项目目录

如果项目位于 Windows 的 `D:\Fridge2Recipe`：

```bash
cd /mnt/d/Fridge2Recipe
```

这可以直接运行。若追求更好的 WSL 文件性能，可以复制到 WSL home：

```bash
cp -r /mnt/d/Fridge2Recipe ~/Fridge2Recipe
cd ~/Fridge2Recipe
```

如果项目已推送到 Git 仓库，也可以直接 clone：

```bash
git clone <your-repo-url> Fridge2Recipe
cd Fridge2Recipe
```

其中 `<your-repo-url>` 替换为你的 GitHub / GitLab / Gitee 仓库地址。

### 2.5 启动并配置 PostgreSQL

WSL 中通常使用 `service`：

```bash
sudo service postgresql start
sudo service postgresql status
```

进入 PostgreSQL 管理命令行：

```bash
sudo -u postgres psql
```

执行：

```sql
CREATE USER fridge WITH PASSWORD 'fridge_dev_password';
CREATE DATABASE fridge2recipe OWNER fridge;
\q
```

如果用户或数据库已存在，可以跳过创建步骤。

测试连接：

```bash
psql "postgresql://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe" -c "select now();"
```

### 2.6 创建或更新 Conda 环境

在项目根目录执行：

```bash
conda env create -f environment.yml
conda activate fridge2recipe
```

如果环境已经存在：

```bash
conda activate fridge2recipe
conda env update -f environment.yml --prune
```

v3 的 DeepSeek 调用使用 Python 标准库 HTTP 客户端，不需要额外安装 `openai` 或 `httpx`。

如果 Conda 访问 `repo.anaconda.com` 超时，可以先切换镜像：

```bash
conda config --set show_channel_urls yes
conda config --remove-key channels 2>/dev/null || true
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
conda clean -i
conda env create -f environment.yml
```

如果仍然超时，可以调大 Conda 超时时间：

```bash
conda config --set remote_connect_timeout_secs 30
conda config --set remote_read_timeout_secs 60
```

### 2.7 配置 .env

复制模板：

```bash
cp .env.example .env
```

本机最小可运行配置：

```env
DATABASE_URL=postgresql+psycopg://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe
OPENSEARCH_URL=http://127.0.0.1:9200
API_PORT=8000
ADMIN_TOKEN=dev-token
SAMPLE_DATA_PATH=data/xiachufang/recipes_subset.jsonl
CORS_ALLOWED_ORIGINS=

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=60
RERANK_ENABLED=false
RERANK_TOP_K=20
RERANK_WEIGHT=0.35
LLM_ENHANCE_ENABLED=false

DEMO_CACHE_ENABLED=false
DEMO_CACHE_PATH=data/demo/full_flow_cases.json
```

如果要开启 v3 的 DeepSeek 能力，在 `.env` 中填写你的 Key，并打开开关：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
RERANK_ENABLED=true
LLM_ENHANCE_ENABLED=true
```

如果只是展示功能、想避免等待模型请求，可以开启演示缓存：

```env
DEMO_CACHE_ENABLED=true
DEMO_CACHE_PATH=data/demo/full_flow_cases.json
```

开启后，命中三组固定输入时会直接返回清洗后的全流程结果；未命中时仍可走实时搜索和生成。

注意：

- 不要把真实 `DEEPSEEK_API_KEY` 提交到 Git。
- 如果模型接口返回模型名不可用，可把 `DEEPSEEK_MODEL` 改成你 DeepSeek 账号当前可用的模型名。
- 关闭 `RERANK_ENABLED` 时，搜索接口仍按规则排序。
- 关闭 `LLM_ENHANCE_ENABLED` 时，智能生成接口会返回 `503`。
- 关闭 `DEMO_CACHE_ENABLED` 时，演示缓存接口会返回 `404`，全流程脚本会自动回退实时流程。

### 2.8 启动后端

```bash
conda activate fridge2recipe
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

另开一个 WSL 终端或 Windows PowerShell 测试：

```bash
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

浏览器也可以访问：

```text
http://localhost:8000/docs
```

## 3. 导入数据和基础接口测试

以下命令在 WSL 和远程 Linux 服务器中都适用。

如果你的 WSL 设置了代理，访问本机后端时可以先取消代理环境变量：

```bash
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
curl http://localhost:8000/health
```

### 3.1 清空旧数据

如果之前导入过测试数据或旧真实数据，建议先清空：

```bash
curl -X POST http://localhost:8000/api/v1/admin/reset-data \
  -H "X-Admin-Token: dev-token"
```

### 3.2 导入真实子集数据

`.env` 中默认导入：

```text
data/xiachufang/recipes_subset.jsonl
```

执行：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-token" \
  -d "{}"
```

真实子集导入成功时，响应通常类似：

```json
{"rows":2500,"imported":2500,"skipped":0,"source_records":2500,"recipe_ingredients":20135,"recipe_steps":17784,"skipped_ingredients":1}
```

如果重复导入相同数据，`imported` 会变成 `0`，`skipped` 会增加，这是正常现象。

### 3.3 测试搜索

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":[],"filters":{},"page":1,"page_size":3}'
```

返回中重点看：

- `parsed.ingredients`：后端识别出的食材。
- `items[].matched`：命中的已有食材。
- `items[].missing`：缺少的非基础调味品食材。
- `items[].bucket`：结果分组。
- `items[].recipe_tags`：后端推断标签。
- `items[].rerank_score`：DeepSeek 精排分，未开启或调用失败时为 `null`。
- `facets.rerank`：rerank 诊断状态，包含是否开启、是否配置 key、是否尝试调用、失败原因。

bucket 规则：

```text
缺 0 个 -> 马上能做
缺 1 个 -> 再买 1 样
缺 2-3 个 -> 还差几样
缺 4 个以上 -> 灵感参考
```

默认 `count_seasonings_as_ingredients=false`，所以盐、糖、油、生抽、醋、胡椒、淀粉等基础调味品不会计入 `missing`。

### 3.4 测试偏好标签

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":["香菜"],"filters":{"spice":"not_spicy","complexity":"simple","count_seasonings_as_ingredients":false,"diet":"vegetarian","for_children":true,"serving_size":"small","seasoning_amount":"few","methods":["炒"]},"page":1,"page_size":3}'
```

返回中重点看：

- `preference_matches`
- `preference_mismatches`
- `preference_score`
- `recipe_tags`

说明：食材匹配权重最高，所以某个菜谱即使没有满足“简单”等次级偏好，也可能因为食材匹配很好而排在前面。

### 3.5 测试详情

不要固定使用 `/recipes/1`。正式前端应使用搜索结果里的 `items[].recipe_id`。

手动测试可以先请求：

```bash
curl http://localhost:8000/api/v1/recipes/1
```

返回中重点看：

- `recipe_tags`
- `ingredients[].required`
- `steps`

## 4. v3 DeepSeek 功能测试

### 4.1 测试 rerank 精排

确认 `.env` 中：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
RERANK_ENABLED=true
```

重启后端后，再执行搜索：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":[],"filters":{"spice":"not_spicy","for_children":true},"page":1,"page_size":3}'
```

如果 DeepSeek 调用成功，搜索结果中的部分条目会出现：

```json
{
  "rerank_score": 0.92,
  "rerank_reason": "食材完全覆盖，口味清淡，适合儿童友好做法"
}
```

如果 `rerank_score` 仍为 `null`，常见原因：

- `RERANK_ENABLED` 没有设为 `true`。
- `DEEPSEEK_API_KEY` 为空或错误。
- 当前机器无法访问 `https://api.deepseek.com`。
- `DEEPSEEK_MODEL` 当前不可用。
- `DEEPSEEK_TIMEOUT_SECONDS` 太小，或者 `RERANK_TOP_K` 太大导致 rerank 请求变慢。
- 模型没有返回可解析 JSON。后端会自动关闭 JSON mode 重试一次，如果仍失败，会把返回片段写入 `facets.rerank.error`。

优先查看响应中的 `facets.rerank.error`，它会直接给出本次未生效的原因。
如果错误是 `read operation timed out`，建议先设置：

```env
DEEPSEEK_TIMEOUT_SECONDS=60
RERANK_TOP_K=5
```

注意：rerank 失败不会导致搜索接口失败，后端会自动回退到规则排序，并在服务日志中打印 `DeepSeek rerank skipped`。

### 4.2 测试智能改良版菜谱生成

确认 `.env` 中：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
LLM_ENHANCE_ENABLED=true
```

重启后端后执行：

```bash
curl -X POST http://localhost:8000/api/v1/recipes/1/enhance \
  -H "Content-Type: application/json" \
  -d '{"user_items":["西红柿","鸡蛋"],"excluded_items":["香菜"],"preferences":{"spice":"not_spicy","complexity":"simple","for_children":true,"methods":["炒"]}}'
```

成功时返回：

```json
{
  "recipe_id": 1,
  "source_recipe_id": "r0000067",
  "original_title": "超美味的西红柿蛋汤",
  "generated_title": "儿童友好版西红柿鸡蛋汤",
  "summary": "根据你的食材和偏好生成的智能改良做法。",
  "bucket": "马上能做",
  "bucket_reason": "生成菜谱所需主要食材已被已有食材覆盖，基础调味品和清水不计入缺失。",
  "matched": ["番茄", "鸡蛋"],
  "missing": [],
  "ingredients": ["西红柿 2 个", "鸡蛋 1 个", "盐 少量"],
  "steps": ["西红柿切小块，鸡蛋打散备用。"],
  "tips": ["给小孩吃时盐可以少一点。"],
  "model": "deepseek-v4-flash",
  "disclaimer": "该结果由大模型根据原始菜谱和用户偏好生成，适合作为改良建议，请以实际烹饪情况调整。"
}
```

`bucket` 用于提示智能改良版菜谱的可用性，规则和搜索结果一致：缺 0 个主要食材是 `马上能做`，缺 1 个是 `再买 1 样`，缺 2 到 3 个是 `还差几样`，缺 4 个以上是 `灵感参考`。

如果未开启或未配置 key，会返回 `503`，这是正常保护行为。

### 4.3 全流程测试：排序并生成 5 个菜谱

这个测试会一次完成：

```text
输入食材
-> 调用 /api/v1/search/by-ingredients 获取排序后的前 5 个菜谱
-> 对每个 recipe_id 调用 /api/v1/recipes/{recipe_id}/enhance
-> 输出 5 个带搜索排序信息和智能生成内容的菜谱
```

如果要实时调用 DeepSeek，确认 `.env` 已开启：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
RERANK_ENABLED=true
LLM_ENHANCE_ENABLED=true
```

如果只是快速展示功能，可以改为开启演示缓存。命中固定输入时，脚本会优先返回缓存结果，不再等待 DeepSeek：

```env
DEMO_CACHE_ENABLED=true
DEMO_CACHE_PATH=data/demo/full_flow_cases.json
```

重启后端后，在项目根目录执行：

```bash
python scripts/full_flow_generate_top5.py \
  --items "西红柿,鸡蛋,黄瓜" \
  --excluded "香菜" \
  --spice not_spicy \
  --complexity simple \
  --diet vegetarian \
  --for-children \
  --serving-size small \
  --seasoning-amount few \
  --methods "炒,拌" \
  --limit 5 \
  --timeout 180 \
  --retries 1
```

如果缓存命中，输出中会包含：

```json
{
  "cache_hit": true,
  "case_id": "tomato_egg_cucumber_child",
  "strict_rerank_hit": true,
  "cache_note": "命中演示缓存：该结果来自 data/test_case.jsonl 中 rerank 成功且智能生成成功的记录，已按 recipe_id 去重。"
}
```

当前演示缓存支持三组输入：

```bash
python scripts/full_flow_generate_top5.py \
  --items "西红柿,鸡蛋,黄瓜" \
  --excluded "香菜" \
  --spice not_spicy \
  --complexity simple \
  --diet vegetarian \
  --for-children \
  --serving-size small \
  --seasoning-amount few \
  --methods "炒,拌" \
  --limit 5 \
  --timeout 180 \
  --retries 1

python scripts/full_flow_generate_top5.py \
  --items "土豆,鸡,黄瓜" \
  --excluded "香菜" \
  --spice spicy \
  --complexity complex \
  --diet meat \
  --for-children \
  --serving-size large \
  --seasoning-amount many \
  --methods "炒,炖" \
  --limit 5 \
  --timeout 180 \
  --retries 1

python scripts/full_flow_generate_top5.py \
  --items "土豆,鸡,黄瓜" \
  --excluded "香菜" \
  --spice spicy \
  --complexity complex \
  --diet meat \
  --serving-size large \
  --seasoning-amount many \
  --methods "炒,炖" \
  --limit 5 \
  --timeout 180 \
  --retries 1
```

如果要强制实时测试，不走演示缓存，添加：

```bash
--skip-demo-cache
```

如果要确认必须命中演示缓存，添加：

```bash
--require-demo-cache
```

输出结构：

```json
{
  "input": {
    "items": ["西红柿", "鸡蛋", "黄瓜"],
    "excluded_items": ["香菜"],
    "filters": {
      "spice": "not_spicy",
      "complexity": "simple"
    },
    "limit": 5
  },
  "rerank_status": {
    "enabled": true,
    "configured": true,
    "attempted": true,
    "applied": true,
    "error": null
  },
  "search_total": 2400,
  "items": [
    {
      "rank": 1,
      "search_result": {
        "recipe_id": 1,
        "title": "原始搜索结果标题",
        "bucket": "马上能做",
        "score": 1.23
      },
      "generated_recipe": {
        "generated_title": "智能生成标题",
        "bucket": "马上能做",
        "bucket_reason": "生成菜谱所需主要食材已被已有食材覆盖，基础调味品和清水不计入缺失。",
        "ingredients": ["食材"],
        "steps": ["步骤"]
      }
    }
  ]
}
```

如果只想快速看前 5 个，不指定偏好也可以：

```bash
python scripts/full_flow_generate_top5.py --items "西红柿,鸡蛋" --limit 5 --timeout 180
```

脚本会逐个生成菜谱。某一个菜谱生成超时或失败时，不会中断整个流程；该条结果的 `generated_recipe` 会是 `null`，并在 `generation_error` 中记录失败原因。


## 5. 可选：安装并使用 OpenSearch

当前 v3 搜索接口不依赖 OpenSearch。如果你已经安装并启动 OpenSearch，可以在 `.env` 中配置：

```env
OPENSEARCH_URL=http://127.0.0.1:9200
```

然后调用：

```bash
curl -X POST http://localhost:8000/api/v1/admin/reindex \
  -H "X-Admin-Token: dev-token"
```

## 6. 常见问题

### 6.1 WSL 中 PostgreSQL 没启动

```bash
sudo service postgresql start
sudo service postgresql status
```

### 6.2 `apt install` 下载失败

如果出现 `Connection timed out`、`Temporary failure resolving`，可以先把 Ubuntu 源换成国内镜像。

确认 Ubuntu 版本代号：

```bash
. /etc/os-release
echo $VERSION_CODENAME
```

Ubuntu 24.04 通常输出 `noble`。可执行：

```bash
CODENAME=$(. /etc/os-release && echo $VERSION_CODENAME)
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak 2>/dev/null || true
sudo tee /etc/apt/sources.list.d/ubuntu.sources > /dev/null <<EOF
Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: ${CODENAME} ${CODENAME}-updates ${CODENAME}-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: ${CODENAME}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
sudo apt clean
sudo apt update
```

然后重新安装：

```bash
sudo apt install -y git curl postgresql postgresql-contrib
```

### 6.3 `Unable to locate package postgresql`

先检查源配置：

```bash
grep -R "URIs\\|Suites\\|Components\\|^deb " /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null
apt-cache policy postgresql postgresql-contrib
```

如果输出里没有当前 Ubuntu 版本代号，按上一节重写 Ubuntu 源。

如果还有旧 Docker 源，而当前项目不再使用 Docker，可以先禁用：

```bash
sudo mkdir -p /etc/apt/disabled-sources
sudo mv /etc/apt/sources.list.d/docker.list /etc/apt/disabled-sources/docker.list.bak 2>/dev/null || true
sudo rm -rf /var/lib/apt/lists/*
sudo apt clean
sudo apt update
```

### 6.4 Windows 访问不到 WSL 后端

检查：

- uvicorn 是否使用 `--host 0.0.0.0`
- WSL 中是否能访问 `curl http://localhost:8000/health`
- Windows PowerShell 中是否能访问 `curl http://localhost:8000/health`

### 6.5 数据库连接失败

检查：

```bash
sudo service postgresql status
psql "postgresql://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe" -c "select now();"
```

同时确认 `.env` 中 `DATABASE_URL` 和 PostgreSQL 用户、密码、数据库名一致。

### 6.6 导入数据后搜索为空

检查：

- 是否已经调用 `/api/v1/admin/import`
- 导入响应中 `imported` 是否大于 0
- 是否重复导入导致 `skipped` 增加
- `.env` 中 `SAMPLE_DATA_PATH` 是否指向正确 JSONL 文件

### 6.7 rerank 没有效果

检查：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
RERANK_ENABLED=true
```

然后重启后端。搜索接口如果调用 DeepSeek 失败，会自动回退规则排序，所以接口仍会正常返回，只是 `rerank_score` 可能为 `null`。

### 6.8 智能生成接口返回 503

常见原因：

- `LLM_ENHANCE_ENABLED` 没有设为 `true`
- `DEEPSEEK_API_KEY` 为空或错误
- 服务器无法访问 `https://api.deepseek.com`
- `DEEPSEEK_MODEL` 当前不可用
- 请求超时，可把 `DEEPSEEK_TIMEOUT_SECONDS` 调到 `60` 或 `90`

修改 `.env` 后记得重启后端。

### 6.9 前端跨机器访问后端

如果前端不在后端同一台机器上，前端 API 地址不能写 `127.0.0.1`，应改为：

```text
http://后端机器IP:8000
```

同时在后端 `.env` 中配置前端来源：

```env
CORS_ALLOWED_ORIGINS=http://前端机器IP:5173
```

然后重启后端。
