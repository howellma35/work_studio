"""
天气查询子Agent
负责实时天气、未来预报、出行建议
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from app.models.llm import create_llm

WEATHER_PROMPT = """\
你是 AutoMind 的天气助手 Agent，提供天气信息服务。

你的能力：
- 实时天气查询：温度、天气状况、湿度、风力、空气质量
- 未来天气预报：多日预报、降雨概率
- 出行建议：根据天气给出驾驶建议

工作规则：
1. 回答简洁明了，突出关键信息（温度、是否下雨）
2. 主动关联车辆控制（如"今日有雨，建议关闭天窗"）
3. 空气质量差时建议关窗开内循环
4. 结合用户位置（默认上海）给出本地天气

请以贴心的车机助手口吻回复。"""


def create_weather_agent(tools: list[BaseTool]):
    """创建天气查询子Agent，绑定天气相关工具"""
    weather_tools = [
        t for t in tools
        if any(kw in t.name for kw in ["weather", "forecast"])
    ]
    return create_agent(
        model=create_llm(temperature=0.3),
        tools=weather_tools,
        name="weather_agent",
        system_prompt=WEATHER_PROMPT,
    )
