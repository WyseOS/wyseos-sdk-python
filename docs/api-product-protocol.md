# 产品分析接口

创建产品分为三步：

1. 调用创建接口，提交产品信息
2. 根据返回的 `product_id` 轮询查询产品状态，直到 `status` 为 `completed` 且 `analysis_result.report_id` 存在，表示产品生成成功
3. 使用 `report_id` 获取完整的产品分析报告

---

## 第一步：创建产品

### POST `/dashboard/product/create`

#### Request

**Content-Type:** `application/json`

| 字段            | 类型             | 必填 | 说明                                              |
| --------------- | ---------------- | ---- | ------------------------------------------------- |
| `product`     | `string`       | 是   | 产品名称或产品相关链接地址                        |
| `attachments` | `Attachment[]` | 否   | 附件列表，通过 `/session/upload` 接口上传后获取 |

**Attachment 对象：**

| 字段          | 类型       | 必填 | 说明            |
| ------------- | ---------- | ---- | --------------- |
| `file_name` | `string` | 是   | 文件名          |
| `file_url`  | `string` | 是   | 文件地址（URL） |

#### Request 示例

使用产品名称：

```json
{
  "product": "My Product",
  "attachments": [
    {
      "file_name": "intro.pdf",
      "file_url": "https://example.com/files/intro.pdf"
    }
  ]
}
```

使用产品链接：

```json
{
  "product": "https://www.example.com/my-product",
  "attachments": []
}
```

---

### 附件上传：POST `/session/upload`

创建产品时如需附带附件，需先通过此接口上传文件，再将返回的 `file_name` 和 `file_url` 填入创建产品请求的 `attachments` 字段。

#### Request

**Content-Type:** `multipart/form-data`

| 字段      | 类型       | 必填 | 说明                                               |
| --------- | ---------- | ---- | -------------------------------------------------- |
| `files` | `File[]` | 是   | 要上传的文件（支持多个，使用同一字段名 `files`） |

#### Response

返回上传成功的文件信息数组：

```json
[
  {
    "file_name": "intro.pdf",
    "file_url": "https://storage.example.com/uploads/intro.pdf"
  }
]
```

#### 完整流程

```
1. 调用 POST /session/upload 上传文件
   → 获得 [{ file_name, file_url }]

2. 调用 POST /dashboard/product/create
   → 将上传结果填入 attachments 字段
   → 获得 { product_id }

3. 轮询 GET /dashboard/product/candidates/${product_id}/info
   → 判断生成状态
   → 生成成功后获得 analysis_result.report_id

4. 调用 GET /dashboard/report/info/${report_id}
   → 获取完整产品分析报告
```

#### Response

| 字段             | 类型                | 说明     |
| ---------------- | ------------------- | -------- |
| `product_id`   | `number \| string` | 产品 ID  |
| `product_name` | `string`          | 产品名称 |
| `status`       | `string`          | 产品状态 |

#### Response 示例

```json
{
  "product_id": 123,
  "product_name": "My Product",
  "status": "pending"
}
```

---

## 第二步：轮询产品状态

### GET `/dashboard/product/candidates/${product_id}/info`

使用第一步返回的 `product_id`，轮询此接口查询产品生成状态。

#### Path 参数

| 参数           | 类型       | 说明                |
| -------------- | ---------- | ------------------- |
| `product_id` | `string` | 第一步返回的产品 ID |

#### Response

| 字段                          | 类型                    | 说明                                  |
| ----------------------------- | ----------------------- | ------------------------------------- |
| `product_id`                | `string`              | 产品 ID                               |
| `product_name`              | `string`              | 产品名称                              |
| `status`                    | `string`              | 产品状态：`pending` / `completed` |
| `analysis_result`           | `object \| undefined`  | 分析结果，生成完成后存在              |
| `analysis_result.report_id` | `string`              | 报告 ID                               |
| `has_guided`                | `boolean \| undefined` | 是否已引导                            |
| `description`               | `string \| undefined`  | 产品描述                              |

#### Response 示例

```json
{
  "product_id": "123",
  "product_name": "My Product",
  "status": "completed",
  "analysis_result": {
    "report_id": "rpt_abc123"
  }
}
```

#### 状态判断逻辑

```
轮询开始
  │
  ├─ status == "completed" && analysis_result.report_id 存在
  │    → 生成成功，停止轮询
  │
  ├─ status == "completed" && analysis_result.report_id 不存在
  │    → 生成失败，停止轮询
  │
  └─ status == "pending"
       → 继续轮询（建议间隔 20 秒）
```

---

## 第三步：获取产品报告

### GET `/dashboard/report/info/${report_id}`

产品生成成功后，使用第二步中获取到的 `analysis_result.report_id` 调用此接口，获取完整的产品分析报告。

#### Path 参数

| 参数          | 类型       | 说明                                       |
| ------------- | ---------- | ------------------------------------------ |
| `report_id` | `string` | 第二步返回的 `analysis_result.report_id` |

#### Response

| 字段                      | 类型                    | 说明             |
| ------------------------- | ----------------------- | ---------------- |
| `report_id`             | `string`              | 报告唯一标识     |
| `product_name`          | `string`              | 产品名称         |
| `target_description`    | `string`              | 目标描述         |
| `keywords`              | `string[]`            | 关键词列表       |
| `user_personas`         | `string[]`            | 典型用户画像     |
| `user_profiles`         | `string[]`            | 用户画像         |
| `competitors`           | `string[]`            | 竞品列表         |
| `recommended_campaigns` | `Campaign[]`          | 推荐营销活动     |
| `related_links`         | `string[]`            | 相关链接         |
| `related_industries`    | `IndustryCondition[]` | 相关行业（可选） |

**IndustryCondition 对象：**

| 字段       | 类型               | 说明                     |
| ---------- | ------------------ | ------------------------ |
| `level1` | `{ id: number }` | 一级行业（可选）         |
| `level2` | `number[]`       | 二级行业 ID 列表（可选） |

行业 ID 可通过 `GET /dashboard/categories` 接口获取，详见下方。

**Campaign 对象：**

| 字段            | 类型       | 说明     |
| --------------- | ---------- | -------- |
| `name`        | `string` | 活动名称 |
| `description` | `string` | 活动描述 |

#### Response 示例

```json
{
  "report_id": "rpt_abc123",
  "product_name": "My Product",
  "target_description": "A SaaS tool for marketing automation",
  "keywords": ["marketing", "automation", "SaaS"],
  "user_personas": ["Growth Marketer", "Startup Founder"],
  "user_profiles": ["25-40 age", "Tech-savvy"],
  "competitors": ["Competitor A", "Competitor B"],
  "recommended_campaigns": [
    {
      "name": "Product Launch Campaign",
      "description": "Leverage Twitter threads to announce product features"
    }
  ],
  "related_links": ["https://example.com/resource"],
  "related_industries": [
    {
      "level1": { "id": 1 },
      "level2": [101, 102]
    }
  ],
  "status": "completed"
}
```

---

## 附录：获取行业数据

### GET `/dashboard/categories`

获取完整的行业分类列表，用于解析产品报告中 `related_industries` 的行业 ID。

#### Response

返回 `IIndustry[]` 数组：

| 字段              | 类型           | 说明                 |
| ----------------- | -------------- | -------------------- |
| `category`      | `Category`   | 一级行业             |
| `subcategories` | `Category[]` | 二级行业列表（可选） |

**Category 对象：**

| 字段        | 类型       | 说明           |
| ----------- | ---------- | -------------- |
| `id`      | `number` | 行业 ID        |
| `zh`      | `string` | 中文名称       |
| `en`      | `string` | 英文名称       |
| `en_desc` | `string` | 英文描述       |
| `level`   | `number` | 层级（1 或 2） |

#### Response 示例

```json
[
  {
    "category": {
      "id": 1,
      "zh": "科技",
      "en": "Technology",
      "en_desc": "Technology industry",
      "level": 1
    },
    "subcategories": [
      {
        "id": 101,
        "zh": "人工智能",
        "en": "Artificial Intelligence",
        "en_desc": "AI and machine learning",
        "level": 2
      }
    ]
  }
]
```
