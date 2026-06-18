"""
车辆控制子Agent
负责车窗、空调、门锁、座椅控制及状态查询
"""
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from app.models.llm import create_llm

VEHICLE_PROMPT = """\
你是 AutoMind 的车辆控制专家 Agent，负责车辆硬件控制。

你的能力：
- 车窗控制：升降车窗（前左/前右/后左/后右/全部）
- 空调控制：温度、模式、风速
- 门锁控制：锁车/解锁
- 座椅控制：位置调整、加热
- 状态查询：车辆整体状态

工作规则：
1. 执行控制前，明确告知用户将要执行的操作
2. 温度建议：夏天推荐 22-24℃，冬天推荐 20-22℃
3. 主动安全提醒（如"高速行驶中建议关闭车窗"）
4. 操作完成后简洁确认

请确保操作安全、合理，体现专业车机助手的服务品质。"""


def create_vehicle_agent(tools: list[BaseTool]):
    """创建车辆控制子Agent，绑定车辆硬件相关工具"""
    vehicle_tools = [
        t for t in tools
        if any(kw in t.name for kw in ["window", "climate", "door", "seat", "vehicle_status"])
    ]
    return create_react_agent(
        model=create_llm(),
        tools=vehicle_tools,
        name="vehicle_agent",
        prompt=VEHICLE_PROMPT,
    )
