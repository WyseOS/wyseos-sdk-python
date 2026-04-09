/**
 * Wyse Session Protocol - 营销会话完整交互示例
 *
 * 用法: API_KEY=xxx API_BASE=https://your-api-base PRODUCT_ID=xxx node example-marketing-session.mjs
 */

import WebSocket from "ws"; // npm install ws
import readline from "node:readline";

const API_BASE = process.env.API_BASE;
const API_KEY = process.env.API_KEY;
const PRODUCT_ID = process.env.PRODUCT_ID;
const TASK = process.env.TASK || "给我的产品做一次Twitter营销推广";
const SKILLS = [{ "skill_id": "7ccfb3d7-e6ac-4cda-bce3-030768ef9a9", skill_name: "persona" }]

if (!API_BASE || !API_KEY) {
  console.error("请设置环境变量: API_BASE, API_KEY");
  process.exit(1);
}

// ============ 工具函数 ============

async function api(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "x-api-key": API_KEY,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  if (json.code !== 0) throw new Error(`API error: ${json.code} ${json.msg}`);
  return json.data;
}

function askUser(prompt) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(prompt, (answer) => { rl.close(); resolve(answer); }));
}

// ============ Step 1: 创建营销会话 ============

console.log("→ 创建营销会话...");
let extra = {
  skills: SKILLS,
}
if (PRODUCT_ID) {
  extra.marketing_product = { product_id: PRODUCT_ID };
}
const { session_id } = await api("POST", "/session/create", {
  task: TASK,
  mode: "marketing",
  platform: "api",
  extra,
});
console.log(`  session_id: ${session_id}`);

// ============ Step 2: 连接 WebSocket ============

console.log("→ 连接 WebSocket...");
const wsUrl = `${API_BASE.replace("https", "wss")}/session/ws/${session_id}?api_key=${API_KEY}`;
const ws = new WebSocket(wsUrl);

let lastMsgType = null;
let pingInterval = null;

// ============ 流式 chunk 收集器 ============

// marketing_tweet_reply / marketing_tweet_interact: 每个 chunk 是数组中的一个 item
// writer_twitter: 相同 chunk_index 的 chunk content 需要拼接
const chunkBuffers = {
  marketing_tweet_reply: [],
  marketing_tweet_interact: [],
  writer_twitter: new Map(), // draft_id → { draft_id, content }
};

function handleChunkMessage(richType, msg) {
  const data = msg.message?.data;
  if (!data) return;

  if (richType === "writer_twitter") {
    // 按 draft_id 分组拼接 content
    const draftId = data.draft_id;
    const existing = chunkBuffers.writer_twitter.get(draftId);
    if (existing) {
      existing.content += data.content;
    } else {
      chunkBuffers.writer_twitter.set(draftId, { ...data });
    }
    console.log(`  [chunk] writer_twitter ${draftId}: +${data.content.length} chars`);
  } else {
    // marketing_tweet_reply / marketing_tweet_interact: 每个 chunk 是一条推文
    chunkBuffers[richType].push(data);
    console.log(`  [chunk] ${richType}: 已收到 ${chunkBuffers[richType].length} 条`);
  }
}

async function handleStreamEnd(richType) {
  console.log(`  [stream end] ${richType} 流式结束，请求完整数据...`);

  // 响应结构: { reply: TweetWithReply[], like: TweetInMessage[], retweet: TweetInMessage[], tweet: TweetWriterData[] }

  if (richType === "marketing_tweet_reply") {
    const resp = await api("GET", `/session/marketing/data/${session_id}?type=reply`);
    const fullData = resp.reply || [];
    console.log(`  [reply] 完整数据: ${fullData.length} 条`);
    fullData.forEach((item, i) => {
      console.log(`    ${i + 1}. @${item.username}: "${item.tweet.slice(0, 50)}..." → 回复: "${item.reply.slice(0, 50)}..."`);
    });
  } else if (richType === "marketing_tweet_interact") {
    // interact 的 chunk 同时包含 like 和 retweet，需要分别查询
    const [likeResp, retweetResp] = await Promise.all([
      api("GET", `/session/marketing/data/${session_id}?type=like`),
      api("GET", `/session/marketing/data/${session_id}?type=retweet`),
    ]);
    const likes = likeResp.like || [];
    const retweets = retweetResp.retweet || [];
    console.log(`  [interact] 点赞: ${likes.length} 条, 转推: ${retweets.length} 条`);
    likes.forEach((item, i) => {
      console.log(`    [like] ${i + 1}. @${item.username}: "${item.tweet.slice(0, 80)}..."`);
    });
    retweets.forEach((item, i) => {
      console.log(`    [retweet] ${i + 1}. @${item.username}: "${item.tweet.slice(0, 80)}..."`);
    });
  } else if (richType === "writer_twitter") {
    const resp = await api("GET", `/session/marketing/data/${session_id}?type=tweet`);
    const fullData = resp.tweet || [];
    console.log(`  [tweet] 完整数据: ${fullData.length} 条`);
    fullData.forEach((item, i) => {
      console.log(`    ${i + 1}. [${item.draft_id}] ${item.content.slice(0, 80)}...`);
    });
  }

  // 清空 buffer
  if (richType === "writer_twitter") {
    chunkBuffers.writer_twitter.clear();
  } else {
    chunkBuffers[richType] = [];
  }
}

// ============ 营销报告处理 ============

async function handleMarketingReport(data) {
  const { product_id, product_name } = data;
  console.log(`  [report] 产品: ${product_name} (${product_id})`);
 
  // 获取产品信息 → 拿到 report_id
  console.log("  → 获取产品信息...");
  const product = await api("GET", `/dashboard/product/candidates/${product_id}/info`);
  console.log(`    状态: ${product.status}`);

  if (product.status === "completed" && product.analysis_result?.report_id) {
    // 获取报告详情
    console.log("  → 获取报告详情...");
    const report = await api("GET", `/dashboard/report/info/${product.analysis_result.report_id}`);
    console.log(`    目标: ${report.target_description}`);
    console.log(`    关键词: ${report.keywords?.join(", ")}`);
    console.log(`    用户画像: ${report.user_personas?.join(", ")}`);
    console.log(`    竞品: ${report.competitors?.join(", ")}`);
    console.log(`    推荐活动: ${report.recommended_campaigns?.map((c) => c.name).join(", ")}`);
  } else {
    console.log(`    产品分析尚未完成 (${product.status})`);
  }
}

// ============ 营销调研推文处理 ============

async function handleResearchTweets(data) {
  const { query_id } = data;
  console.log(`  [research] query_id: ${query_id}`);
  console.log("  → 获取匹配推文...");
  const tweets = await api("GET", `/dashboard/product/query/results/${query_id}/lists`);
  console.log(`    匹配到 ${tweets.length} 条推文:`);
  tweets.slice(0, 5).forEach((t, i) => {
    console.log(`    ${i + 1}. @${t.username}: "${t.tweet.slice(0, 60)}..." (${t.favorite_count} likes)`);
  });
  if (tweets.length > 5) console.log(`    ... 还有 ${tweets.length - 5} 条`);
}

// ============ WebSocket 消息处理 ============

ws.on("open", () => {
  console.log("  WebSocket 已连接");

  pingInterval = setInterval(() => {
    ws.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
  }, 30000);

  // Step 3: 发送 start
  console.log("→ 发送 start...");
  ws.send(
    JSON.stringify({
      type: "start",
      data: {
        messages: [{ type: "task", content: TASK }],
        attachments: [],
        extra,
      },
    })
  );
});

ws.on("message", (raw) => {
  const msg = JSON.parse(raw.toString());

  switch (msg.type) {
    case "pong":
      break;

    case "text":
      console.log(`[text] ${msg.content?.slice(0, 100)}`);
      break;

    case "progress":
      console.log(`[progress] ${msg.content}`);
      break;

    // ---- 计划消息 ----
    case "plan": {
      const subType = msg.message?.type;
      if (subType === "create_plan") {
        const steps = msg.message.data;
        console.log(`[plan] 创建计划，共 ${steps.length} 步:`);
        steps.forEach((s) => console.log(`  - ${s.title}`));
      } else if (subType === "update_task_status") {
        const { id, title, status } = msg.message.data;
        console.log(`[plan] 步骤 ${id} "${title}" → ${status}`);
      } else if (subType === "update_plan") {
        console.log(`[plan] 计划已更新`);
      }
      break;
    }

    // ---- 请求用户输入 ----
    case "input": {
      const requestId = msg.message?.data?.request_id;
      const msgType = msg.message?.type;
      console.log(`[input] 服务端请求输入 (request_id: ${requestId}, message.type: ${msgType})`);

      if (msgType === "x_confirm") {
        // 插件自动执行确认 → 自动同意
        console.log("→ 自动确认执行...");
        // ws.send(
        //   JSON.stringify({
        //     type: "input",
        //     data: {
        //       input_type: "plan",
        //       request_id: requestId,
        //       response: { accepted: true, content: "" },
        //     },
        //   })
        // );
      } else if (lastMsgType === "plan") {
        // 上一条是 plan → 自动确认计划
        console.log("→ 自动确认计划...");
        ws.send(
          JSON.stringify({
            type: "input",
            data: {
              input_type: "plan",
              request_id: requestId,
              response: { accepted: true, plan: [], content: "" },
            },
          })
        );
      } else if (msg.source === "marketing_analyst") {
        // 营销场景：产品分析报告确认，等待用户确认或补充产品信息
        console.log(`[input] 产品分析确认 (source: marketing_analyst)`);
        askUser("确认产品信息后将继续: ").then((text) => {
          ws.send(
            JSON.stringify({
              type: "input",
              data: {
                input_type: "text",
                text,
                request_id: requestId,
                attachments: [],
                skills: [],
              },
            })
          );
        });
      } else {
        // 其他 → 等待用户终端输入
        askUser("请输入回复内容: ").then((text) => {
          ws.send(
            JSON.stringify({
              type: "input",
              data: {
                input_type: "text",
                text,
                request_id: requestId,
                attachments: [],
                skills: [],
              },
            })
          );
        });
      }
      break;
    }

    // ---- 富文本消息（营销核心逻辑） ----
    case "rich": {
      const richType = msg.message?.type;
      const isChunk = msg.delta === true && msg.chunk_id;

      // --- 流式营销消息 ---
      if (richType === "marketing_tweet_reply" || richType === "marketing_tweet_interact" || richType === "writer_twitter") {
        if (isChunk) {
          handleChunkMessage(richType, msg);
        } else {
          // 非 chunk = 流式结束
          handleStreamEnd(richType);
        }
        break;
      }

      // --- 营销报告 ---
      if (richType === "marketing_report") {
        try {
          handleMarketingReport(msg.message.data);
        } catch (error) {
          console.error("Read marketing report failed", error);
        }
        break;
      }

      // --- 营销调研推文 ---
      if (richType === "marketing_research_tweets") {
        try {
          handleResearchTweets(msg.message.data);
        } catch (error) {
          console.error("Read tweets result failed", error);
        }
        break;
      }

      // --- 其他 rich 消息 ---
      console.log(`[rich:${richType}] ${msg.content?.slice(0, 80) || "(structured data)"}`);
      break;
    }

    case "error":
      console.error(`[error] code=${msg.code} ${msg.error}`);
      break;

    case "task_result":
      console.log(`[task_result] 任务完成`);
      if (msg.content) console.log(`  结果: ${msg.content.slice(0, 200)}`);
      setTimeout(() => ws.close(), 2000);
      break;

    case "warning":
      break;

    default:
      console.log(`[${msg.type}] (未处理的消息类型)`);
  }

  lastMsgType = msg.type;
});

ws.on("close", () => {
  console.log("WebSocket 已断开");
  clearInterval(pingInterval);
  process.exit(0);
});

ws.on("error", (err) => {
  console.error("WebSocket 错误:", err.message);
  clearInterval(pingInterval);
  process.exit(1);
});
