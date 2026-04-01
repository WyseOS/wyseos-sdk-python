/**
 * Wyse Session Protocol - 最简完整交互示例
 *
 * 用法: API_KEY=wyse_ak_xxx API_BASE=https://your-api-base node example-session.mjs
 */

import WebSocket from "ws"; // npm install ws
import readline from "node:readline";

const API_BASE = process.env.API_BASE;
const API_KEY = process.env.API_KEY;
const TASK = process.env.TASK || "帮我搜索最近的AI新闻";

if (!API_BASE || !API_KEY) {
  console.error("请设置环境变量: API_BASE, API_KEY");
  process.exit(1);
}


// ============ Step 1: 创建会话 ============

console.log("→ 创建会话...");
const { session_id } = await api("POST", "/session/create", {
  task: TASK,
  platform: "api",
});
console.log(`  session_id: ${session_id}`);

// ============ Step 2: 连接 WebSocket（使用 API Key header 认证） ============

console.log("→ 连接 WebSocket...");
const wsUrl = `${API_BASE.replace("https", "wss")}/session/ws/${session_id}?api_key=${API_KEY}`;
const ws = new WebSocket(wsUrl);

let lastRequestId = null; // 记录最近一次 input 的 request_id
let lastMsgType = null; // 记录上一条消息的 type，用于判断 input 类型
let pingInterval = null;

// 从终端读取用户输入
function askUser(prompt) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(prompt, (answer) => { rl.close(); resolve(answer); }));
}

ws.on("open", () => {
  console.log("  WebSocket 已连接");

  // 启动心跳
  pingInterval = setInterval(() => {
    ws.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
  }, 30000);

  // Step 3: 发送 start 消息
  console.log("→ 发送 start...");
  ws.send(
    JSON.stringify({
      type: "start",
      data: {
        messages: [{ type: "task", content: TASK }],
        attachments: [],
        skills: [],
      },
    })
  );
});

ws.on("message", (raw) => {
  const msg = JSON.parse(raw.toString());

  switch (msg.type) {
    // ---- 心跳响应 ----
    case "pong":
      break;

    // ---- 纯文本消息 ----
    case "text":
      console.log(`[text] ${msg.content?.slice(0, 100)}`);
      break;

    // ---- 进度消息 ----
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
      lastRequestId = requestId;
      console.log(`[input] 服务端请求输入 (request_id: ${requestId})`);

      if (lastMsgType === "plan") {
        // 上一条是 plan，自动确认
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
      } else {
        // 非 plan，等待用户在终端输入
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

    // ---- 富文本消息 ----
    case "rich": {
      const richType = msg.message?.type;
      console.log(`[rich:${richType}] ${msg.content?.slice(0, 80) || "(structured data)"}`);
      break;
    }

    // ---- 错误消息 ----
    case "error":
      console.error(`[error] code=${msg.code} ${msg.error}`);
      break;

    // ---- 任务完成 ----
    case "task_result":
      console.log(`[task_result] 任务完成`);
      if (msg.content) console.log(`  结果: ${msg.content.slice(0, 200)}`);
      // 任务结束，关闭连接
      setTimeout(() => ws.close(), 2000);
      break;

    // ---- 警告（忽略）----
    case "warning":
      break;

    default:
      console.log(`[${msg.type}] (未处理的消息类型)`);
  }

  // 记录上一条消息类型（用于判断 input 场景）
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
