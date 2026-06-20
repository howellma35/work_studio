# AutoMind 启动链路连环踩坑记录

> 从 asyncio 事件循环冲突到 CopilotKit 前后端协议断层，记录一次完整的"修一个 bug 冒出三个"排查历程。

---

## 背景

AutoMind 车机智能助手基于 LangGraph + CopilotKit + FastAPI 构建。前端使用 `@copilotkit/react-core` 提供聊天界面，后端使用 Python `copilotkit` SDK 注册 Agent 端点。

项目已经写好但从未成功启动过，本次会话的目标是：**让后端能启动，前端能聊天**。

最终经历了 **7 个连环问题**，逐个排查修复。

---

## 问题一：asyncio 事件循环嵌套

### 发现

启动后端直接崩溃，报错：

```
RuntimeError: Cannot run the event loop while another loop is running
RuntimeError: asyncio.run() cannot be called from a running event loop
Application startup failed. Exiting.
```

### 排查

看报错栈：

```
supervisor.py:78  _load_mcp_tools_sync()
  → loop.run_until_complete(load_mcp_tools())   ← 第一次尝试失败
  → asyncio.run(load_mcp_tools())               ← 兜底也失败
```

原因：FastAPI 的 `lifespan` 是异步上下文管理器，运行在 uvicorn **已经启动的事件循环**内。而 `_load_mcp_tools_sync()` 试图创建新的事件循环来"同步地"执行异步代码 `load_mcp_tools()`。Python 不允许在已有循环中再创建循环。

### 为什么原代码这么写

`build_supervisor_graph()` 原本是同步函数（因为 LangGraph 的 `create_supervisor` / `compile` 都是同步 API），但它需要调用异步的 `load_mcp_tools()`（网络 IO）。作者不想改整个调用链签名，就写了个同步包装器"桥接"。

这在直接用 `python main.py`（uvicorn 还没创建循环时）可能能跑，但在正式通过 lifespan 启动时就炸了。

### 修复

**删除同步包装器，一路 async/await 传下去：**

```python
# 修复前
def build_supervisor_graph() -> CompiledStateGraph:
    tools = _load_mcp_tools_sync()  # ← 同步包装，试图创建新事件循环
    ...

def _load_mcp_tools_sync():
    loop = asyncio.new_event_loop()
    tools = loop.run_until_complete(load_mcp_tools())
    loop.close()
    return tools

# 修复后
async def build_supervisor_graph() -> CompiledStateGraph:
    tools = await load_mcp_tools()  # ← 直接 await，共用同一个事件循环
    ...

async def get_graph() -> CompiledStateGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = await build_supervisor_graph()
    return _graph_instance
```

`main.py` 中调用处也加 `await`：

```python
await get_graph()  # 不再是 get_graph()
```

### 教训

> 在 FastAPI/Starlette 的 lifespan、路由 handler 等**已经在事件循环内的异步上下文**中，**绝对不能**用 `asyncio.run()`、`loop.run_until_complete()` 等同步包装器。正确做法是**一路 async/await 传下去**。

---

## 问题二：CopilotKit 路由 404

### 发现

修完 asyncio 后，后端能启动了，但前端聊天输入没反应，报错：

```
Code: agent_run_failed
Message: HTTP 404: {"detail":"Not Found"}
```

### 排查

前端 Vite 代理配置 `/copilotkit` → `http://localhost:8001`，端口匹配。后端日志显示 `POST /copilotkit/` 返回 200，但实际聊天请求返回 404。

查看代码发现 CopilotKit 注册在 `@app.on_event("startup")` 中：

```python
@app.on_event("startup")
async def register_copilotkit():
    ...
    add_fastapi_endpoint(app, sdk, "/copilotkit")
```

**问题**：FastAPI 同时使用 `lifespan` 和 `@on_event("startup")` 时，startup event 中的异常可能被**静默吞掉**，导致路由没注册但没报错。

### 修复

**把 CopilotKit 注册移入 `lifespan` 的 `yield` 之前**，和图构建在同一个地方：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 日志配置 ...
    await get_graph()

    # 直接在这里注册 CopilotKit，不再用 @on_event("startup")
    sdk = CopilotKitRemoteEndpoint(agents=[...])
    add_fastapi_endpoint(app, sdk, "/copilotkit")

    yield  # 开放请求
```

### 教训

> `@on_event("startup")` 的异常处理不透明。关键路由注册应放在 `lifespan` 中，确保异常直接暴露。

---

## 问题三：LangGraphAgent 改名

### 发现

移入 lifespan 后，后端再次崩溃：

```
ImportError: cannot import name 'LangGraphAgent' from 'copilotkit'
Did you mean: 'LangGraphAGUIAgent'?
```

### 排查

Python `copilotkit` SDK v0.1.94 将 `LangGraphAgent` 重命名为 `LangGraphAGUIAgent`，代码还在用旧名字。

### 修复

```python
# 修复前
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent

# 修复后
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
```

### 教训

> 库版本更新后类名/导入路径可能变化。遇到 `ImportError` 时先看错误提示中的 `Did you mean`。

---

## 问题四：前端白屏（蓝色背景）

### 发现

修完导入后，后端启动成功，但前端刷新后只剩一片蓝色背景，什么都看不到。

### 排查

后端 `/copilotkit` 返回 200，代码没有被修改。蓝色背景说明 `CopilotKit` 组件包裹了所有内容，但组件内部初始化失败导致**整个 React 树崩溃**。

### 修复

**添加 ErrorBoundary 组件**，防止 CopilotKit 连接失败导致整个页面白屏，同时暴露实际错误信息：

```tsx
// main.tsx
class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: string }
> {
  state = { hasError: false, error: '' };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, color: '#f87171', fontFamily: 'monospace' }}>
          <h2>页面渲染出错</h2>
          <pre>{this.state.error}</pre>
          <button onClick={() => this.setState({ hasError: false, error: '' })}>
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
```

### 效果

ErrorBoundary 暴露了真实错误：

```
useAgent: Agent 'automind' not found after runtime sync (runtimeUrl=/copilotkit).
Known agents: [0]
```

### 教训

> React 组件树中如果某个第三方库组件初始化崩溃，会导致**整个子树消失**。用 ErrorBoundary 包裹可以：1) 防止白屏 2) 暴露真实错误。

---

## 问题五：前后端协议不兼容（核心问题）

### 发现

ErrorBoundary 显示：

```
Agent 'automind' not found after runtime sync. Known agents: [0]
```

后端明明注册了 `automind` agent，`POST /copilotkit/` 也返回 200，但前端认为有 0 个 agent。

### 排查

1. **测试后端**：直接 POST 到 `/copilotkit/`，确实返回了 agent 列表（REST 格式）
2. **检查前端版本**：`@copilotkit/react-core@1.61.0`
3. **检查前端请求**：前端 v1.61.0 使用 `urql` GraphQL 客户端，发送的是 GraphQL 查询：
   ```graphql
   query availableAgents {
     availableAgents {
       agents { name id description }
     }
   }
   ```
4. **对比后端响应**：后端 Python `copilotkit` v0.1.94 只提供 REST API，返回的是 JSON 格式

**协议完全不匹配：**

| | 前端 v1.5+ | 后端 Python copilotkit v0.1.94 |
|---|---|---|
| 查询 agent 列表 | GraphQL: `{ availableAgents { agents { name } } }` | REST: `GET /` → `{"agents": [...]}` |
| 执行 agent | GraphQL mutation `generateCopilotResponse` | REST: `POST /agent/{name}` |
| 流式响应 | GraphQL multipart/mixed incremental | REST streaming JSON |

### 尝试方案 A：降级前端版本

尝试将前端降级到 v1.5.x，以为老版本可能用 REST。

结果：**v1.5.20 也用 GraphQL 协议**。`runtime-client-gql` 模块从 v1.5 开始就是默认。

### 尝试方案 B：自建 GraphQL 适配器

创建了 `graphql_adapter.py`，拦截前端的 GraphQL 请求，翻译成后端能处理的格式：

- `availableAgents` 查询 → 调用 `sdk.info()` → 返回 GraphQL 格式
- `generateCopilotResponse` 变更 → 构造 `RunAgentInput` → 调用 `agent.run()` → 将 AG-UI 事件流转为 GraphQL multipart/mixed 流

**过程中又踩了 3 个子坑：**

1. **导入路径错误**：`from copilotkit.types import CopilotKitContext` → 实际是 `from copilotkit.sdk import CopilotKitContext`
2. **API 变更**：`LangGraphAGUIAgent` 没有 `execute()` 方法，用的是 AG-UI 协议的 `run(RunAgentInput)` 异步生成器
3. **消息缺少 id 字段**：AG-UI 的 `Message` 类型要求每条消息有 `id`，前端消息没有 → 自动添加 UUID
4. **Loguru 格式冲突**：`logger.error(f"...{e}...")` 中 f-string 的花括号被 loguru 当作占位符 → 改用 `logger.error("...: {}", e)`

适配器测试通过了 `availableAgents` 查询，但流式响应的 `multipart/mixed` 格式与前端 urql 客户端的解析仍有兼容性问题。

### 最终方案 C：切换到 AG-UI 协议（SSE）

**放弃 CopilotKit Runtime + GraphQL 适配器的复杂方案**，改用 CopilotKit 官方推荐的新一代标准协议 **AG-UI**（HTTP POST + SSE），彻底绕开 GraphQL 兼容问题。

#### 后端改造（`main.py`）

```python
# 改造前（CopilotKit REST）
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

sdk = CopilotKitRemoteEndpoint(agents=[LangGraphAGUIAgent(...)])
add_fastapi_endpoint(app, sdk, "/copilotkit")

# 改造后（AG-UI SSE）
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

agent = LangGraphAgent(
    name="automind",
    description="AutoMind 智能车机助手",
    graph=await get_graph(),
)
add_langgraph_fastapi_endpoint(app, agent, "/agent")
```

#### 前端改造（`App.tsx`）

```tsx
// 改造前
import { CopilotKit } from "@copilotkit/react-core";
<CopilotKit runtimeUrl="/copilotkit" agent="automind">

// 改造后
import { CopilotKit } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";

const automindAgent = new HttpAgent({ url: "/agent" });

<CopilotKit agents__unsafe_dev_only={{ default: automindAgent }}>
```

#### Vite 代理改造（`vite.config.ts`）

```typescript
// 改造前
proxy: { '/copilotkit': { target: 'http://localhost:8001' } }

// 改造后
proxy: { '/agent': { target: 'http://localhost:8001' } }
```

#### 关键细节

- `agents__unsafe_dev_only` 的 key **必须为 `"default"`**，CopilotPopup 默认查找此 key
- 导入路径从 `@copilotkit/react-core` 改为 `@copilotkit/react-core/v2`
- 新增依赖 `@ag-ui/client`
- CSS 导入改为 `@copilotkit/react-ui/v2/styles.css`

### 教训

> 1. **协议不兼容时，不要试图写适配层去桥接**——urql 的 multipart/mixed 格式极其复杂，完美实现成本极高
> 2. **优先使用标准协议**（AG-UI SSE），它同时被前后端官方支持，不需要任何适配
> 3. 前后端 SDK 版本号是独立维护的，不能假设它们"应该兼容"

---

## 问题六：`GET /copilotkit/threads` 400

### 发现

修复过程中，用户刷新页面时后端报：

```
GET /copilotkit/threads?agentId=0 HTTP/1.1" 400 Bad Request
```

### 排查

前端在刷新时尝试恢复历史会话，请求 `GET /copilotkit/threads`。后端 CopilotKit REST SDK 不支持这个端点。

### 处理

切换到 AG-UI 协议后，这个端点不再需要。前端通过 `HttpAgent` 直连 `/agent` SSE 端点，不再走 CopilotKit Runtime 的会话恢复流程。

---

## 问题七：Loguru f-string 格式冲突

### 发现

GraphQL 适配器调试时，日志报错：

```
KeyError: "'role'"
```

### 排查

代码中写了：

```python
logger.error(f"Agent execution error: {e}")
```

Loguru 会把 `{}` 当作格式化占位符。当 `e` 的内容包含花括号（如 Pydantic 验证错误），loguru 会尝试解析 `{e}` 展开后的内容中的 `{role}` 等作为占位符 → KeyError。

### 修复

```python
# 修复前
logger.error(f"Agent execution error: {e}")

# 修复后
logger.error("Agent execution error: {}", e, exc_info=True)
```

### 教训

> **Loguru 和 f-string 不要混用**。Loguru 自带 `{}` 格式化，用 `logger.error("msg: {}", value)` 代替 `logger.error(f"msg: {value}")`。

---

## 完整时间线

```
启动后端
  │
  ├─ ❌ RuntimeError: Cannot run the event loop while another loop is running
  │   └─ 修复：删除 _load_mcp_tools_sync，一路 async/await
  │
  ├─ ❌ HTTP 404: {"detail":"Not Found"}
  │   └─ 修复：CopilotKit 注册从 @on_event("startup") 移入 lifespan
  │
  ├─ ❌ ImportError: cannot import name 'LangGraphAgent'
  │   └─ 修复：改为 LangGraphAGUIAgent（SDK 改名）
  │
  ├─ ❌ 前端一片蓝色背景（白屏）
  │   └─ 修复：添加 ErrorBoundary 暴露真实错误
  │
  ├─ ❌ Agent 'automind' not found. Known agents: [0]
  │   └─ 根因：前端 GraphQL 协议 vs 后端 REST 协议不兼容
  │   └─ 尝试：降级前端版本 → 仍然用 GraphQL
  │   └─ 尝试：自建 GraphQL 适配器 → 流式响应格式难兼容
  │   └─ 最终：切换到 AG-UI SSE 协议，前后端同时改造
  │
  ├─ ❌ GET /copilotkit/threads 400
  │   └─ 切换 AG-UI 后不再需要此端点
  │
  └─ ✅ 前后端通过 AG-UI SSE 协议正常通信
```

---

## 涉及文件清单

| 文件 | 改动说明 |
|------|----------|
| `backend/app/graph/supervisor.py` | 删除 `_load_mcp_tools_sync`；`build_supervisor_graph` / `get_graph` 改为 async |
| `backend/app/main.py` | CopilotKit REST → AG-UI SSE 端点；注册移入 lifespan |
| `frontend/src/App.tsx` | `@copilotkit/react-core/v2` + `HttpAgent` (AG-UI) |
| `frontend/src/main.tsx` | 添加 ErrorBoundary 防白屏 |
| `frontend/vite.config.ts` | 代理路径 `/copilotkit` → `/agent` |
| `frontend/package.json` | 新增 `@ag-ui/client`，CopilotKit 升级到 v1.61+ |

---

## 核心教训

1. **异步世界不要嵌套事件循环** — 一路 async/await
2. **`@on_event("startup")` 异常会被吞** — 关键初始化放 lifespan
3. **库版本更新要检查 API 变更** — 类名/导入路径/协议都可能变
4. **React 白屏用 ErrorBoundary** — 先暴露错误再修复
5. **协议不兼容时不要写适配层** — 换用双方都支持的标准协议
6. **Loguru 不要和 f-string 混用** — 用 `{}` 占位符代替
