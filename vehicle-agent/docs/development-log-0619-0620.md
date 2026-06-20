# AutoMind 开发日志 — 2026.06.19 ~ 06.20

> 记录车机智能助手平台搭建过程中遇到的 4 个关键技术难点、排查思路与最终方案。

---

## 问题一：CopilotKit 前后端协议不匹配

**时间**：6月19日晚  
**Commit**：`2a64f8f` — fix：车机AIUI前后端协议  
**严重度**：高（完全无法通信）

### 现象

前端 CopilotKit `CopilotPopup` 组件能正常渲染，但发送消息后：
- 后端收不到用户消息，或收到消息但返回的数据前端无法解析
- 消息角色丢失（system/user/assistant 混乱）
- 流式响应断裂，UI 上只显示空白或报错

### 排查过程

1. **查看前端网络请求**：发现 CopilotKit v1.5+ 前端使用 `urql` 的 GraphQL `@stream/@defer` 指令做流式传输
2. **查看后端端点**：Python CopilotKit SDK 0.1.94 注册的是 REST 端点（`CopilotKitRemoteEndpoint`），返回 JSON 流
3. **协议对比**：
   - 前端期望：GraphQL multipart incremental response（`incremental` + `path` 字段做增量合并）
   - 后端实际：REST streaming（逐行 JSON）
   - 两者完全不兼容

4. **尝试自定义 GraphQL 适配器**：极难完美实现 urql 的 multipart incremental 格式，消息角色始终丢失

### 根因

CopilotKit 前端（v1.5+）和 Python SDK（0.1.x）之间存在**协议断层**。前端走 GraphQL 流式协议，后端只提供 REST。这不是配置问题，是架构层面的不兼容。

### 最终方案

**放弃 CopilotKit Runtime，改用 AG-UI 协议**（HTTP POST + SSE），这是 CopilotKit 官方推荐的新一代标准协议。

#### 后端改造（`vehicle-agent/backend/app/main.py`）

```python
# ===== 改造前（REST 端点）=====
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

sdk = CopilotKitRemoteEndpoint(
    agents=[LangGraphAgent(name="automind", graph=get_graph())],
)
add_fastapi_endpoint(app, sdk, "/copilotkit")

# ===== 改造后（AG-UI SSE 端点）=====
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

agent = LangGraphAgent(
    name="automind",
    description="AutoMind 智能车机助手",
    graph=await get_graph(),
)
add_langgraph_fastapi_endpoint(app, agent, "/agent")
```

#### 前端改造（`vehicle-agent/frontend/src/App.tsx`）

```tsx
// ===== 改造前 =====
import { CopilotKit } from "@copilotkit/react-core";
<CopilotKit runtimeUrl="/copilotkit" agent="automind">

// ===== 改造后 =====
import { CopilotKit } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";

const automindAgent = new HttpAgent({ url: "/agent" });

<CopilotKit agents__unsafe_dev_only={{ default: automindAgent }}>
```

**关键细节**：
- `agents__unsafe_dev_only` 的 key 必须为 `"default"`，CopilotPopup 默认查找此 key
- 导入路径从 `@copilotkit/react-core` 改为 `@copilotkit/react-core/v2`
- 新增依赖 `@ag-ui/client`
- `main.tsx` 添加 `ErrorBoundary` 防止连接失败白屏

---

## 问题二：Langfuse V4 SDK 集成与升级

**时间**：6月20日上午  
**Commit**：`7f47e16` — 添加 langfuse（初始版本），后续修复  
**严重度**：中（可观测性功能不可用）

### 现象

初始集成 Langfuse 时，按照旧版文档写代码，启动后报错：
- `from langfuse.callback import CallbackHandler` 导入失败
- 环境变量 `LANGFUSE_HOST` 不生效，trace 数据无法上报
- 即使 API 返回 200，Langfuse 控制台也查不到 trace

### 排查过程

1. **检查 SDK 版本**：`pip show langfuse` → 版本 4.9.1，是 V4
2. **查阅 V4 官方文档**：发现 V4 有重大 API 变更
3. **对比差异**：

| 项目 | V2/V3（旧） | V4（新） |
|------|-------------|----------|
| 环境变量 | `LANGFUSE_HOST` | `LANGFUSE_BASE_URL` |
| 导入路径 | `from langfuse.callback import CallbackHandler` | `from langfuse.langchain import CallbackHandler` |
| 初始化方式 | 手动传参 `CallbackHandler(publicKey=..., host=...)` | 环境变量自动初始化，无需手动传参 |
| 注入位置 | LLM 的 `callbacks` 参数 | LangGraphAgent 的 `config.callbacks` |

4. **排查 trace 不上报**：发现 V3 自部署需要完整的 Redis + ClickHouse + Worker 管道，任何一个环节断了数据就入不了库

### 根因

三个层面的问题：
1. **SDK API 变更**：V4 的环境变量名和导入路径全部改了，旧代码直接报错
2. **@observe 装饰器的阻塞风险**：V4 推荐的 `@observe` 装饰器在 Langfuse 服务端不稳定时会阻塞整个 HTTP 请求
3. **注入方式错误**：V4 的 CallbackHandler 应该注入到 `LangGraphAgent` 的 config 中，而非每个 LLM 实例

#### 中间尝试：@observe 装饰器方案（已放弃）

V4 SDK 推荐使用 `@observe` 装饰器做追踪，初次集成时尝试了这个方案：

```python
from langfuse import observe

@observe(name="build_supervisor_graph")
async def build_supervisor_graph() -> CompiledStateGraph:
    ...

@observe(name="call_model")
def call_model(state, config):
    ...
```

**问题**：当 Langfuse 服务端不稳定时（如 Redis Socket Timeout、ClickHouse 写入超时、容器重启中），`@observe` 装饰器会**同步阻塞 HTTP 请求**，表现为：
- 前端发消息后一直转圈，接口无响应
- 整个 FastAPI 服务卡死，健康检查 `/api/vehicle/health` 也无法返回
- 日志中无任何报错（因为请求根本没到达业务代码，被装饰器卡住了）

**排查**：移除 `@observe` 装饰器后服务立即恢复正常 → 确认是装饰器的网络 IO 阻塞了请求线程。

**结论**：`@observe` 适合 Langfuse 服务端完全稳定且网络可靠的场景，但在开发/自部署环境中风险太高。最终选择 **CallbackHandler** 方案 —— 它通过 LangChain 回调机制异步上报，不会阻塞主流程。

### 最终方案

#### observability.py — 环境变量 + CallbackHandler 单例

```python
def setup_observability() -> None:
    if settings.langfuse_enabled:
        # V4 SDK 标准环境变量名
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.LANGFUSE_BASE_URL)  # 非 LANGFUSE_HOST

        # V4 导入路径
        from langfuse.langchain import CallbackHandler  # 非 langfuse.callback
        global _langfuse_handler
        _langfuse_handler = CallbackHandler()  # 自动读取环境变量，无需手动传参
```

#### main.py — 注入到 LangGraphAgent

```python
langfuse_handler = get_langfuse_handler()
agent_config = {}
if langfuse_handler:
    agent_config = {"callbacks": [langfuse_handler]}

agent = LangGraphAgent(
    name="automind",
    graph=await get_graph(),
    config=agent_config,  # ← 注入到 Agent 级别，自动追踪所有调用
)
```

#### config.py — 兼容旧变量名

```python
LANGFUSE_BASE_URL: str = os.getenv("LANGFUSE_BASE_URL",
    os.getenv("LANGFUSE_HOST", "http://localhost:3000"))  # 兼容旧配置
```

#### llm.py — 不再手动注入

```python
# V4 方案：不在 LLM 层注入 callback，由 LangGraphAgent config 统一管理
llm = ChatOpenAI(
    model=model or settings.LLM_MODEL,
    temperature=temperature,
    streaming=streaming,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_API_BASE,
)  # 无需 callbacks 参数
```

---

## 问题三：Supervisor 不调用子 Agent

**时间**：6月20日下午  
**严重度**：高（核心功能完全失效）

### 现象

用户发送任何指令（"空调温度调低一点"、"播放音乐"、"导航去公司"），Supervisor 都只回复客套话：
- "您好！我是 AutoMind，请问有什么可以帮您？"
- `tool_calls` 始终为空数组 `[]`
- 5 个子 Agent（navigation/media/vehicle/weather/reminder）从未被路由

Langfuse Trace 数据佐证：
```
output_reasoning: 138 tokens   ← 模型在做"思考"
output: 22 tokens              ← 只输出了几个字的客套话
tool_calls: []                 ← 没有任何工具调用
```

执行链只走了一圈就结束了：
```
LangGraph → supervisor → agent → call_model → should_continue → __end__
```

### 排查过程

#### 第一步：分析 Trace，建立初始假说

模型是 `qwen3.7-plus`（思考模型），trace 有 `output_reasoning: 138`。
初始假说：**思考模式和 function calling 不兼容** → 加了 `extra_body={"enable_thinking": False}`。

#### 第二步：用户纠正，改用数据验证

用户指出"不可能这么垃圾"，回滚 thinking 设置，改为**自底向上逐层验证**：

```
┌─────────────────────────────────────────┐
│ 第4层：完整 Supervisor 图（生产代码）     │  ← 问题现象
├─────────────────────────────────────────┤
│ 第3层：_build_prompt + LLM 管道         │  ← 根因在此
├─────────────────────────────────────────┤
│ 第2层：LangChain bind_tools + ainvoke   │  ← 正常 ✅
├─────────────────────────────────────────┤
│ 第1层：原生 OpenAI SDK 直调 API          │  ← 正常 ✅
└─────────────────────────────────────────┘
```

#### 第1层：原生 OpenAI SDK（`test_tool_call.py`）

绕过所有框架，直接调百炼 API：

```python
client = AsyncOpenAI(api_key=API_KEY, base_url=API_BASE)
resp = await client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "你是 AutoMind 车载助手..."},
        {"role": "user", "content": "播放音乐"},
    ],
    tools=[...],
    stream=True,
)
```

**结果**：`tool_calls: {name: 'transfer_to_vehicle_agent'}` — **模型完全支持 tool calling！**

#### 第2层：LangChain bind_tools

```python
llm = ChatOpenAI(model=MODEL, ...)
llm_with_tools = llm.bind_tools(tools)
response = await llm_with_tools.ainvoke([
    SystemMessage(content="你是 AutoMind..."),
    HumanMessage(content="空调温度调低一点"),
])
```

**结果**：`tool_calls: [{name: 'transfer_to_vehicle_agent'}]` — **LangChain 层也正常！**

#### 第3层：定位 _build_prompt 管道

读 `langgraph` 源码 `chat_agent_executor.py`，找到关键代码：

```python
# 第137行：_get_prompt_runnable 函数
def _get_prompt_runnable(prompt):
    if prompt is None:
        ...
    elif isinstance(prompt, str):
        # 字符串 → 自动拼接 state["messages"]
        prompt_runnable = RunnableCallable(
            lambda state: [SystemMessage(content=prompt)] + state["messages"]
        )
    elif callable(prompt):
        # 函数 → 直接用返回值，不做任何额外处理！
        prompt_runnable = RunnableCallable(prompt)

# 第590行：构建管道
static_model = _get_prompt_runnable(prompt) | model
#              ↑ prompt 返回值              ↑ 绑了 tools 的 LLM
```

**发现**：当 prompt 是 callable（函数）时，LangGraph **完全信任返回值**，不会自动拼接 `state["messages"]`。

而我们的 `_build_prompt` 返回的是纯字符串：

```python
def _build_prompt(state: dict) -> str:  # ← 返回 str
    return SUPERVISOR_PROMPT.format(...)  # ← 只有系统提示文本
```

**对话历史被丢弃了！模型看不到用户说了什么。**

#### 对比测试确认根因

```python
# 场景A：只有 SystemMessage（模拟原来的行为）
messages_a = [SystemMessage(content=prompt_result)]
resp_a = await llm_with_tools.ainvoke(messages_a)
# → tool_calls: []  ❌  模型不知道用户说了啥

# 场景B：SystemMessage + 对话历史
messages_b = [SystemMessage(content=prompt_result), HumanMessage(content="空调温度调低一点")]
resp_b = await llm_with_tools.ainvoke(messages_b)
# → tool_calls: [{name: 'transfer_to_vehicle_agent'}]  ✅
```

### 根因

`_build_prompt` 返回 `str` 类型。在 `langgraph-supervisor` 的 `create_supervisor` 中，callable prompt 被包装成 `RunnableCallable(prompt)`，其返回值就是发给 LLM 的全部内容。返回纯字符串意味着**只发了系统提示，对话历史（用户消息）全部丢失**，模型自然无法产生 tool_calls。

### 最终方案

修改 `supervisor.py` 的 `_build_prompt`，返回 `[SystemMessage] + messages`：

```python
# 修复前
def _build_prompt(state: dict) -> str:
    return SUPERVISOR_PROMPT.format(...)

# 修复后
def _build_prompt(state: dict) -> list:
    """返回 [SystemMessage, ...messages] 列表"""
    from langchain_core.messages import SystemMessage

    messages = state.get("messages", [])
    # ... 获取记忆上下文 ...

    system_content = SUPERVISOR_PROMPT.format(
        routing_description=ROUTING_DESCRIPTION,
        user_profile=context.get("user_profile", {}),
        recalled_preferences=context.get("recalled_preferences", []),
        pending_reminders=context.get("pending_reminders", []),
    )

    return [SystemMessage(content=system_content)] + list(messages)
```

### 验证结果

```
--- 测试 1: 单轮 '空调温度调低一点' ---
  tool_calls: [{name: 'transfer_to_vehicle_agent'}]  ✅

--- 测试 2: 单轮 '播放音乐' ---
  tool_calls: [{name: 'transfer_to_media_agent'}]  ✅

--- 测试 3: 多轮 '导航去公司' ---
  tool_calls: [{name: 'transfer_to_navigation_agent'}]  ✅
```

---

## 问题四：Langfuse Trace 排查 — 如何定位工具调用失败

**时间**：6月20日下午（紧接问题三）  
**严重度**：中（排查效率问题）

### 背景

问题三修复后，需要了解如何在 Langfuse 控制台查看 trace 来验证修复效果，以及未来如何快速定位类似问题。

### 排查过程

#### 第一步：理解 Trace 树状结构

Langfuse 的 Trace 页面左侧是树状结构，对应 LangGraph 的执行链：

```
LangGraph (根)
├── supervisor (Supervisor 节点)
│   ── agent (ReAct Agent)
│       ├── call_model
│       │   ── RunnableSequence
│       │       ├── Prompt          ← 系统提示词
│       │       └── ChatOpenAI      ← LLM 调用（点击看详情）
│       └── should_continue         ← 是否继续循环
```

**关键节点**：`ChatOpenAI` 是实际调用 LLM 的地方，所有 tool calling 的信息都在这里。

#### 第二步：看 Input/Output（踩坑点）

点击左侧树的 `ChatOpenAI` 节点后，右侧面板默认显示 **Preview** 标签页。

**踩坑 1：Formatted 视图看不到 tools**

Preview 标签页右上角有 `Formatted` / `JSON` 两个切换按钮：
- `Formatted`：只渲染消息文本（system prompt + 对话），**隐藏了 tools 字段**
- `JSON`：显示原始请求体，包含完整的 `tools` 数组

一开始在 Formatted 视图里翻遍了整个 prompt 文本，没找到 tools 相关内容，误以为工具没传进去。

**正确做法**：点击右上角 `JSON` 切换，就能看到：

```json
[
  {"role": "user", "content": "你是 AutoMind...（系统提示）"},
  {"role": "tool", "content": {"type": "function", "function": {"name": "transfer_to_media_agent", ...}}},
  {"role": "tool", "content": {"type": "function", "function": {"name": "transfer_to_navigation_agent", ...}}},
  ...
]
```

> **注意**：`langgraph_supervisor` 的 `create_supervisor` 把路由工具以 `role: "tool"` 的消息形式注入，而非 OpenAI 标准的 `tools` 参数。这是框架层面的实现细节。

#### 第三步：确认工具传入了，但 LLM 没调用

JSON 视图中确认 5 个 `transfer_to_xxx` 工具都在，但 Output 显示：

```json
"tool_calls": [],
"finish_reason": "stop"
```

LLM 收到了工具定义，但选择了直接文本回复，没有发起 tool call。

**此时有两个假说**：
1. 模型不支持 function calling
2. 模型没看到用户消息（对话历史丢失）

#### 第四步：验证模型能力

用原生 OpenAI SDK 直接调百炼 API 测试 tool calling → **模型完全支持**。

排除假说 1，锁定假说 2 → 回到问题三的根因：`_build_prompt` 返回 `str` 导致对话历史丢失。

### 排查方法论总结（Langfuse 篇）

```
1. 左侧树找 ChatOpenAI 节点
2. 右侧切到 JSON 视图（不是 Formatted！）
3. 看 Input：tools 是否存在？对话历史是否完整？
4. 看 Output：tool_calls 是否为空？finish_reason 是什么？
5. 对比 Input/Output 定位问题层级
```

**关键教训**：
- Formatted 视图会隐藏 tools 字段，排查 tool calling 问题必须切到 JSON 视图
- `role: "tool"` 消息是 langgraph_supervisor 注入路由工具的方式，不是用户消息
- 工具传入了但没被调用 ≠ 模型不支持，大概率是对话历史没传进去

---

## 排查方法论总结

```
问题现象
  ↓
读 Trace / 日志 → 建立假说
  ↓
不要猜，自底向上逐层验证：
  原生 SDK → 框架层 → 业务管道 → 生产代码
  每层独立测试，哪层出问题就定位到哪层
  ↓
读框架源码理解内部机制
  ↓
写对比测试确认根因（有/无某个条件 → 结果差异）
  ↓
精确修复 + 回归验证
```

**核心原则**：不猜，用数据说话。从最底层开始排除，逐层定位。

---

## 四个问题速览

| # | 问题 | 时间 | 严重度 | 根因 | 方案 |
|---|------|------|--------|------|------|
| 1 | CopilotKit 前后端协议不匹配 | 6/19 晚 | 高（无法通信） | 前端 GraphQL vs 后端 REST 协议断层 | 升级到 AG-UI SSE 协议 |
| 2 | Langfuse V4 SDK 集成 | 6/20 上午 | 中（可观测失效） | V4 环境变量、导入路径、注入方式全改 | `LANGFUSE_BASE_URL` + `langfuse.langchain` + Agent config 注入 |
| 3 | @observe 装饰器阻塞 HTTP | 6/20 上午 | 高（服务卡死） | Langfuse 服务端不稳定时装饰器同步阻塞请求线程 | 放弃 @observe，改用 CallbackHandler 异步回调 |
| 4 | Supervisor 不调用子 Agent | 6/20 下午 | 高（核心功能失效） | callable prompt 返回 str 丢弃对话历史 | 返回 `[SystemMessage] + messages` |
| 5 | Langfuse Formatted 视图隐藏 tools | 6/20 下午 | 低（排查效率） | Formatted 视图只渲染消息文本，不显示 tools | 切到 JSON 视图查看原始请求体 |

**共同特征**：5 个问题本质上都是**协议/接口层的不匹配**：
1. 前端 GraphQL vs 后端 REST → 协议不匹配
2. Langfuse V2 API vs V4 API → SDK 版本不匹配
3. @observe 同步 IO vs FastAPI 异步请求 → 执行模型不匹配
4. callable prompt 返回 str vs LangGraph 期望 messages → 数据类型不匹配
5. Langfuse Formatted 视图 vs 原始 JSON → 展示层与实际数据不匹配

---

## 涉及文件清单

| 文件 | 改动说明 |
|------|----------|
| `vehicle-agent/backend/app/main.py` | CopilotKit → AG-UI SSE 端点；Langfuse CallbackHandler 注入 |
| `vehicle-agent/backend/app/graph/supervisor.py` | `_build_prompt` 返回类型从 `str` 改为 `[SystemMessage] + messages` |
| `vehicle-agent/backend/app/utils/observability.py` | Langfuse V4 SDK 标准集成方案 |
| `vehicle-agent/backend/app/models/llm.py` | 移除手动 callback 注入，由 Agent config 统一管理 |
| `vehicle-agent/backend/app/config.py` | `LANGFUSE_BASE_URL` 替代 `LANGFUSE_HOST` |
| `vehicle-agent/frontend/src/App.tsx` | `@copilotkit/react-core/v2` + `HttpAgent` (AG-UI) |
| `vehicle-agent/frontend/src/main.tsx` | ErrorBoundary 防白屏 |
| `vehicle-agent/frontend/package.json` | 新增 `@ag-ui/client`，升级 `@copilotkit` 到 v1.61 |
| `vehicle-agent/backend/test_tool_call.py` | 第1、2层验证测试 |
| `vehicle-agent/backend/test_supervisor_prompt.py` | 第3层验证测试 |