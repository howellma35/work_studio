"""
子 Agent → @tool 封装（方式 A2 / 官方 Sub-Agents 模式）

把每个专业子 Agent 包成一个 LangChain @tool：
- supervisor（create_agent）持有这些工具 + 前端工具（select_origin/update_map）
- 工具内部 `await sub_agent.ainvoke({"messages":[HumanMessage(task)]})` 同步执行
- 只把子 Agent 最终回复文本作为 ToolMessage 返回给 supervisor

关键收益：子 Agent 内部消息不冒泡到 supervisor 共享历史，
HITL 暂停只发生在 supervisor 单一作用域，彻底规避 INVALID_CHAT_HISTORY。
"""
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool, tool
from loguru import logger


def _extract_text(result: dict) -> str:
    """从子 Agent 返回的 state 中取最后一条 AI 文本回复"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content
            if isinstance(content, list):
                # 兼容多段 content（取 text 段拼接）
                content = "".join(
                    seg.get("text", "") if isinstance(seg, dict) else str(seg)
                    for seg in content
                )
            if content and content.strip():
                return content.strip()
    return "（子 Agent 未返回文本结果）"


async def _invoke_subagent(sub_agent, task: str, name: str) -> str:
    """统一的子 Agent 调用入口"""
    logger.info(f"[子Agent调用] {name} <- {task!r}")
    try:
        result = await sub_agent.ainvoke({"messages": [HumanMessage(content=task)]})
    except Exception as e:  # noqa: BLE001
        logger.error(f"[子Agent调用] {name} 执行失败: {e}")
        return f"{name} 执行出错：{e}"
    text = _extract_text(result)
    logger.info(f"[子Agent调用] {name} -> {text[:120]!r}")
    return text


def build_subagent_tools(agents: dict[str, object]) -> list[BaseTool]:
    """根据已创建的子 Agent 字典，生成对应的 @tool 列表

    Args:
        agents: {"navigation_agent": <agent>, "media_agent": <agent>, ...}
    """
    nav = agents["navigation_agent"]
    media = agents["media_agent"]
    vehicle = agents["vehicle_agent"]
    weather = agents["weather_agent"]
    reminder = agents["reminder_agent"]
    knowledge = agents["knowledge_agent"]

    @tool
    async def navigation_agent(task: str) -> str:
        """导航专家：路径规划、POI搜索、路况查询、ETA预估。
        task 需包含明确的起点和终点（如「从家导航到陆家嘴」）。
        返回一句话摘要 + ROUTE_DATA/POI_DATA JSON 行，供 supervisor 调用 update_map。"""
        return await _invoke_subagent(nav, task, "navigation_agent")

    @tool
    async def media_agent(task: str) -> str:
        """多媒体专家：播放/暂停音乐、切歌、调音量、查看歌单。"""
        return await _invoke_subagent(media, task, "media_agent")

    @tool
    async def vehicle_agent(task: str) -> str:
        """车辆控制专家：车窗、空调、门锁、座椅控制及车辆状态查询。"""
        return await _invoke_subagent(vehicle, task, "vehicle_agent")

    @tool
    async def weather_agent(task: str) -> str:
        """天气助手：实时天气、未来预报、出行建议。"""
        return await _invoke_subagent(weather, task, "weather_agent")

    @tool
    async def reminder_agent(task: str) -> str:
        """智能提醒助手：创建提醒、查看待办、保存用户偏好。"""
        return await _invoke_subagent(reminder, task, "reminder_agent")

    @tool
    async def knowledge_agent(task: str) -> str:
        """知识库助手：从知识库检索车辆手册、保养记录、个人档案等信息。
        仅当用户问题涉及知识性内容时调用（如"胎压标准"、"保养记录"、"保险到期"）。
        操作性问题（导航/音乐/空调控制）不需要检索知识库。
        返回结果附带来源标注（[来源: 文档名 | 相关度: xx]）。"""
        return await _invoke_subagent(knowledge, task, "knowledge_agent")

    return [navigation_agent, media_agent, vehicle_agent, weather_agent, reminder_agent, knowledge_agent]
