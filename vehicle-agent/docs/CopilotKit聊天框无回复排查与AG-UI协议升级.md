# 调试记录：CopilotKit 聊天框无回复排查与 AG-UI 协议升级

> **时间**：2026年6月19日  
> **项目**：vehicle-agent（AutoMind 车机智能助手）  
> **严重度**：高（核心功能完全不可用）

---

## 一、问题现象

前端 CopilotKit 聊天界面能正常渲染，用户输入"你好"后：
- 后端**没有报错**
- 前端**不显示 AI 的回复**
- 消息似乎"发出去了"，但没有渲染成助手消息

---

## 二、排查过程

### 第一阶段：初始排查（走了弯路）

**初始思路**：以为问题出在 ai-server（独立的 AI 对话服务），去查看 `ai-server/logs/app.log`。

**发现问题**：
- 日志显示的后端配置还是旧的 OpenAI 配置（`api.openai.com`），`.env` 已改为百炼平台
- 端口 8000（ai-server 默认端口）没有进程监听
- **误判**：以为 ai-server 没运行导致前端无回复

**用户纠正**：用户指出问题出在**车机软件界面**（vehicle-agent），不是 ai-server。排查方向完全搞错了。

---

### 第二阶段：聚焦 vehicle-agent，测试后端

重新聚焦到 vehicle-agent 的架构：
- **后端**：`vehicle-agent/backend`（端口 8001），使用 CopilotKit Python SDK + LangGraph
- **前端**：`vehicle-agent/frontend`（端口 5173），使用 CopilotKit React（v1.5.20）
- **连接**：Vite 代理 `/copilotkit` → `localhost:8001`

**后端直连测试（关键一步）**：

绕过前端，直接用 Python 脚本调用后端 LangGraph 图：

```python
# 测试脚本：直接调用 LangGraph 图，绕过 CopilotKit
result = await graph.ainvoke({"messages": [HumanMessage(content="你好")]})
print(result)
```

**结果**：LangGraph 图**完全正常**，能正确返回 AI 回复。

**流式接口测试**：

```python
async for event in graph.astream_events(...):
    print(event)
```

**结果**：流式输出也**完全正常**。

**结论**：后端 LangGraph 图本身没有问题，问题出在 **CopilotKit 中间层**。

---

### 第三阶段：发现前端 CopilotKit 版本问题

**检查前端版本**：`package.json` 中 `@copilotkit/react-ui` 版本是 `1.5.20`。

**检查前端网络请求**：发现 CopilotKit v1.5 前端使用 `urql` 的 GraphQL `@stream/@defer` 指令做流式传输。

**检查后端端点**：Python CopilotKit SDK 注册的是 REST 端点（`CopilotKitRemoteEndpoint`）。

**对比发现协议不匹配**：

| 层面 | 前端期望 | 后端实际提供 |
|------|----------|--------------|
| 协议 | GraphQL multipart incremental（`@stream/@defer`） | REST streaming JSON |
| 格式 | `incremental` + `path` 字段做增量合并 | 逐行 JSON 流 |
| 客户端 | urql GraphQL client | 普通 HTTP fetch |

**两者完全不兼容**，这是架构层面的问题，不是配置问题。

---

### 第四阶段：尝试修复自定义 GraphQL 适配器

**发现**：项目中有一个 671 行的自定义 GraphQL 适配器（`graphql_adapter.py`），用来桥接前端的 GraphQL 请求和后端的 REST 响应。

**尝试修复方向**：
- 修复 `content` 字段格式（数组 vs 字符串）
- 确保每个 chunk 都包含 `role` 字段
- 调整 multipart 响应格式

**结果**：始终无法完美实现 urql 期望的 multipart incremental 格式，消息角色持续丢失。

**根本原因确认**：urql 的 `@stream/@defer` multipart incremental 格式极其复杂，自定义适配器很难完美实现。这是 CopilotKit 前端（v1.5+）和 Python SDK（0.1.x）之间的**协议断层**。

---

### 第五阶段：调研业界标准方案

**调研发现**：CopilotKit 官方已经推出了新一代标准协议 —— **AG-UI Protocol**（Agent-User Interaction Protocol）。

- **协议特点**：HTTP POST + SSE（Server-Sent Events），比 GraphQL multipart 简单得多
- **生态支持**：已被 Google、LangChain、AWS、Microsoft 采纳
- **Python SDK**：`ag-ui-langgraph` 包，`add_langgraph_fastapi_endpoint` 一行代码注册 SSE 端点
- **前端 SDK**：`@ag-ui/client` 包，`HttpAgent` 直连 SSE 端点

**决策**：放弃自定义 GraphQL 适配器，全面升级到 AG-UI SSE 协议。

---

## 三、解决方案

### 后端改造（`vehicle-agent/backend/app/main.py`）

```python
# ===== 改造前（自定义 GraphQL 适配器）=====
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from app.utils.graphql_adapter import register_graphql_endpoint

sdk = CopilotKitRemoteEndpoint(
    agents=[LangGraphAGUIAgent(name="automind", graph=get_graph())],
)
register_graphql_endpoint(app, sdk, "/copilotkit")

# ===== 改造后（AG-UI SSE 标准端点）=====
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

agent = LangGraphAgent(
    name="automind",
    description="AutoMind 智能车机助手 - 支持导航、音乐、车辆控制、天气、提醒",
    graph=await get_graph(),
)
add_langgraph_fastapi_endpoint(app, agent, "/agent")
```

### 前端改造（`vehicle-agent/frontend/src/App.tsx`）

```tsx
// ===== 改造前（CopilotKit v1.5 GraphQL）=====
import { CopilotKit } from "@copilotkit/react-core";
<CopilotKit runtimeUrl="/copilotkit" agent="automind">

// ===== 改造后（CopilotKit v1.61+ AG-UI SSE）=====
import { CopilotKit } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";

const automindAgent = new HttpAgent({ url: "/agent" });

<CopilotKit agents__unsafe_dev_only={{ default: automindAgent }}>
```

### 前端依赖升级（`vehicle-agent/frontend/package.json`）

```json
{
  "@copilotkit/react-core": "^1.61.0",
  "@copilotkit/react-ui": "^1.61.0",
  "@ag-ui/client": "^0.0.15"
}
```

### Vite 代理更新（`vehicle-agent/frontend/vite.config.ts`）

```ts
// 改造前
proxy: { '/copilotkit': { target: 'http://localhost:8001', changeOrigin: true } }

// 改造后
proxy: { '/agent': { target: 'http://localhost:8001', changeOrigin: true } }
```

### 删除文件

- `vehicle-agent/backend/app/utils/graphql_adapter.py`（671 行自定义 GraphQL 适配器）
- 7 个调试测试脚本（`test_chat.py`、`test_llm.py`、`test_graph.py`、`test_stream.py`、`test_agent.py`、`test_gql_stream.py`、`test_fix.py`）

---

## 四、实施过程中遇到的坑

### 坑1：`@copilotkit/react-ui/v2` 模块不存在

**现象**：`import { CopilotPopup } from "@copilotkit/react-ui/v2"` 报错。

**原因**：v1.61 的 `@copilotkit/react-ui` 包没有 `v2` JS 导出（只有 `v2/styles.css`）。

**修复**：改为 `import { CopilotPopup } from "@copilotkit/react-ui"`（主入口），CSS 保持 `@copilotkit/react-ui/v2/styles.css`。

---

### 坑2：`@ag-ui/client` 包未安装

**现象**：`npm install` 后 `@ag-ui/client` 不在 `node_modules` 中。

**原因**：该包被声明为 `@copilotkit/react-core` 的依赖，但没有自动安装到独立目录。

**修复**：手动安装 `npm install @ag-ui/client@0.0.57`。

---

### 坑3：端口 8001 被旧进程占用

**现象**：重启后端时报 `Address already in use`。

**修复**：`Stop-Process -Id <PID> -Force` 杀掉旧进程后重启。

---

### 坑4：Agent key 必须是 `default`

**现象**：升级后前端报错 `useAgent: Agent 'default' not found after runtime sync (no runtimeUrl). Known agents: [automind]`。

**原因**：CopilotPopup v1.61 默认查找名为 `default` 的 agent，但注册时 key 是 `automind`。

**修复**：将 `agents__unsafe_dev_only={{ automind: automindAgent }}` 改为 `agents__unsafe_dev_only={{ default: automindAgent }}`。

---

## 五、最终验证

### 后端 SSE 端点测试

```bash
# 健康检查
curl http://localhost:8001/api/vehicle/health
# → {"status": "ok", "agent": "automind"}

# SSE 流式测试（返回标准 AG-UI 事件）
curl -X POST http://localhost:8001/agent -d '{"run_id":"test","thread_id":"t1","messages":[{"role":"user","content":"你好"}]}'
# → RUN_STARTED → TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT → TEXT_MESSAGE_END → RUN_FINISHED
```

### 前端聊天测试

打开 http://localhost:5175，点击聊天按钮，输入"你好"，AI 正确回复并渲染为助手消息。

---

## 六、经验总结

### 排查方法论

```
问题现象（前端无回复）
  ↓
第一步：确认问题范围（是 ai-server 还是 vehicle-agent？）→ 用户纠正
  ↓
第二步：绕过中间层，直连底层测试（LangGraph 图是否正常）→ 正常
  ↓
第三步：缩小范围，测试中间层（CopilotKit SDK 流式输出）→ 正常
  ↓
第四步：对比前后端协议（GraphQL vs REST）→ 发现协议断层
  ↓
第五步：调研业界标准方案（AG-UI Protocol）→ 找到根本解法
  ↓
第六步：全面升级协议，删除自定义适配器
```

### 核心教训

1. **先确认问题范围再排查**：一开始搞错了方向（查 ai-server 而不是 vehicle-agent），浪费了大量时间
2. **自底向上逐层验证**：先测最底层的 LangGraph 图，再测中间层，最后看前端，逐层排除
3. **协议断层问题不要硬补**：自定义 GraphQL 适配器 671 行代码仍然不完美，升级到标准协议才是正道
4. **升级要读官方文档**：AG-UI 是 CopilotKit 官方推荐的新一代协议，不是野路子

### 涉及文件清单

| 文件 | 改动说明 |
|------|----------|
| `vehicle-agent/backend/app/main.py` | CopilotKit REST → AG-UI SSE 端点 |
| `vehicle-agent/backend/app/utils/graphql_adapter.py` | **已删除**（671 行自定义 GraphQL 适配器） |
| `vehicle-agent/frontend/src/App.tsx` | CopilotKit v1.5 GraphQL → v1.61+ AG-UI SSE |
| `vehicle-agent/frontend/package.json` | 升级 CopilotKit 到 v1.61，新增 `@ag-ui/client` |
| `vehicle-agent/frontend/vite.config.ts` | 代理路径 `/copilotkit` → `/agent` |
