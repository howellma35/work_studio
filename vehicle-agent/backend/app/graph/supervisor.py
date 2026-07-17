"""
AutoMind Supervisor Agent - 多Agent编排核心（方式 A2 / 官方 Sub-Agents 模式）

架构：
- Supervisor = `create_agent(..., middleware=[CopilotKitMiddleware()])`
- 5 个专业子Agent 各自包成 @tool，由 supervisor 同步 invoke
- 前端工具（select_origin / update_map）由 CopilotKitMiddleware 在 supervisor 层注入
- HITL 暂停只发生在 supervisor 单一作用域 → 不再有跨作用域孤儿 tool_call

这是整个系统的"大脑"，通过单一 ReAct Agent 协调所有子Agent 与前端工具。
"""
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

from copilotkit import CopilotKitMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from app.agents.media_agent import create_media_agent
from app.agents.navigation_agent import create_navigation_agent
from app.agents.reminder_agent import create_reminder_agent
from app.agents.vehicle_agent import create_vehicle_agent
from app.agents.weather_agent import create_weather_agent
from app.config import settings
from app.graph.routing import ROUTING_DESCRIPTION
from app.graph.state import AutoMindState
from app.graph.subagent_tools import build_subagent_tools
from app.memory.manager import memory_manager
from app.mcp.client import load_mcp_tools
from app.models.llm import create_llm

SUPERVISOR_PROMPT = """\
你是 AutoMind，一个智能车载助手。你的核心职责是理解车主需求，调用合适的专业子Agent工具完成任务，并用自然语音简短回复。

{routing_description}

## 你的工作流程
1. 分析用户最新消息，识别意图
2. 调用对应子Agent工具（如 navigation_agent("从家导航到陆家嘴")）
3. 子Agent返回结果后，按需调用前端工具把结果呈现到界面
4. 用一句话简短播报，不要复述子Agent返回的长文本/逐条路线步骤

## 导航专用流程（重要）
- 若用户未明确起点（如"导航去公司"），**先调用 select_origin 前端工具**让用户选择起点
  - select_origin 的默认起点选项已由前端工具 schema 定义，直接调用即可
  - 调用后会暂停等待用户选择，拿到结果再继续
- 拿到起点后，调用 navigation_agent("从〈起点〉导航到〈终点〉")
- navigation_agent 返回里包含一行 `ROUTE_DATA: {{...}}`（JSON）。解析它，调用 update_map(action="navigate")，
  把其中的起点/终点/坐标/距离/时长等字段传给 update_map
  - **不要把逐条 steps 文本、坐标数字、route_coords、JSON 写进你的回复**，这些只传给 update_map，地图会展示路线
- 若是 POI 搜索，navigation_agent 返回 `POI_DATA: {{...}}`，调用 update_map(action="search_poi")，把 pois 传过去
- 最后只说一句话，例如："已为你规划从家到陆家嘴的路线，约 8 公里、25 分钟。"

## 用户偏好上下文（来自记忆系统）
用户档案: {user_profile}
召回偏好: {recalled_preferences}
待办提醒: {pending_reminders}

## 交互规范
- 用简洁、自然的口语回复，适合驾驶场景（单次回复控制在 50 字以内）
- 禁止复述数据：回复中绝对不要出现坐标数字、route_coords、lat/lng、JSON、ROUTE_DATA 等技术数据。这些只通过 update_map 工具参数传递，回复只说人话
- 模糊意图礼貌反问；涉及车辆操作确认无误后执行
- 中文回复，语气亲切专业

记住：你是车主的全能智能助手，目标是让驾驶更安全、更便捷、更愉悦。"""


@dynamic_prompt
def _build_prompt(request) -> str:
    """动态构建 Supervisor 系统提示词，注入记忆上下文（dynamic_prompt 中间件）。

    create_agent 的 system_prompt 只接受 str/SystemMessage，不接受 callable；
    需要按对话动态生成提示词时，应使用 dynamic_prompt 中间件：
    它通过 wrap_model_call 在每次模型调用前把返回的字符串设为系统提示，
    对话历史由 create_agent 自动保留，无需在此手动拼接。
    """
    state = request.state
    user_id = state.get("user_id", settings.DEFAULT_VEHICLE_USER_ID)
    messages = state.get("messages", [])
    user_message = ""
    if messages:
        last = messages[-1]
        user_message = last.content if hasattr(last, "content") else str(last)

    context = memory_manager.get_context(user_id, user_message)

    return SUPERVISOR_PROMPT.format(
        routing_description=ROUTING_DESCRIPTION,
        user_profile=context.get("user_profile", {}),
        recalled_preferences=context.get("recalled_preferences", []),
        pending_reminders=context.get("pending_reminders", []),
    )


async def build_supervisor_graph() -> CompiledStateGraph:
    """
    构建 Supervisor 编排图（方式 A2 / 官方 Sub-Agents 模式）

    架构:
        ┌────────────────────────────────────┐
        │  Supervisor (create_agent)          │
        │  middleware=[CopilotKitMiddleware]  │ ← 注入 select_origin / update_map
        │  tools=[navigation_agent, ...,      │
        │         media_agent, ...]           │ ← 子Agent 包成 @tool 同步 invoke
        └────────────────────────────────────┘

    前端工具（select_origin / update_map）由 CopilotKitMiddleware 在 supervisor 层
    自动注入（读取 state["copilotkit"]["actions"]）。HITL 暂停只发生在 supervisor
    单一消息作用域，子 Agent 内部消息不冒泡，故不会产生孤儿 tool_call。

    Returns:
        编译后的 LangGraph 图，可直接传给 CopilotKit
    """
    logger.info("开始构建 AutoMind Supervisor 图（A2 模式）...")

    # 1. 加载 MCP 工具（异步方式）
    tools = await load_mcp_tools()
    logger.info(f"[初始化] MCP 工具 ({len(tools)} 个): {[t.name for t in tools]}")

    # 2. 创建子Agent（只持有各自的 MCP 工具，不含前端工具）
    agents = {
        "navigation_agent": create_navigation_agent(tools),
        "media_agent": create_media_agent(tools),
        "vehicle_agent": create_vehicle_agent(tools),
        "weather_agent": create_weather_agent(tools),
        "reminder_agent": create_reminder_agent(),
    }

    # 3. 把子Agent 包成 supervisor 可调用的 @tool
    subagent_tools = build_subagent_tools(agents)
    logger.info(f"[初始化] 子Agent 工具 ({len(subagent_tools)} 个): {[t.name for t in subagent_tools]}")

    # 4. 创建 supervisor（前端工具由 CopilotKitMiddleware 注入，无需手动加 stub）
    #    - dynamic_prompt: 每次模型调用前动态生成系统提示（注入记忆上下文）
    #    - CopilotKitMiddleware: 注入前端工具 select_origin / update_map
    #    create_agent 直接返回已编译图，checkpointer 在此处传入（无需再 .compile()）
    checkpointer = await get_checkpointer()
    graph = create_agent(
        model=create_llm(temperature=0.3),
        tools=subagent_tools,
        state_schema=AutoMindState,
        middleware=[_build_prompt, CopilotKitMiddleware()],
        checkpointer=checkpointer,
        name="supervisor",
    )

    logger.info(
        f"AutoMind Supervisor 图构建完成（A2） | "
        f"子Agent={len(agents)} MCP工具={len(tools)} 模型={settings.LLM_MODEL}"
    )
    return graph


# 全局图实例（延迟加载）
_graph_instance: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()

# ===== 持久化 Checkpointer 管理 =====
_checkpointer_stack = AsyncExitStack()
_checkpointer = None

async def get_checkpointer():
    """进程级单例：AsyncSqliteSaver 连接在整个应用生命周期内保持打开"""
    global _checkpointer
    if _checkpointer is None:
        db_path = str(settings.SQLITE_DB_PATH).replace("memory.db", "checkpoints.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _checkpointer = await _checkpointer_stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(db_path)
        )
    return _checkpointer

async def close_checkpointer():
    """关闭 checkpointer 连接（应用 shutdown 时调用）"""
    await _checkpointer_stack.aclose()


async def get_graph() -> CompiledStateGraph:
    """获取编译好的 Supervisor 图（单例，Double-Check Locking）"""
    global _graph_instance
    if _graph_instance is None:
        async with _graph_lock:
            if _graph_instance is None:
                _graph_instance = await build_supervisor_graph()
    return _graph_instance
