# Fridge2Recipe 前端接口文档

本文档面向前端开发。当前后端支持“已有食材 / 不需要食材 / 偏好标签”进行菜谱筛选。食材命中权重最高，其次是荤素和辣不辣，其余偏好用于小幅调整排序。默认情况下基础调味品不会计入缺失食材，例如 `盐`、`糖`、`食用油`、`生抽`、`醋`、`胡椒`、`淀粉` 等。

v3 增加了可选 DeepSeek 大模型能力：开启 `RERANK_ENABLED=true` 后，搜索接口会对规则排序后的前若干结果进行模型精排；开启 `LLM_ENHANCE_ENABLED=true` 后，详情页可以调用智能改良版菜谱生成接口。两个能力都通过 `.env` 开关控制，关闭时后端仍按 v2 逻辑正常运行。

## 1. 后端地址

本机后端地址固定使用：

```text
http://127.0.0.1:8000
```

前端建议配置：

```ts
export const API_BASE_URL = "http://127.0.0.1:8000";
```

如果前端运行在另一台机器上，不能使用 `127.0.0.1`，需要改为后端所在机器的局域网 IP 或服务器 IP：

```ts
export const API_BASE_URL = "http://<后端机器IP>:8000";
```

例如：

```ts
export const API_BASE_URL = "http://192.168.1.23:8000";
```

如果前端运行在 Vite 默认端口 `5173`，并且浏览器出现 CORS 报错，请在后端 `.env` 中设置：

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

如果前端在另一台机器上，例如 `http://192.168.1.50:5173`，则改为：

```env
CORS_ALLOWED_ORIGINS=http://192.168.1.50:5173
```

修改后重启后端。

健康检查：

```http
GET /health
```

响应：

```json
{
  "status": "ok"
}
```

## 2. 前后端交互流程

前端第一版建议只有一个搜索页和一个详情弹窗 / 抽屉。

```text
用户输入食材
  -> 点击“搜索”或按 Enter
  -> POST /api/v1/search/by-ingredients
  -> 渲染搜索结果列表
  -> 点击某个菜谱卡片
  -> GET /api/v1/recipes/{recipe_id}
  -> 渲染菜谱详情
```

可选流程：

```text
用户输入食材
  -> 点击“解析”或输入完成后自动解析
  -> POST /api/v1/ingredients/parse
  -> 展示后端归一后的食材 tag
```

搜索接口本身也会解析食材，因此前端可以不单独调用解析接口，直接调用搜索接口。

## 快速演示模式接口

为了展示功能时减少 DeepSeek 请求耗时，后端提供一个可选的演示缓存接口。开启后，如果前端输入命中固定三组测试输入，后端会直接从 `data/demo/full_flow_cases.json` 返回清洗后的“搜索 + rerank + 智能生成”全流程结果。

开启方式是在后端 `.env` 中设置：

```env
DEMO_CACHE_ENABLED=true
DEMO_CACHE_PATH=data/demo/full_flow_cases.json
```

修改后重启后端。

前端推荐流程：

```text
用户点击“生成 5 个菜谱”
  -> POST /api/v1/demo/full-flow
  -> 如果 200：直接渲染缓存返回的搜索结果和生成菜谱
  -> 如果 404：说明未开启缓存或输入未命中，回退到实时接口
  -> POST /api/v1/search/by-ingredients
  -> 对返回的前 N 个 recipe_id 逐个 POST /api/v1/recipes/{recipe_id}/enhance
```

演示缓存接口：

```http
POST /api/v1/demo/full-flow
```

请求格式：

```json
{
  "items": ["西红柿", "鸡蛋", "黄瓜"],
  "excluded_items": ["香菜"],
  "filters": {
    "spice": "not_spicy",
    "complexity": "simple",
    "count_seasonings_as_ingredients": false,
    "diet": "vegetarian",
    "for_children": true,
    "serving_size": "small",
    "seasoning_amount": "few",
    "methods": ["炒", "拌"]
  },
  "limit": 5
}
```

响应格式：

```json
{
  "input": {
    "items": ["西红柿", "鸡蛋", "黄瓜"],
    "excluded_items": ["香菜"],
    "filters": {
      "spice": "not_spicy",
      "complexity": "simple",
      "count_seasonings_as_ingredients": false,
      "diet": "vegetarian",
      "for_children": true,
      "serving_size": "small",
      "seasoning_amount": "few",
      "methods": ["炒", "拌"]
    },
    "limit": 5
  },
  "rerank_status": {
    "enabled": true,
    "configured": true,
    "attempted": true,
    "applied": true,
    "candidate_count": 5,
    "applied_count": 1,
    "model": "deepseek-v4-pro",
    "error": null
  },
  "search_total": 2418,
  "items": [
    {
      "rank": 1,
      "search_result": {
        "recipe_id": 1,
        "source_recipe_id": "r0000067",
        "title": "超美味的西红柿蛋汤",
        "dish": "西红柿蛋汤",
        "quality_score": 1.0,
        "matched": ["番茄", "鸡蛋"],
        "missing": [],
        "bucket": "马上能做",
        "score": 1.157,
        "reason": "命中 2 个已有食材，必需食材已覆盖，偏好匹配：素菜、不辣、适合小孩、分量少，质量分 1.00",
        "recipe_tags": ["不辣", "素菜", "复杂", "调料少", "分量少", "适合小孩", "炒"],
        "preference_matches": ["素菜", "不辣", "适合小孩", "分量少", "调料少", "炒"],
        "preference_mismatches": ["简单"],
        "preference_score": 0.34,
        "rerank_score": null,
        "rerank_reason": null
      },
      "generated_recipe": {
        "recipe_id": 1,
        "source_recipe_id": "r0000067",
        "original_title": "超美味的西红柿蛋汤",
        "generated_title": "番茄黄瓜炒鸡蛋",
        "summary": "酸甜开胃，颜色鲜艳，简单快手，非常适合小朋友的素食小炒。",
        "bucket": "马上能做",
        "bucket_reason": "生成菜谱所需主要食材已被已有食材覆盖，基础调味品和清水不计入缺失。",
        "matched": ["鸡蛋", "番茄", "黄瓜"],
        "missing": [],
        "ingredients": ["鸡蛋 2个", "西红柿 2个", "黄瓜 1根"],
        "steps": ["黄瓜洗净切薄片，西红柿洗净切小块，鸡蛋打散备用。"],
        "tips": ["想要口感更滑嫩，可在出锅前淋入少许水淀粉。"],
        "model": "deepseek-v4-pro",
        "disclaimer": "该结果由大模型根据原始菜谱和用户偏好生成，适合作为改良建议，请以实际烹饪情况调整。"
      },
      "generation_error": null
    }
  ],
  "cache_hit": true,
  "case_id": "tomato_egg_cucumber_child",
  "strict_rerank_hit": true,
  "cache_note": "来自 test_case.jsonl 中 rerank 成功且智能生成成功的结果。"
}
```

字段含义：

| 字段 | 前端用途 |
|---|---|
| `items[].search_result` | 搜索结果卡片，字段含义与 `/api/v1/search/by-ingredients` 的 `items[]` 完全一致 |
| `items[].generated_recipe` | 已生成的智能菜谱，字段含义与 `/api/v1/recipes/{recipe_id}/enhance` 完全一致 |
| `items[].generated_recipe.bucket` | 前端可显示为“马上能做 / 再买 1 样 / 还差几样 / 灵感参考”标签 |
| `items[].generated_recipe.bucket_reason` | 前端可显示为可用性说明 |
| `cache_hit` | `true` 表示本次结果来自演示缓存 |
| `case_id` | 命中的演示样例编号 |
| `strict_rerank_hit` | `true` 表示该样例来自原始记录中 rerank 成功且智能生成成功的结果；第二组为 `false` |
| `cache_note` | 数据来源说明，第二组会说明原始记录没有 rerank 成功样本 |

当前清洗后的三组准确返回数据保存在 `data/demo/full_flow_cases.json`，前端可按接口直接渲染。命中结果概览：

| case_id | 输入 | 是否来自 rerank 成功记录 | 返回 recipe_id 顺序 |
|---|---|---|---|
| `tomato_egg_cucumber_child` | 西红柿、鸡蛋、黄瓜；不需要香菜；不辣、简单、素菜、适合小孩、分量少、调料少、炒/拌 | 是 | `1, 2262, 1653, 1126, 1075` |
| `potato_chicken_cucumber_child` | 土豆、鸡、黄瓜；不需要香菜；辣、复杂、荤菜、适合小孩、分量多、调料多、炒/炖 | 否，原始 `test_case.jsonl` 没有该输入的 rerank 成功记录，只保留智能生成成功结果 | `2154, 2144, 2008, 2339` |
| `potato_chicken_cucumber` | 土豆、鸡、黄瓜；不需要香菜；辣、复杂、荤菜、分量多、调料多、炒/炖 | 是 | `2144, 1259, 2339, 782` |

如果接口返回：

| 状态码 | 含义 | 前端处理 |
|---|---|---|
| `200` | 命中缓存 | 直接渲染结果 |
| `404` | 缓存未开启或输入未命中 | 回退到实时搜索和生成流程 |
| `503` | 缓存文件缺失或格式错误 | 提示后端配置问题，或回退实时流程 |

注意：未命中缓存时，后端日志中出现 `POST /api/v1/demo/full-flow 404 Not Found` 是预期回退信号，不代表后端异常。

## 3. 输入标签与后端字段对应

| 前端区域 | 前端含义 | 后端字段 | 类型 | 示例 |
|---|---|---|---|---|
| 已有食材输入框 / tag | 用户拥有、希望用于匹配的食材 | `items` | `string[]` | `["西红柿", "鸡蛋"]` |
| 不需要食材输入框 / tag | 用户不想看到的食材，含有这些食材的菜谱会被排除 | `excluded_items` | `string[]` | `["香菜"]` |

`items` 和 `excluded_items` 都可以传干净食材名；解析接口也支持识别“不想吃香菜”“不要猪肉”这类自然语言排除表达，并会归一为真正的食材名。

偏好标签统一放在 `filters` 中：

| 前端标签 | 后端字段 | 可选值 | 说明 |
|---|---|---|---|
| 辣 / 不辣 | `filters.spice` | `"spicy"` / `"not_spicy"` | 影响排序，辣不辣权重较高 |
| 简单 / 复杂 | `filters.complexity` | `"simple"` / `"complex"` | 简单表示步骤数 `<= 5`，复杂表示步骤数 `> 5` |
| 调味料是否算食材 | `filters.count_seasonings_as_ingredients` | `true` / `false` | `false` 时基础调味品不计入 `missing`，默认 `false` |
| 荤菜 / 素菜 | `filters.diet` | `"meat"` / `"vegetarian"` | 影响排序，荤素权重较高 |
| 是否给小孩 | `filters.for_children` | `true` / `false` | `true` 时偏好不辣、步骤不太多、少酒类词的菜谱；`false` 或不传表示不启用该偏好 |
| 分量多 / 少 | `filters.serving_size` | `"large"` / `"small"` | 根据标题、描述和食材数量粗略推断 |
| 调料多 / 少 | `filters.seasoning_amount` | `"many"` / `"few"` | 根据基础调味品数量和占比推断 |
| 烹饪手法 | `filters.methods` | `["炒","蒸","煎","拌","炖","炸"]` | 可多选 |

除 `excluded_items`、`max_minutes`、`difficulty_lte`、`cuisine` 外，偏好标签主要用于调整排序分，不会把不完全匹配的菜谱硬过滤掉。

后端还保留以下兼容字段，当前数据中大多为空，前端第一版可以不做：

| 字段 | 类型 | 说明 |
|---|---|---|
| `filters.max_minutes` | `number \| null` | 最大烹饪时间，当前数据基本缺失 |
| `filters.difficulty_lte` | `number \| null` | 最大难度，当前数据基本缺失 |
| `filters.cuisine` | `string[] \| null` | 菜系筛选，当前数据基本缺失 |

分页字段：

| 前端区域 | 后端字段 | 类型 | 示例 |
|---|---|---|---|
| 页码 | `page` | `number` | `1` |
| 每页数量 | `page_size` | `number` | `20` |

## 4. 搜索接口

```http
POST /api/v1/search/by-ingredients
```

### 4.1 请求格式

```json
{
  "items": ["西红柿", "鸡蛋"],
  "excluded_items": ["香菜"],
  "filters": {
    "spice": "not_spicy",
    "complexity": "simple",
    "count_seasonings_as_ingredients": false,
    "diet": "vegetarian",
    "for_children": true,
    "serving_size": "small",
    "seasoning_amount": "few",
    "methods": ["炒"]
  },
  "page": 1,
  "page_size": 20
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `items` | 建议传 | `string[]` | 已有食材，可为空数组；省略时默认为 `[]` |
| `excluded_items` | 建议传 | `string[]` | 不需要食材，可为空数组；省略时默认为 `[]` |
| `filters` | 建议传 | `object` | 偏好标签对象；没有偏好时传 `{}`，省略时后端也会按 `{}` 处理 |
| `page` | 建议传 | `number` | 从 1 开始；省略时默认为 `1` |
| `page_size` | 建议传 | `number` | 1 到 100；省略时默认为 `20` |

### 4.2 响应格式

```json
{
  "parsed": {
    "ingredients": [
      {
        "raw": "西红柿",
        "canonical": "番茄",
        "quantity": null,
        "unit": null,
        "confidence": 1.0
      },
      {
        "raw": "鸡蛋",
        "canonical": "鸡蛋",
        "quantity": null,
        "unit": null,
        "confidence": 1.0
      }
    ],
    "excluded_ingredients": ["香菜"],
    "need_confirmation": ["香菜"]
  },
  "total": 2418,
  "items": [
    {
      "recipe_id": 1,
      "source_recipe_id": "r0000067",
      "title": "超美味的西红柿蛋汤",
      "dish": "西红柿蛋汤",
      "quality_score": 1.0,
      "matched": ["番茄", "鸡蛋"],
      "missing": [],
      "bucket": "马上能做",
      "score": 1.562,
      "reason": "命中 2 个已有食材，必需食材已覆盖，偏好匹配：素菜、不辣、适合小孩、分量少，质量分 1.00，模型判断：食材完全覆盖，口味清淡，适合按用户偏好改造成简单儿童友好版",
      "recipe_tags": ["不辣", "素菜", "复杂", "调料少", "分量少", "适合小孩", "炒"],
      "preference_matches": ["素菜", "不辣", "适合小孩", "分量少", "调料少", "炒"],
      "preference_mismatches": ["简单"],
      "preference_score": 0.34,
      "rerank_score": 0.92,
      "rerank_reason": "食材完全覆盖，口味清淡，适合按用户偏好改造成简单儿童友好版"
    }
  ],
  "facets": {
    "bucket": [
      {
        "name": "马上能做",
        "count": 1
      },
      {
        "name": "还差几样",
        "count": 358
      }
    ],
    "rerank": {
      "enabled": true,
      "configured": true,
      "attempted": true,
      "applied": true,
      "candidate_count": 10,
      "applied_count": 10,
      "model": "deepseek-v4-flash",
      "fallback": null,
      "warning": null,
      "error": null
    }
  }
}
```

注意：示例响应对应上方带 `excluded_items:["香菜"]` 和偏好标签的请求。实际结果会随导入数据、用户输入和偏好选择变化。
`facets.bucket` 示例只展示了部分分组，前端应按接口实际返回的数组渲染。
如果未开启 `RERANK_ENABLED` 或未配置 `DEEPSEEK_API_KEY`，`rerank_score` 和 `rerank_reason` 会是 `null`，排序只使用规则分数。
`facets.rerank` 会返回 rerank 诊断状态。如果 `items[].rerank_score` 为 `null`，优先查看 `facets.rerank.error`。
如果 `facets.rerank.error` 是 `read operation timed out`，表示 DeepSeek 响应超过当前超时时间，后端会自动回退规则排序；可调大 `DEEPSEEK_TIMEOUT_SECONDS` 或调小 `RERANK_TOP_K`。
如果错误是“模型没有返回可解析的 JSON”或“模型返回空内容”，后端会自动关闭 JSON mode 重试一次；仍失败时，会尝试对每个候选菜谱逐条精排。
逐条兜底成功时，`facets.rerank.fallback` 为 `"single_candidate"`，`facets.rerank.warning` 会记录批量精排失败原因；逐条兜底仍失败时，`facets.rerank.error` 会记录失败原因，搜索结果会回退为规则排序。
`facets.rerank.model` 和智能生成响应中的 `model` 都来自后端 `.env` 的 `DEEPSEEK_MODEL`，示例值只用于说明字段格式，实际值以运行环境为准。

### 4.3 搜索响应与前端显示对应

| 后端字段 | 类型 | 前端建议显示 |
|---|---|---|
| `parsed.ingredients[].canonical` | `string` | 顶部“识别到的食材”tag，例如 `番茄` |
| `parsed.ingredients[].raw` | `string` | 原始输入，可作为 tag tooltip 或调试文本 |
| `parsed.excluded_ingredients[]` | `string[]` | 顶部“不需要”tag |
| `parsed.need_confirmation[]` | `string[]` | 需要用户确认的低置信度食材；普通食材和排除食材都可能出现在这里 |
| `total` | `number` | 当前请求条件下的结果总数，例如 `共 2418 个结果` |
| `items[].recipe_id` | `number` | 点击卡片后请求详情接口 |
| `items[].title` | `string` | 菜谱卡片主标题 |
| `items[].dish` | `string \| null` | 菜谱卡片副标题 / 菜品名 |
| `items[].bucket` | `string` | 结果标签，例如 `马上能做`、`再买 1 样`、`还差几样`、`灵感参考` |
| `items[].matched` | `string[]` | “已匹配”食材 tag |
| `items[].missing` | `string[]` | “还缺”食材 tag；当 `count_seasonings_as_ingredients=false` 时基础调味品不会出现在这里 |
| `items[].reason` | `string` | 推荐原因，可直接显示 |
| `items[].score` | `number` | 排序分，前端可隐藏 |
| `items[].quality_score` | `number` | 菜谱质量分，前端可隐藏 |
| `items[].recipe_tags` | `string[]` | 后端推断出的菜谱标签，可显示在卡片上 |
| `items[].preference_matches` | `string[]` | 与用户偏好匹配的标签，可显示为高亮 tag |
| `items[].preference_mismatches` | `string[]` | 未匹配的偏好标签，可隐藏或调试显示 |
| `items[].preference_score` | `number` | 偏好加权分，前端可隐藏 |
| `items[].rerank_score` | `number \| null` | DeepSeek 精排分，未开启 rerank 时为 `null` |
| `items[].rerank_reason` | `string \| null` | DeepSeek 精排原因，前端可作为补充推荐理由 |
| `facets.bucket` | `{name:string,count:number}[]` | 顶部结果分类统计 |
| `facets.rerank.enabled` | `boolean` | 后端当前是否开启 `RERANK_ENABLED` |
| `facets.rerank.configured` | `boolean` | 后端当前是否读到了 `DEEPSEEK_API_KEY` |
| `facets.rerank.attempted` | `boolean` | 本次搜索是否尝试调用 DeepSeek |
| `facets.rerank.applied` | `boolean` | DeepSeek 精排结果是否实际应用到排序 |
| `facets.rerank.candidate_count` | `number` | 本次交给 DeepSeek 的候选数量 |
| `facets.rerank.applied_count` | `number` | 成功应用 rerank 分数的候选数量 |
| `facets.rerank.model` | `string` | 本次配置使用的 DeepSeek 模型名 |
| `facets.rerank.fallback` | `string \| null` | `"single_candidate"` 表示批量精排失败后使用逐条精排兜底 |
| `facets.rerank.warning` | `string \| null` | rerank 已生效但批量调用有异常时的诊断信息 |
| `facets.rerank.error` | `string \| null` | rerank 未生效时的诊断原因 |

说明：`preference_mismatches` 只表示该菜谱没有满足某个偏好标签，不代表结果错误。因为食材匹配权重最高，一个菜谱即使没有满足“简单”等次级偏好，也可能因为食材完全匹配而排在前面。

## 5. 菜谱详情接口

```http
GET /api/v1/recipes/{recipe_id}
```

前端触发方式：用户点击搜索结果卡片时，把该卡片的 `recipe_id` 拼到 URL 中。
不要固定请求 `/api/v1/recipes/1`；详情页必须使用当前被点击卡片的 `items[].recipe_id`。

### 5.1 响应格式

```json
{
  "recipe_id": 1,
  "source_recipe_id": "r0000067",
  "title": "超美味的西红柿蛋汤",
  "dish": "西红柿蛋汤",
  "description": "人人都会做的西红柿蛋汤,我只喜欢喝我自己做的,不用加任何味精鸡精,健康美味",
  "quality_score": 1.0,
  "recipe_tags": ["不辣", "素菜", "复杂", "调料少", "分量少", "适合小孩", "炒"],
  "ingredients": [
    {
      "raw_text": "2个西红柿",
      "canonical_name": "番茄",
      "quantity": null,
      "unit": null,
      "required": true,
      "position": 1
    },
    {
      "raw_text": "1个鸡蛋",
      "canonical_name": "鸡蛋",
      "quantity": null,
      "unit": null,
      "required": true,
      "position": 2
    },
    {
      "raw_text": "2勺盐",
      "canonical_name": "盐",
      "quantity": null,
      "unit": null,
      "required": false,
      "position": 3
    },
    {
      "raw_text": "1勺淀粉",
      "canonical_name": "淀粉",
      "quantity": null,
      "unit": null,
      "required": false,
      "position": 4
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "text": "热油下葱花爆锅"
    }
  ]
}
```

说明：上面的 `steps` 只截取了第 1 步作为格式示例，实际详情接口会返回该菜谱的全部步骤。

### 5.2 详情响应与前端显示对应

| 后端字段 | 类型 | 前端建议显示 |
|---|---|---|
| `title` | `string` | 详情标题 |
| `dish` | `string \| null` | 菜品名 / 副标题 |
| `description` | `string \| null` | 简介，没有则隐藏 |
| `recipe_tags` | `string[]` | 与搜索结果一致的后端推断标签 |
| `ingredients[].raw_text` | `string` | 食材原文列表 |
| `ingredients[].canonical_name` | `string \| null` | 规范食材名，可用于 tag |
| `ingredients[].required` | `boolean` | `true` 显示为“必需食材”，`false` 显示为“基础调味品” |
| `ingredients[].position` | `number` | 食材顺序 |
| `steps[].step_no` | `number` | 步骤序号 |
| `steps[].text` | `string` | 步骤内容 |

## 6. 智能改良版菜谱生成接口

该接口用于详情页“生成适合我的做法”按钮。它不会修改数据库中的原始菜谱，只返回一份由 DeepSeek 根据原始菜谱和用户偏好生成的改良建议。

需要后端 `.env` 中开启：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
LLM_ENHANCE_ENABLED=true
```

```http
POST /api/v1/recipes/{recipe_id}/enhance
```

请求：

```json
{
  "user_items": ["西红柿", "鸡蛋"],
  "excluded_items": ["香菜"],
  "preferences": {
    "spice": "not_spicy",
    "complexity": "simple",
    "count_seasonings_as_ingredients": false,
    "diet": "vegetarian",
    "for_children": true,
    "serving_size": "small",
    "seasoning_amount": "few",
    "methods": ["炒"]
  }
}
```

响应：

```json
{
  "recipe_id": 1,
  "source_recipe_id": "r0000067",
  "original_title": "超美味的西红柿蛋汤",
  "generated_title": "儿童友好版西红柿鸡蛋汤",
  "summary": "保留原菜谱主要做法，减少刺激性调味，让步骤更适合家庭快手烹饪。",
  "bucket": "马上能做",
  "bucket_reason": "生成菜谱所需主要食材已被已有食材覆盖，基础调味品和清水不计入缺失。",
  "matched": ["番茄", "鸡蛋"],
  "missing": [],
  "ingredients": [
    "西红柿 2 个",
    "鸡蛋 1 个",
    "盐 少量",
    "清水 适量"
  ],
  "steps": [
    "西红柿切小块，鸡蛋打散备用。",
    "锅中放少量油，加入西红柿炒出汤汁。",
    "加入清水煮开，慢慢倒入蛋液。",
    "蛋花成形后加少量盐调味即可。"
  ],
  "tips": [
    "给小孩吃时盐可以再少一点。",
    "如果怕酸，可以把西红柿多炒一会儿。"
  ],
  "model": "deepseek-v4-flash",
  "disclaimer": "该结果由大模型根据原始菜谱和用户偏好生成，适合作为改良建议，请以实际烹饪情况调整。"
}
```

其中 `bucket` 与搜索结果的可用性标签保持一致：

| bucket | 含义 |
|---|---|
| `马上能做` | 生成菜谱的主要食材都已覆盖 |
| `再买 1 样` | 还缺 1 个主要食材 |
| `还差几样` | 还缺 2 到 3 个主要食材 |
| `灵感参考` | 还缺 4 个或更多主要食材 |

`matched` 和 `missing` 只统计主要食材，基础调味品和清水不计入缺失。

如果未配置 key 或未开启生成开关，接口会返回 `503`。前端可提示“智能生成暂不可用，请稍后再试”。
如果模型请求或生成结果处理失败，接口也会返回 `503`，错误原因在响应体 `detail` 字段中，例如：

```json
{
  "detail": "智能生成失败: 具体错误原因"
}
```

## 7. 食材解析接口

该接口可选。用于搜索前预览后端如何理解用户输入。

```http
POST /api/v1/ingredients/parse
```

请求：

```json
{
  "items": ["西红柿2个 鸡蛋3枚", "不想吃香菜"]
}
```

响应：

```json
{
  "ingredients": [
    {
      "raw": "西红柿2个",
      "canonical": "番茄",
      "quantity": 2.0,
      "unit": "个",
      "confidence": 1.0
    },
    {
      "raw": "鸡蛋3枚",
      "canonical": "鸡蛋",
      "quantity": 3.0,
      "unit": "枚",
      "confidence": 1.0
    }
  ],
  "excluded_ingredients": ["香菜"],
  "need_confirmation": []
}
```

## 8. 全流程示例

### 8.1 前端搜索按钮触发

用户界面：

```text
已有食材：西红柿、鸡蛋
不需要：香菜
偏好：不辣、简单、素菜、适合小孩、分量少、调料少、炒
点击：搜索
```

前端请求：

```ts
const response = await fetch("http://127.0.0.1:8000/api/v1/search/by-ingredients", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    items: ["西红柿", "鸡蛋"],
    excluded_items: ["香菜"],
    filters: {
      spice: "not_spicy",
      complexity: "simple",
      count_seasonings_as_ingredients: false,
      diet: "vegetarian",
      for_children: true,
      serving_size: "small",
      seasoning_amount: "few",
      methods: ["炒"]
    },
    page: 1,
    page_size: 10
  })
});

const data = await response.json();
```

前端渲染：

```text
顶部 tag：
识别到：番茄、鸡蛋
不需要：香菜

结果卡片：
标题：超美味的西红柿蛋汤
副标题：西红柿蛋汤
标签：马上能做
菜谱标签：不辣、素菜、复杂、调料少、分量少、适合小孩、炒
偏好匹配：素菜、不辣、适合小孩、分量少、调料少、炒
偏好未匹配：简单
已匹配：番茄、鸡蛋
还缺：无
原因：命中 2 个已有食材，必需食材已覆盖，偏好匹配：素菜、不辣、适合小孩、分量少，质量分 1.00
```

### 8.2 点击卡片查看详情

用户点击第一条搜索结果，前端读取：

```ts
const recipeId = data.items[0].recipe_id;
```

请求详情：

```ts
const detailResponse = await fetch(`http://127.0.0.1:8000/api/v1/recipes/${recipeId}`);
const detail = await detailResponse.json();
```

前端渲染：

```text
标题：超美味的西红柿蛋汤
简介：人人都会做的西红柿蛋汤...
菜谱标签：不辣、素菜、复杂、调料少、分量少、适合小孩、炒

必需食材：
- 2个西红柿
- 1个鸡蛋

基础调味品：
- 2勺盐
- 1勺淀粉

步骤：
1. 热油下葱花爆锅
2. 西红柿下锅...
```

### 8.3 点击按钮生成智能改良版

```ts
const enhancedResponse = await fetch(`${API_BASE_URL}/api/v1/recipes/${recipeId}/enhance`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    user_items: ["西红柿", "鸡蛋"],
    excluded_items: ["香菜"],
    preferences: {
      spice: "not_spicy",
      complexity: "simple",
      for_children: true,
      methods: ["炒"]
    }
  })
});

const enhanced = await enhancedResponse.json();
```

前端渲染：

```text
智能改良版标题：儿童友好版西红柿鸡蛋汤
摘要：保留原菜谱主要做法，减少刺激性调味...
食材：西红柿 2 个、鸡蛋 1 个、盐 少量、清水 适量
步骤：按 enhanced.steps 渲染
小贴士：按 enhanced.tips 渲染
```

## 9. TypeScript 类型

```ts
export interface ParsedIngredient {
  raw: string;
  canonical: string;
  quantity: number | null;
  unit: string | null;
  confidence: number;
}

export interface ParseResponse {
  ingredients: ParsedIngredient[];
  excluded_ingredients: string[];
  need_confirmation: string[];
}

export interface SearchRequest {
  items?: string[];
  excluded_items?: string[];
  filters?: {
    max_minutes?: number | null;
    difficulty_lte?: number | null;
    cuisine?: string[] | null;
    spice?: "spicy" | "not_spicy" | null;
    complexity?: "simple" | "complex" | null;
    count_seasonings_as_ingredients?: boolean;
    diet?: "meat" | "vegetarian" | null;
    for_children?: boolean | null;
    serving_size?: "large" | "small" | null;
    seasoning_amount?: "many" | "few" | null;
    methods?: Array<"炒" | "蒸" | "煎" | "拌" | "炖" | "炸">;
  };
  page?: number;
  page_size?: number;
}

export interface SearchItem {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  quality_score: number;
  matched: string[];
  missing: string[];
  bucket: string;
  score: number;
  reason: string;
  recipe_tags: string[];
  preference_matches: string[];
  preference_mismatches: string[];
  preference_score: number;
  rerank_score: number | null;
  rerank_reason: string | null;
}

export interface SearchResponse {
  parsed: ParseResponse;
  total: number;
  items: SearchItem[];
  facets: {
    bucket: Array<{ name: string; count: number }>;
    rerank: {
      enabled: boolean;
      configured: boolean;
      attempted: boolean;
      applied: boolean;
      candidate_count: number;
      applied_count: number;
      model: string;
      fallback: "single_candidate" | null;
      warning: string | null;
      error: string | null;
    };
    [key: string]: unknown;
  };
}

export interface RecipeDetail {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  description: string | null;
  quality_score: number;
  recipe_tags: string[];
  ingredients: Array<{
    raw_text: string;
    canonical_name: string | null;
    quantity: number | null;
    unit: string | null;
    required: boolean;
    position: number;
  }>;
  steps: Array<{
    step_no: number;
    text: string;
  }>;
}

export interface RecipeEnhanceRequest {
  user_items?: string[];
  excluded_items?: string[];
  preferences?: SearchRequest["filters"];
}

export interface RecipeEnhanceResponse {
  recipe_id: number;
  source_recipe_id: string | null;
  original_title: string;
  generated_title: string;
  summary: string;
  bucket: string;
  bucket_reason: string;
  matched: string[];
  missing: string[];
  ingredients: string[];
  steps: string[];
  tips: string[];
  model: string;
  disclaimer: string;
}

export interface DemoFullFlowRequest {
  items?: string[];
  excluded_items?: string[];
  filters?: SearchRequest["filters"];
  limit?: number;
}

export interface FullFlowItem {
  rank: number;
  search_result: SearchItem;
  generated_recipe: RecipeEnhanceResponse | null;
  generation_error: string | null;
}

export interface DemoFullFlowResponse {
  input: {
    items: string[];
    excluded_items: string[];
    filters: SearchRequest["filters"];
    limit: number;
  };
  rerank_status: SearchResponse["facets"]["rerank"] | Record<string, unknown> | null;
  search_total: number;
  items: FullFlowItem[];
  cache_hit: boolean;
  case_id: string;
  strict_rerank_hit: boolean;
  cache_note: string;
}
```

## 10. 错误处理

| 状态码 | 场景 | 前端处理 |
|---|---|---|
| `404` | 详情接口中 `recipe_id` 不存在；或演示缓存接口未开启 / 未命中 | 详情页提示“菜谱不存在”；演示缓存未命中时回退实时流程 |
| `422` | 请求体格式错误，例如 `page_size` 超过 100 | 提示“搜索参数错误” |
| `503` | 智能生成接口中 DeepSeek 未配置、未开启，或模型请求失败；或演示缓存文件缺失 / 格式错误 | 提示“智能生成暂不可用”或“演示缓存配置异常” |
| `500` | 后端服务异常 | 提示“服务异常，请稍后重试” |

管理接口如 `/api/v1/admin/import`、`/api/v1/admin/reset-data` 只用于数据准备，不建议普通前端页面调用。
搜索接口的 rerank 失败不会返回 `503`，而是保持 `200` 返回搜索结果，并在 `facets.rerank.error` 中说明原因。
