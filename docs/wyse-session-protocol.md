# 市场模式接口

---

## 典型交互时序

一次完整的会话交互流程如下：

```
1. createSession          → 获取 session_id
2. 连接 WebSocket          → wss://.../session/ws/{session_id}?authorization={jwt}
3. 发送 start             → 携带任务描述、附件、技能
4. 收到 plan (create_plan) → 服务端生成执行计划
5. 收到 input             → 服务端请求确认计划
6. 发送 input (plan)      → 用户确认/拒绝计划
7. 收到 progress          → 执行进度更新
8. 收到 plan (update_task_status) → 步骤状态变更
9. 收到 text / rich       → 执行过程中的输出消息
10. 收到 task_result       → 任务执行结束
11. (可选) 收到 follow_up_suggestion → 后续建议
```

> 注意：步骤 4-9 可能多次循环，如果执行过程中需要用户输入（`input`），会再次进入等待状态。遇到 `error` 类型消息时表示执行出错。

---

## 认证方式

支持两种认证方式：

- **JWT Token**：HTTP API 在请求头中携带 `Authorization: {jwt_token}`，WebSocket 在 URL query 中携带 `?authorization={jwt_token}`
- **API Key**：HTTP API 在请求头中携带 `x-api-key: {api_key}`，WebSocket 在 URL query 中携带 `?api_key={api_key}`

## HTTP API

### 通用响应结构

所有 HTTP API 响应遵循统一结构：

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

| 字段     | 类型   | 说明                                                          |
| -------- | ------ | ------------------------------------------------------------- |
| `code` | number | 状态码，`0` 表示成功，非 `0` 为错误                       |
| `msg`  | string | 状态描述                                                      |
| `data` | T      | 业务数据，**后文所有 API 的"响应"部分均指此字段的内容** |

### 会话 API

在连接 WebSocket 之前，需要通过 HTTP API 创建会话。

### 创建会话 createSession

创建新的会话，返回 `session_id` 后即可用于 WebSocket 连接。

**请求**

```
POST /session/create
```

**请求体**

```json
{
  "task": "用户任务描述",
  "mode": "",
  "platform": "",
  "extra": {
    "skills": [{ "skill_id": "xxx", "skill_name": "xxx" }],
    "marketing_product": { "product_id": "xxx" },
    "strategy": { "strategy_key": "xxx", "prompt_id": "xxx" }
  }
}
```

| 字段                        | 类型                            | 必填 | 说明                                                                                   |
| --------------------------- | ------------------------------- | ---- | -------------------------------------------------------------------------------------- |
| `task`                    | string                          | 是   | 任务描述                                                                               |
| `intent_id`               | string                          | 否   | 意图 ID                                                                                |
| `mode`                    | string                          | 否   | 模式，可选 `"marketing"` 或留空                                                      |
| `platform`                | string                          | 否   | 平台标识，可选 `"extension"`（使用插件）/ `"api"`（API 调用）/ `"web"`（Web 端） |
| `extra`                   | object                          | 否   | 扩展参数                                                                               |
| `extra.skills`            | `SkillType[]`                 | 否   | 关联技能列表                                                                           |
| `extra.marketing_product` | `{ product_id }`              | 否   | 营销产品                                                                               |
| `extra.strategy`          | `{ strategy_key, prompt_id }` | 否   | 营销策略                                                                               |

**响应**

```json
{
  "session_id": "新创建的会话 ID"
}
```

---

### 获取会话详情 getSessionInfo

获取已有会话的详细信息。

**请求**

```
GET /session/info/{session_id}
```

| 参数           | 类型          | 说明    |
| -------------- | ------------- | ------- |
| `session_id` | string (path) | 会话 ID |

**响应**

```json
{
  "name": "会话名称",
  "session_id": "xxx",
  "browser_id": "xxx",
  "status": "created",
  "task": [{ "role": "user", "content": "任务描述" }],
  "task_result": { "type": "", "source": "", "content": "" },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "visibility": "private",
  "platform": "core",
  "mode": "",
  "attachments": [],
  "extra": null
}
```

| 字段            | 类型                            | 说明                                                                                                                                                    |
| --------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `session_id`  | string                          | 会话唯一标识                                                                                                                                            |
| `team_id`     | string                          | 所属团队 ID                                                                                                                                             |
| `intent_id`   | string                          | 意图 ID                                                                                                                                                 |
| `browser_id`  | string                          | 关联浏览器实例 ID                                                                                                                                       |
| `status`      | string                          | 会话状态：`"created"`（已创建）/ `"active"`（执行中）/ `"complete"`（完成）/ `"error"`（出错）/ `"stopped"`（已停止）/ `"paused"`（已暂停） |
| `task`        | `{ role, content }[]`         | 任务描述                                                                                                                                                |
| `task_result` | object                          | 任务执行结果                                                                                                                                            |
| `visibility`  | `"private" \| "access_by_url"` | 是否为公开的                                                                                                                                            |
| `platform`    | string                          | 平台标识                                                                                                                                                |
| `mode`        | string?                         | 模式                                                                                                                                                    |
| `attachments` | AttachmentType[]?               | 附件列表                                                                                                                                                |
| `extra`       | object?                         | 扩展信息（技能、营销产品、策略等）结构和创建时传入的一致                                                                                                |

---

### 获取营销数据 getMarketingDataInSession

流式营销消息（`marketing_tweet_reply` / `marketing_tweet_interact` / `writer_twitter`）结束后，调用此 API 获取本次生成的完整数据。

**请求**

```
GET /session/marketing/data/{session_id}?type={type}
```

| 参数           | 类型           | 说明                                                                                    |
| -------------- | -------------- | --------------------------------------------------------------------------------------- |
| `session_id` | string (path)  | 会话 ID                                                                                 |
| `type`       | string (query) | 数据类型，可选 `"reply"` / `"like"` / `"retweet"` / `"tweet"`，留空返回所有类型 |

**响应**

```json
{
  "reply": [],
  "like": [],
  "retweet": [],
  "tweet": []
}
```

| 字段        | 类型                  | 说明               |
| ----------- | --------------------- | ------------------ |
| `reply`   | `TweetWithReply[]`  | 生成的推文回复     |
| `like`    | `TweetInMessage[]`  | 匹配到的待点赞推文 |
| `retweet` | `TweetInMessage[]`  | 匹配到的待转推推文 |
| `tweet`   | `TweetWriterData[]` | 创作的营销推文     |

> 当指定 `type` 参数时，仅对应字段有数据，其余为空数组。

---

## 连接参数

### WebSocket URL

```
wss://{API_BASE_URL}/session/ws/{session_id}
```

| 参数             | 类型   | 说明       |
| ---------------- | ------ | ---------- |
| `API_BASE_URL` | string | 服务端地址 |
| `session_id`   | string | 会话 ID    |

### 认证方式（二选一）

**方式一：JWT 放在 URL query 参数中**

```
wss://{API_BASE_URL}/session/ws/{session_id}?authorization={jwt_token}
```

**方式二：API Key 放在 URL query 参数中**

```
wss://{API_BASE_URL}/session/ws/{session_id}?api_key={api_key}
```

### 心跳机制

- 使用Ping/Pong检测连接活跃
- 传输格式:

客户端发送 `ping`

```json
{
    type: "ping",
    timestamp: 1711234567890,
}
```

心跳响应 `pong`

```json
{
  "type": "pong",
  "timestamp": 1711234567890
}
```

---

## 客户端发送消息（Client → Server）

### 1. 启动任务 `start`

开始一轮新的任务执行。

```json
{
  "type": "start",
  "data": {
    "messages": [
      {
        "type": "task",
        "content": "用户输入的任务描述"
      }
    ],
    "attachments": [
      {
        "file_name": "example.pdf",
        "file_url": "https://..."
      }
    ],
    "extra": {
      "skills": [{ "skill_id": "xxx", "skill_name": "xxx" }],
      "marketing_product": { "product_id": "xxx" },
      "strategy": { "strategy_key": "xxx", "prompt_id": "xxx" }
    }
  }
}
```

| 字段                        | 类型                            | 必填 | 说明         |
| --------------------------- | ------------------------------- | ---- | ------------ |
| `data.messages[].type`    | `"task"`                      | 是   | 消息类型     |
| `data.messages[].content` | string                          | 是   | 任务内容     |
| `data.attachments`        | SessionFileType[]               | 否   | 附件列表     |
| `extra`                   | object                          | 否   | 扩展参数     |
| `extra.skills`            | `SkillType[]`                 | 否   | 关联技能列表 |
| `extra.marketing_product` | `{ product_id }`              | 否   | 营销产品     |
| `extra.strategy`          | `{ strategy_key, prompt_id }` | 否   | 营销策略     |

### 回复 `input` 消息

收到服务端 `type: "input"` 消息后，需根据上下文判断 `input_type`，再发送对应格式的回复：

| 条件                               | input_type      | 说明                                                   |
| ---------------------------------- | --------------- | ------------------------------------------------------ |
| `message.type === "x_confirm"`   | `"x_confirm"` | 插件自动执行任务确认                                   |
| 上一条消息 `type === "plan"`     | `"plan"`      | 计划确认                                               |
| `source === "marketing_analyst"` | `"text"`      | 产品分析报告确认（营销场景），用户需确认或补充产品信息 |
| 其他                               | `"text"`      | 普通文本输入                                           |

#### 2a. 文本回复 `input` (text)

用户文本回复，适用于普通输入及 `source === "marketing_analyst"` 的产品分析确认。

```json
{
  "type": "input",
  "data": {
    "input_type": "text",
    "text": "用户回复内容",
    "request_id": "req_xxx",
    "attachments": [],
    "skills": []
  }
}
```

| 字段                 | 类型              | 必填 | 说明                                                                         |
| -------------------- | ----------------- | ---- | ---------------------------------------------------------------------------- |
| `data.input_type`  | `"text"`        | 是   | 输入类型                                                                     |
| `data.text`        | string            | 是   | 回复文本内容，可能是纯文本或 JSON 字符串（含 `message` + `data` 选中项） |
| `data.request_id`  | string            | 是   | 对应的请求 ID，从最近一条 `input` 消息的 `message.data.request_id` 获取  |
| `data.attachments` | SessionFileType[] | 否   | 可选附件                                                                     |
| `data.skills`      | SkillType[]       | 否   | 可选技能                                                                     |

#### 2b. 计划回复 `input` (plan)

用户确认或拒绝 Agent 提出的执行计划。

```json
{
  "type": "input",
  "data": {
    "input_type": "plan",
    "request_id": "",
    "response": {
      "accepted": true,
      "plan": [
        { "id": "1", "title": "Step 1", "description": "...", "status": "" }
      ],
      "content": ""
    }
  }
}
```

| 字段                       | 类型        | 必填 | 说明                                                                       |
| -------------------------- | ----------- | ---- | -------------------------------------------------------------------------- |
| `data.input_type`        | `"plan"`  | 是   | 输入类型                                                                   |
| `data.request_id`        | string      | 是   | 请求 ID                                                                    |
| `data.response.accepted` | boolean     | 是   | 是否接受计划                                                               |
| `data.response.plan`     | BasicStep[] | 否   | 接受时附带的计划步骤（可被用户编辑后返回）                                 |
| `data.response.content`  | string      | 否   | 拒绝时的说明，如 `"Regenerate a plan that improves on the current plan"` |

#### 2c. 确认回复 `input` (x_confirm)

用户确认特定操作（如 Twitter 发布确认等）。

```json
{
  "type": "input",
  "data": {
    "input_type": "plan",
    "request_id": "",
    "response": {
      "accepted": true,
      "content": "用户确认内容"
    }
  }
}
```

### 5. 暂停 / 停止 `pause` / `stop`

控制会话执行状态。

```json
{
  "type": "pause",
  "reason": "可选的暂停原因"
}
```

```json
{
  "type": "stop",
  "reason": "可选的停止原因"
}
```

### 6. 心跳 `ping`

```json
{
  "type": "ping",
  "timestamp": 1711234567890
}
```

---

## 服务端推送消息（Server → Client）

所有服务端消息解析为 JSON。

### 公共字段

所有服务端消息都包含以下字段：

| 字段                 | 类型                                               | 说明                                                                  |
| -------------------- | -------------------------------------------------- | --------------------------------------------------------------------- |
| `type`             | string                                             | 消息类型                                                              |
| `message_id`       | string                                             | 消息唯一标识                                                          |
| `source`           | string                                             | 来源 Agent ID 或 Team ID                                              |
| `source_component` | `"wyse_team" \| "wyse_agent" \| "user" \| "system"` | 来源组件类型                                                          |
| `source_type`      | string                                             | 来源类型，如 `"wyse_browser"`, `"user_proxy"`, `"wyse_mate"` 等 |
| `content`          | string                                             | 消息文本内容（markdown）                                              |
| `created_at`       | string                                             | 创建时间                                                              |
| `browser_id`       | string?                                            | 关联的浏览器实例 ID                                                   |
| `session_round`    | number?                                            | 会话轮次                                                              |
| `timestamp`        | number?                                            | 时间戳                                                                |
| `attachments`      | AttachmentType[]?                                  | 附件                                                                  |
| `code`             | number?                                            | 错误码（错误消息时）                                                  |
| `error`            | string?                                            | 错误描述（错误消息时）                                                |
| `chunk_id`         | string\| null?                                     | 分块 ID（流式消息）                                                   |
| `chunk_index`      | number?                                            | 分块索引（流式消息）                                                  |
| `delta`            | boolean\| null?                                    | 是否为增量消息                                                        |

---

### 1. 文本消息 `type: "text"`

纯文本消息。

```json
{
  "type": "text",
  "message_id": "msg_xxx",
  "source": "wyse_mate",
  "source_component": "wyse_agent",
  "content": "这是一条 Markdown 文本消息"
}
```

---

### 2. 复杂类型消息 `type: "rich"`

根据 `message.type` 分发不同的渲染组件，`message.data` 结构因子类型而异。

```json
{
  "type": "rich",
  "message_id": "msg_xxx",
  "source": "wyse_browser",
  "source_component": "wyse_agent",
  "content": "",
  "message": {
    "type": "browser",
    "data": { ... },
    "metadata": {
      "internal": "yes",
      "exec_file": "",
      "type": "final_answer",
      "to": "marketing",
      "data_type": "marketing_tweet_reply",
      "from_request_id": "req_xxx"
    }
  }
}
```

#### `message.type` 子类型及 `message.data` 结构

**`file`** — 文件列表

```json
{ "data": [{ "file_name": "report.pdf", "url": "https://...", "extension": "pdf" }] }
```

**`browser`** — 浏览器操作

```json
{ "data": { "action": "screenshot", "text": "操作描述", "screenshot": "base64...", "url": "https://..." } }
```

**`search`** — 搜索结果

```json
{ "data": [{ "favicon": "https://...", "link": "https://...", "title": "标题", "snippet": "摘要" }] }
```

**`image`** — 图片列表

```json
{ "data": [{ "file_name": "photo.png", "url": "https://...", "extension": "png" }] }
```

**`file_surfer`** — 文件浏览操作

```json
{ "data": { "action": "open", "text": "操作描述", "file_name": "example.py" } }
```

**`marketing_tweet_reply`** — 营销推文回复（支持分块流式）

流式传输流程：

1. 连续收到 N 个 chunk 消息（`delta: true` 且 `chunk_id` 有值），每个 chunk 的 `data` 是数组中的一个 item
2. 一组 chunk 构成一个 `TweetWithReply[]` 数组，表示本轮生成的一组带回复的推文
3. 最后收到一条同类型但非 chunk 的消息（`delta: false/null`，无 `chunk_id`），表示流式结束
4. 流式结束后，调用 API 获取完整数据

chunk 消息示例：

```json
{
  "type": "rich",
  "message": { "type": "marketing_tweet_reply", "data": { ... } },
  "delta": true,
  "chunk_id": "chunk_xxx",
  "chunk_index": 0
}
```

结束消息示例：

```json
{
  "type": "rich",
  "message": { "type": "marketing_tweet_reply", "data": null },
  "delta": false,
  "chunk_id": null
}
```

流式结束后调用 API 获取完整数据，见 [获取营销数据 API](#获取营销数据-getmarketingdatainsession)。

**`marketing_tweet_interact`** — 营销推文互动（支持分块流式）

流式传输流程与 `marketing_tweet_reply` 一致，区别在于：

- chunk data 类型为 `TweetInMessage`（即不含 `reply` 字段的推文）
- **下发的 chunk 同时包含点赞（like）和转推（retweet）两类推文**，流式过程中无法区分

chunk 消息示例：

```json
{
  "type": "rich",
  "message": { "type": "marketing_tweet_interact", "data": { ... } },
  "delta": true,
  "chunk_id": "chunk_xxx",
  "chunk_index": 0
}
```

结束消息示例：

```json
{
  "type": "rich",
  "message": { "type": "marketing_tweet_interact", "data": null },
  "delta": false,
  "chunk_id": null
}
```

流式结束后需要**分别查询** `like` 和 `retweet` 两种类型的完整数据：

- `GET /session/marketing/data/{session_id}?type=like` → `resp.like: TweetInMessage[]`
- `GET /session/marketing/data/{session_id}?type=retweet` → `resp.retweet: TweetInMessage[]`

见 [获取营销数据 API](#获取营销数据-getmarketingdatainsession)。

**`writer_twitter`** — 创作营销推文（支持分块流式）

流式传输流程与前两者类似，但需要通过 `draft_id` 区分不同推文：

1. 连续收到 chunk 消息（`delta: true` 且 `chunk_id` 有值）
2. **相同 `draft_id` 的 chunk 属于同一条推文**，只需将 `content` 拼接即可
3. `draft_id` 变化时表示开始创作下一条推文
4. 最终所有 chunk 组成一个推文列表 `TweetWriterData[]`
5. 收到同类型非 chunk 消息时流式结束，调用 API 获取完整数据

chunk 消息示例（同一条推文的两个 chunk，`draft_id` 相同）：

```json
{
  "type": "rich",
  "message": {
    "type": "writer_twitter",
    "data": { "draft_id": "draft_001", "content": "推文内容片段1" }
  },
  "delta": true,
  "chunk_id": "chunk_xxx",
  "chunk_index": 0
}
```

```json
{
  "type": "rich",
  "message": {
    "type": "writer_twitter",
    "data": { "draft_id": "draft_001", "content": "推文内容片段2" }
  },
  "delta": true,
  "chunk_id": "chunk_yyy",
  "chunk_index": 1
}
```

上面两条 `draft_id` 均为 `"draft_001"`，拼接后得到完整的第一条推文内容。

结束消息示例：

```json
{
  "type": "rich",
  "message": { "type": "writer_twitter", "data": null },
  "delta": false,
  "chunk_id": null
}
```

流式结束后调用 API 获取完整数据，见 [获取营销数据 API](#获取营销数据-getmarketingdatainsession)。

**`marketing_report`** — 营销产品分析报告

```json
{ "data": { "product_name": "产品名称", "product_id": "xxx" } }
```

收到此消息后，需通过 API 获取完整报告数据：

- **获取产品信息** `GET /dashboard/product/candidates/{product_id}/info`

```json
// 响应 IProduct
{
  "product_id": "xxx",
  "product_name": "产品名称",
  "status": "completed",
  "analysis_result": { "report_id": "xxx" },
  "has_guided": false,
  "description": "产品描述"
}
```

| 字段                          | 类型                                                  | 说明                                |
| ----------------------------- | ----------------------------------------------------- | ----------------------------------- |
| `status`                    | `"pending" \| "completed" \| "processing" \| "failed"` | 产品分析状态                        |
| `analysis_result.report_id` | string                                                | 报告 ID，用于获取报告详情或保存修改 |

- **获取报告详情** `GET /dashboard/report/info/{report_id}`

```json
// 响应 IMarketingProduct
{
  "id": 1,
  "report_id": "xxx",
  "product_name": "产品名称",
  "target_description": "目标描述",
  "keywords": ["关键词1", "关键词2"],
  "user_personas": ["用户画像1"],
  "user_profiles": ["用户画像描述1"],
  "competitors": ["竞品1"],
  "recommended_campaigns": [{ "name": "活动名", "description": "活动描述" }],
  "related_links": ["https://..."],
  "related_industries": [{ "level1": { "id": 1 }, "level2": [1, 2] }],
  "taxonomy": [
    {
      "level_1": { "id": 1, "name": { "zh": "科技", "en": "Technology" } },
      "level_2": { "id": 2, "name": { "zh": "人工智能", "en": "AI" } }
    }
  ],
  "status": "completed"
}
```

- **保存/修改报告** `POST /dashboard/report/update/{report_id}`

请求体为 `IMarketingProduct` 中除 `report_id`、`product_name`、`id` 外的字段。响应返回 `{ "report_id": "xxx" }`。

**`x_browser_action`** — 浏览器自动化操作

```json
{ "data": { "action_type": "click", "data_id": "xxx", "status": "completed" } }
```

**`marketing_research_tweets`** — 营销匹配的推文（仅供查看）

```json
{ "data": { "query_id": "xxx" } }
```

收到后通过 `query_id` 调用 API 获取完整的匹配推文列表：

`GET /dashboard/product/query/results/{query_id}/lists`

响应为 `TweetInMessage[]`。

**`follow_up_suggestion`** — 后续建议

任务完成后推送，提供用户可执行的后续操作建议。`data` 为 `FollowUpItem[]`：

```json
{
  "data": [
    { "content": "查看详细报告", "display_type": "link", "url": "https://..." },
    { "content": "继续优化推文", "display_type": "button", "url": "" },
    { "content": "分析已完成", "display_type": "text", "url": "" }
  ]
}
```

| 字段             | 类型                                    | 说明                                        |
| ---------------- | --------------------------------------- | ------------------------------------------- |
| `content`      | string                                  | 建议内容文本                                |
| `display_type` | `"link" \| "button" \| "text" \| "bool"` | 展示类型                                    |
| `url`          | string                                  | `display_type` 为 `"link"` 时的跳转链接 |

**`skill`** — 技能调用
skill_name 表示当前正在使用的技能，tool_name 表示使用的tool

```json
{ "data": { "skill_name": "xxx", "tool_name": "xxx" } }
```

---

### 3. 计划消息 `type: "plan"`

渲染计划视图或更新计划状态，通过 `message.type` 区分子类型。

```json
{
  "type": "plan",
  "message_id": "msg_xxx",
  "source": "wyse_mate",
  "source_component": "wyse_agent",
  "content": "",
  "message": {
    "type": "create_plan",
    "data": [{ "id": "1", "title": "Step 1", "description": "...", "status": "" }]
  }
}
```

#### `message.type` 子类型

**`create_plan`** — 创建计划

```json
{ "data": [{ "id": "1", "title": "步骤标题", "description": "...", "status": "" }] }
```

**`update_plan`** — 更新计划

```json
{ "data": [{ "id": "1", "title": "步骤标题", "description": "...", "status": "" }] }
```

**`update_task_status`** — 更新单个步骤的执行状态

```json
{ "data": { "id": "1", "status": "in_progress", "title": "步骤标题" } }
```

| status          | 说明           |
| --------------- | -------------- |
| `in_progress` | 开始执行该步骤 |
| `done`        | 该步骤执行完成 |
| `error`       | 该步骤执行失败 |

---

### 4. 错误消息 `type: "error"`

表示执行过程中的错误。

```json
{
  "type": "error",
  "code": 4200,
  "error": "Service is currently at capacity",
  "message_id": "msg_xxx",
  "source": "system",
  "source_component": "system",
  "content": ""
}
```

| 字段      | 类型   | 说明     |
| --------- | ------ | -------- |
| `code`  | number | 错误码   |
| `error` | string | 错误描述 |

#### 常见错误码

| 错误码   | 说明           | 建议处理     |
| -------- | -------------- | ------------ |
| `4000` | 无效的输入参数 | 检查请求参数 |
| `4200` | 服务容量已满   | 稍后重试     |
| `4201` | 请求频率超限   | 稍后重试     |
| `4202` | 提交任务过多   | 稍后重试     |
| `4203` | 资源未找到     | 检查资源 ID  |
| `4600` | 积分余额不足   | 提示用户充值 |
| `5000` | 服务器内部错误 | 稍后重试     |

---

### 5. 任务结果 `type: "task_result"`

标记任务执行完成。收到此消息后会话进入 `complete` 状态。

```json
{
  "type": "task_result",
  "message_id": "msg_xxx",
  "source": "wyse_mate",
  "source_component": "wyse_agent",
  "content": "任务执行结果内容（markdown）",
  "message": {
    "type": "",
    "data": { "status": "stopped" },
    "metadata": {
      "type": "final_answer"
    }
  }
}
```

| 字段                      | 类型                | 说明                                          |
| ------------------------- | ------------------- | --------------------------------------------- |
| `content`               | string              | 最终结果文本（markdown）                      |
| `message.data.status`   | string?             | 若为 `"stopped"` 表示会话被停止而非正常完成 |
| `message.metadata.type` | `"final_answer"?` | 标记为最终回答                                |

> 收到 `task_result` 后，可能紧接着收到一条 `follow_up_suggestion` 类型的 `rich` 消息，提供后续操作建议。

---

### 6. 请求用户输入 `type: "input"`

服务端请求用户提供输入。

```json
{
  "type": "input",
  "message_id": "msg_xxx",
  "source": "user_proxy",
  "source_component": "wyse_agent",
  "content": "提示文本",
  "session_round": 1,
  "message": {
    "type": "",
    "data": { "request_id": "req_xxx" }
  }
}
```

| 字段                        | 类型                 | 说明                                                                     |
| --------------------------- | -------------------- | ------------------------------------------------------------------------ |
| `message.type`            | `"x_confirm" \| ""` | 输入请求类型。`x_confirm` 表示需要用户确认内容无误开启自动执行插件任务 |
| `message.data.request_id` | string               | **关键字段**，用户回复时必须携带此 ID                              |

---

### 7. 警告消息 `type: "warning"`

可以忽略此类型消息，不影响流程

---

### 8. 进度消息 `type: "progress"`

显示当前执行进度

```json
{
  "type": "progress",
  "message_id": "msg_xxx",
  "source": "wyse_mate",
  "source_component": "wyse_agent",
  "content": "正在执行xxxx..."
}
```

---

## 附录：类型定义速查

### AttachmentType / SessionFileType

```typescript
type SessionFileType = { 
  file_name: string, 
  file_url: string 
};
```

### SkillType

```typescript
type SkillType = { 
  skill_id: string, 
  skill_name: string
}
```

文件附件，用于上传和消息中的文件引用。

### BasicStep

```typescript
type BasicStep = {
  id: string,
  title: string,
  description: string,
  status: "not_started" | "in_progress" | "done" | "skip" | "",
  steps?: BasicStep[],
  agents?: string[]
}
```

### TweetWithReply

```typescript
type TweetWithReply = {
  reply: string,
  tweet: string,
  tweet_id: string,
  username: string,
  tweet_time: string,
  url: string,
  bookmark_count: number,
  favorite_count: number,
  quote_count: number,
  reply_count: number,
  retweet_count: number,
  view_count: number,
  user_profile: {
    avatar_url: string,
    username: string,
    follower_count: number,
    following_count: number
  },
  media?: TweetMedia[]
}

type TweetMedia = {
  url: string,
  type: "photo" | "video" | "gif",
  width: number,
  height: number,
  text_url?: string,
  video_url?: string,
  duration_ms?: number
}
```

### TweetWriterData

```typescript
type TweetWriterData = {
  draft_id: string,
  content: string,
  media?: TweetMedia[]
}
```

### TweetInMessage

```typescript
type TweetInMessage = Omit<TweetWithReply, "reply">
```

即不含 `reply` 字段的推文数据，用于互动（点赞/转推）场景。

### IMarketingProduct

```typescript
interface IMarketingProduct {
  id: number,
  report_id: string,
  product_name: string,
  target_description: string,
  keywords: string[],
  user_personas: string[],
  user_profiles: string[],
  competitors: string[],
  recommended_campaigns: { name: string, description: string }[],
  related_links: string[],
  related_industries?: IndustryConditionBackendType[],
  taxonomy?: IndustryInMessageType[],
  status?: "pending" | "completed" | "processing" | "failed"
}
```

### IndustryInMessageType

```typescript
type IndustryInMessageType = {
  level_1: { id: number, name: { zh: string, en: string } },
  level_2: { id: number, name: { zh: string, en: string } }
}
```

### IndustryConditionBackendType

```typescript
type IndustryConditionBackendType = {
  level1?: { id: number },
  level2?: number[]
}
```

### RichMessageType 枚举

```typescript
enum RichMessageType {
  MarketingReplyTweet = "marketing_tweet_reply",
  MarketingInteractTweet = "marketing_tweet_interact",
  MarketinTweet = "marketing_tweet",
  WriterTwitter = "writer_twitter",
  MarketingTopic = "marketing_topic",
  MarketingReport = "marketing_report",
  FollowUpSuggestion = "follow_up_suggestion",
  MarketingBrowserAction = "x_browser_action",
  MarketingResearchTweets = "marketing_research_tweets",
  Skill = "skill",
}
```
