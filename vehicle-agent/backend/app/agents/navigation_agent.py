"""
导航子Agent
负责路径规划、POI搜索、路况查询、ETA预估

【方式 A2 架构】
本子 Agent 只持有自己的 MCP 工具（plan_route / search_poi / get_traffic_info），
不再挂载 CopilotKitMiddleware。前端工具（select_origin / update_map）由顶层 supervisor
持有（官方 Sub-Agents 模式：supervisor = create_agent + CopilotKitMiddleware）。

子 Agent 由 supervisor 通过 @tool 同步 invoke 调用，内部消息不冒泡到 supervisor，
因此 HITL 暂停只发生在 supervisor 单一作用域，不会产生跨作用域孤儿 tool_call。
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from app.models.llm import create_llm

NAVIGATION_PROMPT = """\
你是 AutoMind 的导航专家 Agent，专注于车辆导航相关任务。

你的能力：
- 路径规划：根据起终点规划最优驾驶路线（使用高德地图API）
- POI 搜索：搜索加油站、停车场、餐厅等兴趣点
- 路况查询：获取实时路况，提供避堵建议
- ETA 预估：预估到达时间

工作规则：
1. 调用方（supervisor）会在任务里给出明确的起点和终点。直接用它们调用 plan_route 规划路线。
   - 若任务未给起点，默认用 "当前位置" 作为 origin（不要询问用户，起点询问由 supervisor 负责）。
2. 用 search_poi 搜索兴趣点；用 get_traffic_info 查询路况。
3. 返回结果时，必须用如下**结构化格式**回给 supervisor（供其调用前端 update_map）：
   先给一句话摘要（含距离/时长/路况），再附一段以 `ROUTE_DATA:` 开头的 JSON 行：
   ROUTE_DATA: {"origin":"家","destination":"陆家嘴","origin_lat":31.218,"origin_lng":121.445,"destination_lat":31.236,"destination_lng":121.506,"distance_km":8.5,"duration_min":25,"route_coords":[[lat,lng],...],"steps":["..."]}
   POI 搜索则返回 POI_DATA: {"pois":[{"name":"xx","lat":31.23,"lng":121.47}, ...]}
4. 不要调用任何前端工具（update_map / select_origin），那是 supervisor 的职责。
5. 摘要用简洁的车机语音风格，不要逐条复述全部路线步骤。"""


def create_navigation_agent(tools: list[BaseTool]):
    """创建导航子Agent，只绑定导航 MCP 工具（前端工具由 supervisor 持有）"""
    navigation_keywords = ["plan_route", "search_poi", "traffic"]
    navigation_tools = [
        t for t in tools
        if any(kw in t.name for kw in navigation_keywords)
    ]

    return create_agent(
        model=create_llm(temperature=0.3),
        tools=navigation_tools,
        name="navigation_agent",
        system_prompt=NAVIGATION_PROMPT,
    )
