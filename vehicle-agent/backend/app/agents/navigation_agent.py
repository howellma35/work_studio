"""
导航子Agent
负责路径规划、POI搜索、路况查询、ETA预估
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from app.models.llm import create_llm

NAVIGATION_PROMPT = """\
你是 AutoMind 的导航专家 Agent，专注于车辆导航相关任务。

你的能力：
- 路径规划：根据起终点规划最优驾驶路线
- POI 搜索：搜索加油站、停车场、餐厅等兴趣点
- 路况查询：获取实时路况，提供避堵建议
- ETA 预估：预估到达时间

工作规则：
1. 如果用户没有明确起点，默认使用“当前位置”
2. 提供路线时，说明距离、时长和路况
3. 发现拥堵时主动建议绕行
4. 用简洁的车机语音风格回复，适合驾驶场景

请基于工具调用结果，给出清晰、可执行的导航指令。"""


def create_navigation_agent(tools: list[BaseTool]):
    """创建导航子Agent，绑定导航相关工具"""
    navigation_tools = [
        t for t in tools
        if any(kw in t.name for kw in ["plan_route", "search_poi", "traffic"])
    ]
    return create_agent(
        model=create_llm(),
        tools=navigation_tools,
        name="navigation_agent",
        system_prompt=NAVIGATION_PROMPT,
    )
