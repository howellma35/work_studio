"""
MCP 导航工具集
模拟高德/百度地图 API，提供路径规划、POI搜索、路况查询能力
"""
import math
import random
from mcp.server.fastmcp import FastMCP

from app.config import settings

# 导航工具子服务器
mcp = FastMCP("NavigationTools")

# ====== 地名 → 坐标映射（模拟地理编码） ======
_DEST_COORDS: dict[str, tuple[float, float]] = {
    "公司": (31.2397, 121.4998),
    "陆家嘴": (31.2363, 121.5055),
    "外滩": (31.24, 121.49),
    "南京路": (31.2352, 121.475),
    "虹桥机场": (31.198, 121.3363),
    "浦东机场": (31.1434, 121.8081),
    "徐家汇": (31.1905, 121.437),
    "静安寺": (31.2238, 121.4473),
    "世纪公园": (31.215, 121.543),
    "家": (31.218, 121.445),
    "加油站": (31.225, 121.46),
    "停车场": (31.232, 121.48),
    "餐厅": (31.228, 121.472),
    "医院": (31.22, 121.465),
}

_DEFAULT_ORIGIN = (31.2304, 121.4737)  # 上海人民广场


def _resolve(name: str) -> tuple[float, float]:
    """地名 → 坐标，未知地名在默认位置附近随机偏移"""
    for key, coord in _DEST_COORDS.items():
        if key in name or name in key:
            return coord
    return (
        _DEFAULT_ORIGIN[0] + (random.random() - 0.5) * 0.04,
        _DEFAULT_ORIGIN[1] + (random.random() - 0.5) * 0.04,
    )


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点间距离（km）"""
    R = 6371
    dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a[0]))
        * math.cos(math.radians(b[0]))
        * math.sin(dlng / 2) ** 2
    )
    return round(R * 2 * math.asin(math.sqrt(h)), 1)


def _generate_route(
    origin: tuple[float, float], dest: tuple[float, float]
) -> list[list[float]]:
    """生成带随机偏移的折线坐标序列"""
    pts: list[list[float]] = [list(origin)]
    steps = 5 + random.randint(0, 3)
    for i in range(1, steps):
        t = i / steps
        pts.append([
            origin[0] + (dest[0] - origin[0]) * t + (random.random() - 0.5) * 0.006,
            origin[1] + (dest[1] - origin[1]) * t + (random.random() - 0.5) * 0.006,
        ])
    pts.append(list(dest))
    return pts


@mcp.tool()
def plan_route(origin: str, destination: str, avoid_traffic: bool = False) -> dict:
    """
    规划驾驶路线

    Args:
        origin: 起点地址或地名（如"公司"、"上海中心大厦"）
        destination: 终点地址或地名
        avoid_traffic: 是否避开拥堵路段

    Returns:
        包含距离、时长、路线步骤和坐标数据的字典
    """
    origin_coord = _resolve(origin) if origin != "当前位置" else _DEFAULT_ORIGIN
    dest_coord = _resolve(destination)
    distance_km = _haversine(origin_coord, dest_coord)
    duration_min = round(distance_km * 2.2) if not avoid_traffic else round(distance_km * 2.8)

    return {
        "status": "ok",
        "provider": settings.MAP_SERVICE_PROVIDER,
        "route": {
            "origin": origin,
            "destination": destination,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "avoid_traffic": avoid_traffic,
            "origin_coord": {"lat": origin_coord[0], "lng": origin_coord[1]},
            "destination_coord": {"lat": dest_coord[0], "lng": dest_coord[1]},
            "route_coords": _generate_route(origin_coord, dest_coord),
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
        POI 列表（包含坐标）
    """
    center = _resolve(location) if location != "当前位置" else _DEFAULT_ORIGIN
    results = []
    for suffix in ["人民广场店", "南京路店", "陆家嘴店"]:
        offset_lat = (random.random() - 0.5) * 0.02
        offset_lng = (random.random() - 0.5) * 0.02
        coord = (center[0] + offset_lat, center[1] + offset_lng)
        dist = _haversine(center, coord)
        results.append({
            "name": f"{keyword}({suffix})",
            "address": f"{location}附近",
            "distance_km": dist,
            "rating": round(4.0 + random.random() * 0.9, 1),
            "lat": coord[0],
            "lng": coord[1],
        })
    return {
        "status": "ok",
        "keyword": keyword,
        "location": location,
        "results": results,
        "total": len(results),
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
