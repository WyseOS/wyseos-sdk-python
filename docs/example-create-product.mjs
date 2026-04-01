/**
 * 创建产品并获取产品报告详情 - 完整示例
 *
 * 用法:
 *   API_KEY=wyse_ak_xxx API_BASE=https://your-api-base node example-create-product.mjs
 *
 * 可选环境变量:
 *   PRODUCT_NAME  - 产品名称或产品链接（默认: "Notion"）
 *   POLL_INTERVAL - 轮询间隔毫秒数（默认: 20000）
 */

const API_BASE = process.env.API_BASE;
const API_KEY = process.env.API_KEY;
const PRODUCT_NAME = process.env.PRODUCT_NAME || "Notion";
const POLL_INTERVAL = Number(process.env.POLL_INTERVAL) || 20000;

if (!API_BASE || !API_KEY) {
  console.error("请设置环境变量: API_BASE, API_KEY");
  process.exit(1);
}

// ============ 工具函数 ============

async function api(method, path, body) {
  const options = {
    method,
    headers: {
      "x-api-key": API_KEY,
      "Content-Type": "application/json",
    },
  };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, options);
  const json = await res.json();
  if (json.code !== 0) throw new Error(`API error: ${json.code} ${json.msg}`);
  return json.data;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============ Step 1: 创建产品 ============

console.log(`→ 创建产品: "${PRODUCT_NAME}"`);

const product = await api("POST", "/dashboard/product/create", {
  product: PRODUCT_NAME,
  attachments: [],
});

const productId = product.product_id;
console.log(`  product_id: ${productId}`);
console.log(`  product_name: ${product.product_name}`);
console.log(`  status: ${product.status}`);

// ============ Step 2: 轮询产品状态 ============

console.log(`\n→ 开始轮询产品状态（间隔 ${POLL_INTERVAL / 1000}s）...`);

let reportId = null;
let pollCount = 0;

while (true) {
  pollCount++;
  const info = await api("GET", `/dashboard/product/candidates/${productId}/info`);
  console.log(`  [第${pollCount}次] status: ${info.status}`);

  if (info.status === "completed") {
    if (info.analysis_result?.report_id) {
      reportId = info.analysis_result.report_id;
      console.log(`  ✓ 生成成功, report_id: ${reportId}`);
    } else {
      console.error("  ✗ 生成失败: status 为 completed 但无 report_id");
      process.exit(1);
    }
    break;
  }

  // status == "pending"，继续轮询
  await sleep(POLL_INTERVAL);
}

// ============ Step 3: 获取产品报告 ============
console.log(`\n→ 获取产品报告: ${reportId}`);

const report = await api("GET", `/dashboard/report/info/${reportId}`);

console.log("\n========== 产品报告 ==========");
console.log(`产品名称:     ${report.product_name}`);
console.log(`目标描述:     ${report.target_description}`);
console.log(`关键词:       ${report.keywords?.join(", ")}`);
console.log(`竞品:         ${report.competitors?.join(", ")}`);
console.log(`相关链接:     ${report.related_links?.join(", ")}`);

if (report.user_personas.length) {
  console.log(`\n典型用户画像:`);
  report.user_personas.forEach((c, i) => {
    console.log(`  ${i + 1}. ${c}`);
  });
}
if (report.user_profiles.length) {
  console.log(`\n用户画像:`);
  report.user_profiles.forEach((c, i) => {
    console.log(`  ${i + 1}. ${c}`);
  });
}

if (report.recommended_campaigns?.length) {
  console.log(`\n推荐营销活动:`);
  report.recommended_campaigns.forEach((c, i) => {
    console.log(`  ${i + 1}. ${c.name} - ${c.description}`);
  });
}

if (report.related_industries?.length) {
  console.log(`\n相关行业:`);
  report.related_industries.forEach((ind, i) => {
    console.log(`  ${i + 1}. level1: ${ind.level1?.id}, level2: [${ind.level2?.join(", ")}]`);
  });
}

console.log("\n========== 完成 ==========");
