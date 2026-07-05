# CopilotKit GraphQL 适配层踩坑记录

> 记录从前端 CopilotKit v1.5 与后端 Python copilotkit v0.1.94 对接过程中遇到的所有问题、排查过程和解决方案。

---

## 一、问题全景

后端使用 FastAPI + LangGraph + CopilotKit Python SDK，前端使用 CopilotKit React v1.5。由于前后端协议版本差异，需要自建 GraphQL 适配层（`graphql_adapter.py`）将 AG-UI 事件流转换为 GraphQL multipart/mixed 流式响应。

整个对接过程中共踩了 **13 个坑**，涉及配置错误、SDK API 误用、库 bug、字段名不匹配、数据格式不兼容等多个层面。

---

## 二、踩坑时间线

### 坑 1：`agent=` 为空导致 400 Bad Request

**现象**：后端日志显示 `agent=`（空字符串），前端请求直接返回 400。

**原因**：前端 CopilotKit v1.5 发送 GraphQL 请求时，`agentName` 字段名与后端提取逻辑不匹配。

**解决**：兼容多种字段名，单 agent 时自动回退：
```python
agent_name = (
    data.get("agentName", "")
    or data.get("agent_name", "")
    or data.get("agent", "")
    or data.get("name", "")
)
if not agent_name:
    # 只有一个 agent 时自动使用
    agents_list = sdk.agents(context) if callable(sdk.agents) else sdk.agents
    if len(agents_list) == 1:
        agent_name = agents_list[0].name
```

---

### 坑 2：`NameError: name 'k' is not defined`

**现象**：后端崩溃，报 `NameError: name 'k' is not defined`。

**原因**：f-string 中嵌套字典推导式语法不兼容：
```python
# 错误写法
logger.info(f"data={ {k: v for k, v in data.items()} }")
```

**解决**：提取为独立变量：
```python
_debug_data = {k: v for k, v in data.items() if k != 'messages'}
logger.info(f"data={_debug_data}")
```

---

### 坑 3：`AttributeError: 'CopilotKitRemoteEndpoint' object has no attribute 'agents'`

**现象**：调用 `sdk.agents(context)` 时报错。

**原因**：`sdk.agents` 可能是属性（列表）也可能是 callable，不能直接当方法调用。

**解决**：
```python
agents_list = sdk.agents(context) if callable(sdk.agents) else sdk.agents
```

---

### 坑 4：`AttributeError: type object 'LangGraphAgent' has no attribute 'execute'`

**现象**：`sdk.execute_agent()` 内部调用 `agent.execute()`，但 `LangGraphAGUIAgent` 没有此方法。

**原因**：SDK 的 `execute_agent()` 方法假设 agent 有 `execute()` 方法，但 `LangGraphAGUIAgent` 只有 `run()` 方法。

**解决**：绕过 `execute_agent()`，直接调用 agent：
```python
agent = next(a for a in agents_list if a.name == agent_name)
event_stream = agent.run(run_input)  # 直接调用 run()
```

---

### 坑 5：`Model not exist` — 百炼平台模型名错误

**现象**：LLM 调用返回 404，`'Model not exist.'`。

**原因**：`.env` 中配置的 `LLM_MODEL=qwen3.6-flash` 在 Token Plan 中是正确的，但之前改成了 `qwen-turbo-latest`（不存在于 Token Plan）。

**解决**：改回 Token Plan 支持的模型名：
```
LLM_MODEL=qwen3.6-flash
```

Token Plan 支持的文本模型清单：
- `qwen3.7-max`（限时活动）、`qwen3.6-plus`、`qwen3.6-flash`
- `deepseek-v4-pro`、`deepseek-v4-flash`、`deepseek-v3.2`
- `kimi-k2.6`、`kimi-k2.5`、`glm-5.1`、`glm-5`、`MiniMax-M2.5`

---

### 坑 6：Token Plan 不支持 Embedding 模型

**现象**：`text-embedding-v4` 在 Token Plan 端点调用失败。

**原因**：Token Plan 只支持文本生成和图像生成模型，**不支持 Embedding 模型**。Embedding 需要走标准 dashscope 接口（`https://dashscope.aliyuncs.com/compatible-mode/v1`），且需要标准 API Key（`sk-` 开头，不是 `sk-sp-`）。

**解决**：暂时禁用记忆模块：
```env
MEMORY_ENABLED=false
```
代码中加开关守卫，等有了标准 dashscope API Key 再启用。

---

### 坑 7：`TypeError: 'NoneType' object does not support item assignment`

**现象**：LLM 调用失败后，`ag_ui_langgraph` 库内部崩溃。

**原因**：`ag_ui_langgraph/agent.py` 的 bug — 当 LLM 抛异常后 `finally` 块将 `self.active_run` 置为 `None`，但流还在继续产生事件，后续代码直接访问 `self.active_run["langgraph_run_id"]` 就崩了。

**解决**：在 `_handle_stream_events` 方法中所有访问 `self.active_run` 的地方加 `None` 守卫：
```python
# 第 312 行
if self.active_run is not None:
    self.active_run["langgraph_run_id"] = event_run_id

# 第 329 行
exiting_node = (self.active_run or {}).get("node_name") == current_node_name

# 循环内加 break 守卫
if self.active_run is None:
    break
```

---

### 坑 8：后端没有任何输出

**现象**：前端收到初始 chunk 后直接结束，没有 AG-UI 事件。

**原因**：事件流异常被静默吞掉，没有日志。

**解决**：在 `_agui_to_graphql_stream` 中加 `try/except` 包裹整个事件循环：
```python
try:
    async for event in event_stream:
        ...
except Exception as e:
    logger.error(f"[AG-UI] 事件流异常: {type(e).__name__}: {e}", exc_info=True)
    # 发送错误响应给前端
```

---

### 坑 9：事件流正常但前端不显示消息

**现象**：日志显示收到了 `TEXT_MESSAGE_CONTENT`、`TEXT_MESSAGE_END` 等事件，但前端空白。

**原因**：缺少 `TEXT_MESSAGE_START` 事件！`ag_ui_langgraph` 库在某些条件下不会发出 START 事件，但前端需要先收到 START 才能初始化消息容器。

**解决**：在适配层自动补发：
```python
if event_type in ("TEXT_MESSAGE_CONTENT",):
    msg_id = event_dict.get("message_id", "")
    if msg_id and msg_id not in sent_start_ids:
        sent_start_ids.add(msg_id)
        # 补发 START 事件
        yield _make_graphql_chunk(thread_id, run_id, messages=[start_msg])
```

---

### 坑 10：Pydantic 字段名 snake_case vs camelCase

**现象**：`event_dict.get("messageId")` 返回 `None`。

**原因**：AG-UI 的 Pydantic 模型 `model_dump()` 输出的是 **snake_case** 字段名（`message_id`、`tool_call_id`），不是 camelCase（`messageId`）。

**解决**：所有字段提取都兼容两种格式：
```python
msg_id = event_dict.get("message_id", "") or event_dict.get("messageId", "")
tool_call_id = event_dict.get("tool_call_id", "") or event_dict.get("toolCallId", "")
```

---

### 坑 11：`Cannot read properties of undefined (reading 'forEach')`

**现象**：前端 CopilotKit 内部函数 `filterAdjacentAgentStateMessages` 崩溃。

**原因**：CopilotKit v1.5 要求每个 GraphQL chunk 都必须包含 `messages` 和 `metaEvents` 字段，即使是空数组也不能省略。之前的代码用条件判断后才添加：
```python
# 错误：缺少字段时前端拿到 undefined
if messages is not None:
    response["messages"] = messages
```

**解决**：始终包含这两个字段：
```python
"messages": messages if messages is not None else [],
"metaEvents": meta_events if meta_events is not None else [],
```

---

### 坑 12：`content.join is not a function`

**现象**：前端 `convertGqlOutputsToMessages` 函数崩溃，`message2.content.join("")` 报错。

**原因**：CopilotKit v1.5 前端代码期望 `content` 是一个**字符串数组**（如 `["你好", "！"]`），调用 `.join("")` 拼接。但后端返回的是**纯字符串**（如 `"你好！"`），字符串没有 `.join()` 方法。

**解决**：所有 `content` 字段改为数组格式：
```python
# START 事件
"content": [],

# CONTENT 事件
"content": [delta] if delta else [],

# END 事件
"content": [],
```

---

## 三、最终解决方案总结

核心文件：`backend/app/utils/graphql_adapter.py`

关键设计决策：
1. **直接调用 `agent.run()`** 而非 `sdk.execute_agent()`（后者假设 agent 有 `execute()` 方法）
2. **自动补发缺失的 `TEXT_MESSAGE_START`** 事件
3. **兼容 snake_case 和 camelCase** 两种字段名
4. **每个 chunk 必须包含** `messages: []` 和 `metaEvents: []`
5. **`content` 字段必须是数组**，不是字符串
6. **`try/except` 包裹事件流**，防止异常静默吞掉
7. **`active_run` None 守卫**，防止库 bug 导致崩溃

---

## 四、排查方法论

| 步骤 | 方法 | 工具 |
|------|------|------|
| 1. 确认后端配置 | 打印实际加载的配置值 | `python -c "from app.config import settings; print(...)"` |
| 2. 验证 API 可用性 | 直接用 Python 调 API | `openai.OpenAI().chat.completions.create(...)` |
| 3. 加调试日志 | 在事件循环中打印每个事件 | `logger.info(f"[AG-UI] 收到事件: ...")` |
| 4. 加异常捕获 | 包裹 async generator | `try/except` |
| 5. 验证字段名 | 实例化 Pydantic 模型看 dump 结果 | `model.model_dump().keys()` |
| 6. 浏览器 F12 | Console 看报错 + Network 看响应 | Chrome DevTools |
| 7. 对比前端期望 | 读前端 JS 源码看期望的数据格式 | `node_modules/.vite/deps/chunk-*.js` |

---

## 五、经验教训

1. **协议版本差异是最大坑源** — 前后端 CopilotKit 版本不同，GraphQL schema 和事件格式都有差异
2. **Pydantic 模型 dump 的字段名是 snake_case** — 不要假设是 camelCase
3. **前端 JS 代码是最终裁判** — 后端返回什么格式不重要，关键是前端期望什么格式
4. **库 bug 要加防御** — 第三方库的边界条件处理不完善，调用方需要加 None 守卫
5. **日志和异常捕获不能省** — 异步生成器中的异常会被静默吞掉，必须显式捕获
6. **Token Plan 有模型限制** — 不是所有百炼模型都支持 Token Plan，Embedding 模型完全不支持
