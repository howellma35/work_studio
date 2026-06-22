"""
意图路由逻辑
Supervisor 根据用户意图动态路由到对应子Agent
"""
from langgraph.types import Command
from typing_extensions import Literal

# Agent 路由映射
AGENT_NAMES = ["navigation_agent", "media_agent", "vehicle_agent", "weather_agent", "reminder_agent"]

# 路由描述，注入 Supervisor 提示词
ROUTING_DESCRIPTION = """\
你可以将任务委派给以下专业子 Agent:

1. **navigation_agent** - 导航专家
   适用场景：路径规划、导航到某地、搜索附近地点、查路况、预估到达时间
   特殊行为：如用户未指定起点，会先通过 select_origin 前端工具让用户选择起点（家/公司/火车站/机场），再调用高德地图 API 规划路线
   示例："导航去公司"、"从家出发去机场"、"附近有加油站吗"、"去机场要多久"

2. **media_agent** - 多媒体专家
   适用场景：播放音乐、暂停、切歌、调音量、看歌单
   示例："放点音乐"、"把音量调大"、"下一首"

3. **vehicle_agent** - 车辆控制专家
   适用场景：车窗、空调、门锁、座椅、查车辆状态
   示例："打开车窗"、"空调调到24度"、"锁车"

4. **weather_agent** - 天气助手
   适用场景：查天气、查预报、出行建议
   示例："今天天气怎么样"、"明天会下雨吗"

5. **reminder_agent** - 智能提醒助手
   适用场景：创建提醒、看待办、保存偏好、上下文建议
   示例："提醒我下午3点开会"、"我有哪些待办"

路由规则：
- 根据用户意图选择最合适的子 Agent
- 如果意图模糊，先用 FINISH 反问澄清
- 复合请求可依次委派多个 Agent"""


def route_intent(state) -> Command[Literal["navigation_agent", "media_agent", "vehicle_agent", "weather_agent", "reminder_agent", "__end__"]]:
    """
    意图路由函数

    Supervisor LLM 会在 state["next"] 中输出目标 Agent 名称，
    此函数读取该值并返回对应路由 Command。
    """
    goto = state.get("next", "__end__")
    if goto not in AGENT_NAMES:
        goto = "__end__"
    return Command(goto=goto)
