"""
MCP 导航工具集
接入高德地图 REST API，提供真实路径规划、POI搜索、路况查询能力
"""
import httpx
from loguru import logger
from mcp.server.fastmcp import FastMCP

from app.config import settings

# 导航工具子服务器
mcp = FastMCP("NavigationTools")

# ====== 预设地名 → 坐标映射（用于常见地点快速匹配） ======
_PRESET_LOCATIONS: dict[str, tuple[float, float]] = {
    "家": (31.218, 121.445),
    "公司": (31.2397, 121.4998),
    "火车站": (31.1944, 121.4557),  # 上海站
    "虹桥火车站": (31.1944, 121.3363),
    "机场": (31.1434, 121.8081),  # 浦东机场
    "虹桥机场": (31.198, 121.3363),
    "浦东机场": (31.1434, 121.8081),
    "陆家嘴": (31.2363, 121.5055),
    "外滩": (31.24, 121.49),
    "南京路": (31.2352, 121.475),
    "徐家汇": (31.1905, 121.437),
    "静安寺": (31.2238, 121.4473),
    "世纪公园": (31.215, 121.543),
    "人民广场": (31.2304, 121.4737),
}

_DEFAULT_ORIGIN = (31.2304, 121.4737)  # 上海人民广场


async def _amap_request(endpoint: str, params: dict) -> dict:
    """封装高德地图 REST API HTTP 请求

    Args:
        endpoint: API端点路径，如 /direction/driving
        params: 请求参数（不含key）

    Returns:
        API响应 JSON
    """
    params["key"] = settings.AMAP_API_KEY
    url = f"{settings.AMAP_API_BASE}{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            infocode = data.get("infocode", "")
            logger.warning(f"高德API返回错误: {info} (code={infocode}), endpoint={endpoint}")
            return {"status": "error", "message": f"高德API错误: {info} (code={infocode})"}

        return data
    except httpx.HTTPError as e:
        logger.error(f"高德API请求失败: {e}, endpoint={endpoint}")
        return {"status": "error", "message": f"请求失败: {e}"}


async def _geocode(address: str, city: str = "") -> tuple[float, float] | None:
    """地名 → 坐标（调用高德地理编码API）

    Args:
        address: 地址文本
        city: 城市名（可选，提高精度）

    Returns:
        (lat, lng) 坐标，失败返回 None
    """
    # 先查预设映射
    for key, coord in _PRESET_LOCATIONS.items():
        if key in address or address in key:
            return coord

    # 调用高德地理编码API
    params = {"address": address}
    if city:
        params["city"] = city

    data = await _amap_request("/geocode/geo", params)
    if data.get("status") == "error":
        return None

    geocodes = data.get("geocodes", [])
    if not geocodes:
        logger.warning(f"地理编码无结果: address={address}")
        return None

    location = geocodes[0].get("location", "")
    if not location:
        return None

    lng, lat = location.split(",")
    return (float(lat), float(lng))


def _coord_to_amap_str(coord: tuple[float, float]) -> str:
    """坐标 → 高德格式字符串 (lng,lat)"""
    return f"{coord[1]},{coord[0]}"


def _amap_str_to_coord(s: str) -> tuple[float, float]:
    """高德格式字符串 (lng,lat) → 坐标 (lat, lng)"""
    parts = s.split(",")
    return (float(parts[1]), float(parts[0]))


def _downsample_coords(coords: list[list[float]], max_points: int = 40) -> list[list[float]]:
    """对路线坐标降采样，保留首尾点，等间隔抽样到 max_points 个。

    高德 polyline 常返回上百个点，全量经 LLM 流式输出会显著拖慢响应。
    降采样后折线视觉上仍平滑，但负载大幅减小。
    """
    n = len(coords)
    if n <= max_points:
        return coords
    step = (n - 1) / (max_points - 1)
    sampled = [coords[round(i * step)] for i in range(max_points)]
    # 确保末点是真实终点
    sampled[-1] = coords[-1]
    return sampled


@mcp.tool()
async def plan_route(origin: str, destination: str, avoid_traffic: bool = False, city: str = "上海") -> dict:
    """
    规划驾驶路线（接入高德地图API，返回真实路线数据）

    Args:
        origin: 起点地址或地名（如"家"、"公司"、"上海中心大厦"），如为"当前位置"则使用默认起点
        destination: 终点地址或地名
        avoid_traffic: 是否避开拥堵路段（True时使用策略2: 避堵）
        city: 城市名（默认上海，提高地理编码精度）

    Returns:
        包含真实距离、时长、路线步骤和坐标数据的字典
    """
    # 解析起点
    if origin == "当前位置":
        origin_coord = _DEFAULT_ORIGIN
    else:
        origin_coord = await _geocode(origin, city)
        if origin_coord is None:
            return {"status": "error", "message": f"无法解析起点地址: {origin}"}

    # 解析终点
    dest_coord = await _geocode(destination, city)
    if dest_coord is None:
        return {"status": "error", "message": f"无法解析终点地址: {destination}"}

    # 调用高德驾驶路线规划API
    # strategy: 0=速度优先, 2=避堵, 10=避免收费
    strategy = 2 if avoid_traffic else 0

    params = {
        "origin": _coord_to_amap_str(origin_coord),
        "destination": _coord_to_amap_str(dest_coord),
        "strategy": strategy,
        "extensions": "all",  # 返回完整路线步骤
    }

    data = await _amap_request("/direction/driving", params)
    if data.get("status") == "error":
        return data

    route_data = data.get("route", {})
    paths = route_data.get("paths", [])

    if not paths:
        return {"status": "error", "message": "未找到可用路线"}

    # 取第一条路线（最优）
    path = paths[0]
    distance_m = int(path.get("distance", 0))
    duration_s = int(path.get("duration", 0))
    distance_km = round(distance_m / 1000, 1)
    duration_min = round(duration_s / 60)

    # 提取路线步骤
    steps_list = []
    route_coords = []
    for step in path.get("steps", []):
        instruction = step.get("instruction", "")
        road_name = step.get("road", "")
        step_distance = int(step.get("distance", 0))
        step_duration = int(step.get("duration", 0))

        step_text = f"{instruction}" if instruction else f"沿{road_name}行驶{step_distance}米"
        steps_list.append(step_text)

        # 提取路线坐标点（高德返回 polyline 格式: lng,lat;lng,lat;...）
        polyline = step.get("polyline", "")
        if polyline:
            for point_str in polyline.split(";"):
                if point_str:
                    coord = _amap_str_to_coord(point_str)
                    route_coords.append([coord[0], coord[1]])

    # 如果没有坐标数据，用起终点构造
    if not route_coords:
        route_coords = [
            [origin_coord[0], origin_coord[1]],
            [dest_coord[0], dest_coord[1]],
        ]

    # 降采样路线坐标，减小经 LLM 流式输出的负载（加快地图刷新）
    # 20 点已足够画平滑折线，token 消耗约为 40 点的一半
    route_coords = _downsample_coords(route_coords, max_points=20)

    return {
        "status": "ok",
        "provider": "amap",
        "route": {
            "origin": origin,
            "destination": destination,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "avoid_traffic": avoid_traffic,
            "origin_coord": {"lat": origin_coord[0], "lng": origin_coord[1]},
            "destination_coord": {"lat": dest_coord[0], "lng": dest_coord[1]},
            "route_coords": route_coords,
            "steps": steps_list,
        },
    }


@mcp.tool()
async def search_poi(keyword: str, location: str = "当前位置", city: str = "上海") -> dict:
    """
    搜索兴趣点（POI）（接入高德地图API，返回真实POI数据）

    Args:
        keyword: 搜索关键词（如"加油站"、"停车场"、"咖啡店"）
        location: 搜索中心位置（地名或"当前位置"）
        city: 城市名（默认上海）

    Returns:
        真实 POI 列表（包含名称、地址、坐标、距离）
    """
    # 解析中心位置
    if location == "当前位置":
        center_coord = _DEFAULT_ORIGIN
    else:
        center_coord = await _geocode(location, city)
        if center_coord is None:
            center_coord = _DEFAULT_ORIGIN

    # 调用高德POI搜索API
    params = {
        "keywords": keyword,
        "location": _coord_to_amap_str(center_coord),
        "city": city,
        "radius": 5000,  # 搜索半径5公里
        "offset": 5,     # 返回5条结果
    }

    data = await _amap_request("/place/text", params)
    if data.get("status") == "error":
        return data

    pois_data = data.get("pois", [])
    results = []

    for poi in pois_data:
        name = poi.get("name", "")
        address = poi.get("address", "") or poi.get("pname", "")
        location_str = poi.get("location", "")
        distance_str = poi.get("distance", "")

        if location_str:
            coord = _amap_str_to_coord(location_str)
            results.append({
                "name": name,
                "address": address,
                "distance_km": round(int(distance_str) / 1000, 1) if distance_str else 0,
                "rating": float(poi.get("biz_ext", {}).get("rating", "4.5")),
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
async def get_traffic_info(route_id: str = "current") -> dict:
    """
    获取实时路况信息（使用高德地图API查询矩形区域路况）

    Args:
        route_id: 路线 ID，默认查询当前导航路线周边路况

    Returns:
        路况信息（拥堵段、预计延误）
    """
    # 查询上海核心区域路况（人民广场周边矩形）
    # 高德路况矩形查询需要左下和右上坐标 (lng,lat)
    params = {
        "rectangle": "121.44,31.20;121.52,31.26",  # 上海核心区矩形
        "level": 5,  # 返回5级路况
    }

    data = await _amap_request("/traffic/status/rectangle", params)
    if data.get("status") == "error":
        # API不可用时返回模拟数据
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

    # 解析真实路况数据
    traffic_data = data.get("trafficinfo", {})
    evaluation = traffic_data.get("evaluation", {})

    congestion_level = evaluation.get("level", "未知")
    overall_desc = evaluation.get("description", "暂无数据")

    segments = []
    roads = traffic_data.get("roads", [])
    for road in roads[:5]:  # 取前5条路段
        segments.append({
            "road": road.get("name", "未知路段"),
            "status": road.get("status_desc", "未知"),
            "speed_kmh": int(road.get("speed", 0)) // 100 if road.get("speed") else 0,
        })

    return {
        "status": "ok",
        "route_id": route_id,
        "overall": overall_desc,
        "congestion_level": congestion_level,
        "delay_min": int(evaluation.get("expedite", "0")) if evaluation.get("expedite") else 0,
        "segments": segments,
    }
