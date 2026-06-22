"""
导航子Agent
负责路径规划、POI搜索、路况查询、ETA预估

前端工具(update_map, select_origin)通过 CopilotKitMiddleware 自动注入到 Agent 的工具列表中，
前端 useFrontendTool / useHumanInTheLoop 注册的工具定义会通过 AG-UI 协议传到后端，
CopilotKitMiddleware 将它们转发给子 Agent，让 LLM 能看到并调用这些前端工具。
当 Agent 调用前端工具时，AG-UI 协议路由到前端 handler 执行，结果返回给 LLM 继续对话。
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from copilotkit import CopilotKitMiddleware

from app.models.llm import create_llm

NAVIGATION_PROMPT = """\
你是 AutoMind 的导航专家 Agent，专注于车辆导航相关任务。

你的能力：
- 路径规划：根据起终点规划最优驾驶路线（使用高德地图API）
- POI 搜索：搜索加油站、停车场、餐厅等兴趣点
- 路况查询：获取实时路况，提供避堵建议
- ETA 预估：预估到达时间

工作规则：
1. 如果用户没有明确起点（例如只说"导航去公司"而未说从哪出发），必须先调用 select_origin 前端工具，让用户选择起点
   - select_origin 的 options 参数设为: ["家", "公司", "火车站", "机场"]
   - select_origin 的 message 参数设为: "请选择您的出发地点："
   - 用户选择后，将该地点作为起点调用 plan_route
2. 调用 plan_route 获得路线数据后，必须立即调用 update_map 前端工具更新地图显示
   - action 参数设为 "navigate"
   - 传递完整的路线数据：destination, destination_lat, destination_lng, origin, origin_lat, origin_lng, distance_km, duration_min, steps, route_coords
3. 调用 search_poi 获得 POI 数据后，必须调用 update_map(action="search_poi") 来在地图上标记兴趣点
   - 传递 pois 参数: [{"name":"xx","lat":31.23,"lng":121.47}, ...]
4. 提供路线时，说明距离、时长和路况
5. 发现拥堵时主动建议绕行
6. 用简洁的车机语音风格回复，适合驾驶场景

重要：每次导航操作都必须调用 update_map 前端工具，否则用户看不到地图上的路线变化！"""


def create_navigation_agent(tools: list[BaseTool]):
    """创建导航子Agent，绑定导航 MCP 工具 + CopilotKitMiddleware 注入前端工具"""
    navigation_keywords = ["plan_route", "search_poi", "traffic"]
    navigation_tools = [
        t for t in tools
        if any(kw in t.name for kw in navigation_keywords)
    ]

    # CopilotKitMiddleware 会自动将前端注册的工具（useFrontendTool / useHumanInTheLoop）
    # 注入到 Agent 的工具列表中，不需要后端手动添加 stub
    return create_agent(
        model=create_llm(),
        tools=navigation_tools,
        name="navigation_agent",
        system_prompt=NAVIGATION_PROMPT,
        middleware=[CopilotKitMiddleware()],
    )
