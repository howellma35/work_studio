"""
前端工具桥接定义
定义 update_map 和 select_origin 的 LangChain StructuredTool，
schema 与前端 useFrontendTool 定义一致，让 navigation_agent LLM 能看到并调用这些工具。

实际执行由 AG-UI 协议路由到前端 handler，这里只定义 schema 作为桥接。
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class UpdateMapInput(BaseModel):
    """update_map 前端工具参数定义"""
    action: str = Field(description="操作类型: navigate=导航, search_poi=搜索兴趣点, clear=清除路线")
    destination: str | None = Field(default=None, description="目的地名称（navigate 时必填）")
    destination_lat: float | None = Field(default=None, description="目的地纬度")
    destination_lng: float | None = Field(default=None, description="目的地经度")
    origin: str | None = Field(default=None, description="起点名称")
    origin_lat: float | None = Field(default=None, description="起点纬度")
    origin_lng: float | None = Field(default=None, description="起点经度")
    distance_km: float | None = Field(default=None, description="距离（公里）")
    duration_min: float | None = Field(default=None, description="预计时长（分钟）")
    steps: list[str] | None = Field(default=None, description="路线步骤描述列表")
    route_coords: list[list[float]] | None = Field(
        default=None,
        description="路线坐标序列 [[lat, lng], ...]"
    )
    pois: list[dict] | None = Field(
        default=None,
        description="POI 列表，格式: [{'name': 'xxx', 'lat': 31.23, 'lng': 121.47}, ...]"
    )


class SelectOriginInput(BaseModel):
    """select_origin 前端工具参数定义"""
    options: list[str] = Field(
        default=["家", "公司", "火车站", "机场"],
        description="可选起点列表"
    )
    message: str = Field(
        default="请选择您的出发地点：",
        description="询问起点时展示给用户的提示文本"
    )


def _update_map_stub(**kwargs) -> str:
    """update_map 桥接执行函数（占位，实际执行由前端 handler 完成）

    当 AG-UI 协议正确路由时，此函数不会被调用。
    如果协议未路由，则返回占位信息。
    """
    action = kwargs.get("action", "unknown")
    if action == "navigate":
        dest = kwargs.get("destination", "目的地")
        origin = kwargs.get("origin", "当前位置")
        return f"地图导航已更新: {origin} → {dest}"
    elif action == "search_poi":
        return f"地图已显示搜索结果"
    elif action == "clear":
        return "地图已清除导航数据"
    return "地图更新完成"


def _select_origin_stub(options: list[str] | None = None, message: str = "") -> str:
    """select_origin 桥接执行函数（占位，实际执行由前端 handler 完成）

    当 AG-UI 协议正确路由时，此函数不会被调用。
    如果协议未路由，则返回默认选择。
    """
    return "当前位置"


# 创建 LangChain StructuredTool 实例
update_map_tool = StructuredTool.from_function(
    func=_update_map_stub,
    name="update_map",
    description="更新地图显示。当规划导航路线、搜索 POI 或更新位置时调用此前端工具。"
                "调用 plan_route 获得路线数据后，必须调用此工具将路线显示到地图上。",
    args_schema=UpdateMapInput,
)

select_origin_tool = StructuredTool.from_function(
    func=_select_origin_stub,
    name="select_origin",
    description="让用户选择导航起点位置。当用户没有指定起点时，调用此前端工具弹出选择面板，"
                "提供家、公司、火车站、机场等常见起点选项供用户选择。",
    args_schema=SelectOriginInput,
)


# 所有前端桥接工具列表
FRONTEND_BRIDGE_TOOLS = [update_map_tool, select_origin_tool]
