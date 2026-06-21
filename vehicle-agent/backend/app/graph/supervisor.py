"""
AutoMind Supervisor Agent - 多Agent编排核心

使用 langgraph-supervisor 构建 Supervisor 模式编排:
- Supervisor 负责意图识别、任务分发、结果汇总
- 5 个专业子Agent 各自处理特定领域任务
- 支持动态路由与模糊意图澄清

这是整个系统的"大脑"，通过 LangGraph 状态图协调所有子Agent。
"""
import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph_supervisor import create_supervisor
from loguru import logger

from app.agents.media_agent import create_media_agent
from app.agents.navigation_agent import create_navigation_agent
from app.agents.reminder_agent import create_reminder_agent
from app.agents.vehicle_agent import create_vehicle_agent
from app.agents.weather_agent import create_weather_agent
from app.config import settings
from app.graph.routing import ROUTING_DESCRIPTION
from app.memory.manager import memory_manager
from app.mcp.client import load_mcp_tools
from app.models.llm import create_llm

SUPERVISOR_PROMPT = """\
你是 AutoMind，一个智能车载助手。你的核心职责是理解车主需求，并将任务委派给最合适的专业子Agent。

{routing_description}

## 你的工作流程
1. 分析用户最新消息，识别意图
2. 将任务委派给对应子Agent（transfer_to_xxx）
3. 子Agent 执行工具调用并返回结果
4. 汇总结果，用自然的语音回复用户

## 用户偏好上下文（来自记忆系统）
用户档案: {user_profile}
召回偏好: {recalled_preferences}
待办提醒: {pending_reminders}

## 交互规范
- 用简洁、自然的口语回复，适合驾驶场景（单次回复控制在 50 字以内）
- 主动关怀：结合天气、时间、提醒给出贴心建议
- 模糊意图澄清：如果不确定用户想要什么，礼貌反问
- 安全第一：涉及车辆操作时，确认无误后执行
- 中文回复，语气亲切专业

记住：你是车主的全能智能助手，目标是让驾驶更安全、更便捷、更愉悦。"""


def _build_prompt(state: dict) -> list:
    """动态构建 Supervisor 提示词，注入记忆上下文和对话历史

    返回 [SystemMessage, ...messages] 列表，确保模型同时看到：
    1. 系统指令（路由规则 + 用户偏好上下文）
    2. 完整对话历史（用户说了什么、之前聊了什么）
    """
    from langchain_core.messages import SystemMessage

    user_id = state.get("user_id", settings.DEFAULT_VEHICLE_USER_ID)
    messages = state.get("messages", [])
    user_message = ""
    if messages:
        last = messages[-1]
        user_message = last.content if hasattr(last, "content") else str(last)

    context = memory_manager.get_context(user_id, user_message)

    system_content = SUPERVISOR_PROMPT.format(
        routing_description=ROUTING_DESCRIPTION,
        user_profile=context.get("user_profile", {}),
        recalled_preferences=context.get("recalled_preferences", []),
        pending_reminders=context.get("pending_reminders", []),
    )

    # 关键：返回 SystemMessage + 完整对话历史，不能只返回系统消息
    # 如果只返回字符串，langgraph 的 create_react_agent 会丢弃对话历史，
    # 导致模型看不到用户消息，无法产生 tool_calls
    return [SystemMessage(content=system_content)] + list(messages)


async def build_supervisor_graph() -> CompiledStateGraph:
    """
    构建 Supervisor 多Agent编排图

    架构:
        ┌──────────────┐
        │  Supervisor   │ ← 意图识别 + 任务分发 + 结果汇总
        └──────┬───────┘
               ├─→ navigation_agent
               ├─→ media_agent
               ├─→ vehicle_agent
               ├─→ weather_agent
               └─→ reminder_agent

    每个子Agent 执行完毕后返回 Supervisor，由 Supervisor 决定
    是否需要继续委派或结束对话。

    Returns:
        编译后的 LangGraph 图，可直接传给 CopilotKit
    """
    logger.info("开始构建 AutoMind Supervisor 图...")

    # 1. 加载 MCP 工具（异步方式）
    tools = await load_mcp_tools()

    # 2. 创建子Agent
    agents = [
        create_navigation_agent(tools),
        create_media_agent(tools),
        create_vehicle_agent(tools),
        create_weather_agent(tools),
        create_reminder_agent(),
    ]

    # 3. 构建 Supervisor 编排
    supervisor = create_supervisor(
        agents=agents,
        model=create_llm(temperature=0.3),
        prompt=_build_prompt,
    )

    # 4. 编译图，附加 checkpointer 实现多轮对话记忆
    graph = supervisor.compile(checkpointer=MemorySaver())

    logger.info(
        f"AutoMind Supervisor 图构建完成 | "
        f"子Agent={len(agents)} 工具={len(tools)} 模型={settings.LLM_MODEL}"
    )
    return graph


# 全局图实例（延迟加载）
_graph_instance: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()


async def get_graph() -> CompiledStateGraph:
    """获取编译好的 Supervisor 图（单例，Double-Check Locking）"""
    global _graph_instance
    if _graph_instance is None:
        async with _graph_lock:
            if _graph_instance is None:
                _graph_instance = await build_supervisor_graph()
    return _graph_instance
