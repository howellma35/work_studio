"""
MCP 车辆控制工具集
模拟车机接口，提供车窗、空调、门锁、座椅控制能力
"""
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("VehicleTools")

# 模拟车辆状态
_vehicle_state = {
    "windows": {"front_left": 0, "front_right": 0, "rear_left": 0, "rear_right": 0},  # 0-100 开度
    "climate": {"temperature": settings.DEFAULT_VEHICLE_TEMP, "mode": "cooling", "fan_speed": 2, "is_on": False},
    "doors": {"locked": True},
    "seats": {"driver_position": "normal", "heated": False},
    "battery": 78,
    "mileage": 15234,
}


@mcp.tool()
def control_window(position: str, action: str) -> dict:
    """
    控制车窗升降

    Args:
        position: 车窗位置 (front_left / front_right / rear_left / rear_right / all)
        action: 操作 (open / close / half)

    Returns:
        车窗最新状态
    """
    targets = ["front_left", "front_right", "rear_left", "rear_right"] if position == "all" else [position]
    value = {"open": 100, "close": 0, "half": 50}.get(action, 0)

    for p in targets:
        if p in _vehicle_state["windows"]:
            _vehicle_state["windows"][p] = value

    return {"status": "ok", "action": f"车窗{action}", "position": position, "windows": _vehicle_state["windows"]}


@mcp.tool()
def set_climate(temperature: int = 22, mode: str = "auto", fan_speed: int = 2, turn_on: bool = True) -> dict:
    """
    设置空调

    Args:
        temperature: 目标温度 16-30
        mode: 模式 (cooling/heating/auto/defrost)
        fan_speed: 风速 1-5
        turn_on: 是否开启

    Returns:
        空调最新状态
    """
    _vehicle_state["climate"]["temperature"] = max(16, min(30, temperature))
    _vehicle_state["climate"]["mode"] = mode
    _vehicle_state["climate"]["fan_speed"] = max(1, min(5, fan_speed))
    _vehicle_state["climate"]["is_on"] = turn_on

    return {"status": "ok", "action": "空调设置", "climate": _vehicle_state["climate"]}


@mcp.tool()
def lock_doors(action: str = "lock") -> dict:
    """
    锁止/解锁车门

    Args:
        action: 操作 (lock/unlock)

    Returns:
        门锁状态
    """
    _vehicle_state["doors"]["locked"] = (action == "lock")
    return {"status": "ok", "action": f"车门{action}", "doors": _vehicle_state["doors"]}


@mcp.tool()
def set_seat(position: str = "normal", heated: bool = False) -> dict:
    """
    调整驾驶座椅

    Args:
        position: 座椅位置 (normal/comfort/sport)
        heated: 是否加热

    Returns:
        座椅状态
    """
    _vehicle_state["seats"]["driver_position"] = position
    _vehicle_state["seats"]["heated"] = heated
    return {"status": "ok", "action": "座椅调整", "seats": _vehicle_state["seats"]}


@mcp.tool()
def get_vehicle_status() -> dict:
    """
    获取车辆完整状态

    Returns:
        车辆所有子系统状态（车窗/空调/门锁/座椅/电量/里程）
    """
    return {
        "status": "ok",
        "vehicle": _vehicle_state,
    }
