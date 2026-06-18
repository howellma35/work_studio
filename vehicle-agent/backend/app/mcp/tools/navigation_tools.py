"""
MCP 导航工具集
模拟高德/百度地图 API，提供路径规划、POI搜索、路况查询能力
"""
from mcp.server.fastmcp import FastMCP

from app.config import settings

# 导航工具子服务器
mcp = FastMCP("NavigationTools")


@mcp.tool()
def plan_route(origin: str, destination: str, avoid_traffic: bool = False) -> dict:
    """
    规划驾驶路线

    Args:
        origin: 起点地址或地名（如"公司"、"上海中心大厦"）
        destination: 终点地址或地名
        avoid_traffic: 是否避开拥堵路段

    Returns:
        包含距离、时长、路线步骤的字典
    """
    # 模拟路径规划（真实环境对接 ${MAP_SERVICE_PROVIDER} API）
    distance_km = 12.5
    duration_min = 28 if not avoid_traffic else 35

    return {
        "status": "ok",
        "provider": settings.MAP_SERVICE_PROVIDER,
        "route": {
            "origin": origin,
            "destination": destination,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "avoid_traffic": avoid_traffic,
            "steps": [
                f"从 {origin} 出发，驶入主干道",
                f"沿主线行驶 {distance_km * 0.6:.1f} 公里",
                f"到达 {destination} 附近",
                f"导航结束，全程约 {duration_min} 分钟",
            ],
        },
    }


@mcp.tool()
def search_poi(keyword: str, location: str = "当前位置") -> dict:
    """
    搜索兴趣点（POI）

    Args:
        keyword: 搜索关键词（如"加油站"、"停车场"、"咖啡店"）
        location: 搜索中心位置

    Returns:
        POI 列表
    """
    # 模拟 POI 搜索结果
    mock_results = [
        {"name": f"{keyword}(人民广场店)", "address": f"{location}附近人民路88号", "distance_km": 1.2, "rating": 4.5},
        {"name": f"{keyword}(南京路店)", "address": f"{location}附近南京路168号", "distance_km": 2.8, "rating": 4.2},
        {"name": f"{keyword}(陆家嘴店)", "address": f"{location}附近世纪大道200号", "distance_km": 4.1, "rating": 4.7},
    ]
    return {
        "status": "ok",
        "keyword": keyword,
        "location": location,
        "results": mock_results,
        "total": len(mock_results),
    }


@mcp.tool()
def get_traffic_info(route_id: str = "current") -> dict:
    """
    获取实时路况信息

    Args:
        route_id: 路线 ID，默认查询当前导航路线

    Returns:
        路况信息（拥堵段、预计延误）
    """
    return {
        "status": "ok",
        "route_id": route_id,
        "overall": "轻度拥堵",
        "congestion_level": "moderate",
        "delay_min": 8,
        "segments": [
            {"road": "延安高架(西向东)", "status": "拥堵", "speed_kmh": 22},
            {"road": "内环高架", "status": "畅通", "speed_kmh": 60},
        ],
    }
