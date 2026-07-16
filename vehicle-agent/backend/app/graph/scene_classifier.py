"""
驾驶场景分类器 — 基于车况数据+用户上下文判断当前驾驶场景

分类逻辑:
1. 优先判断紧急态（报警灯/故障）
2. 基于档位判断停车态
3. 基于速度判断高速/城市
4. 默认回退到待机态

输出: scene_type + confidence + transition_reason
"""
from loguru import logger

from app.graph.scene_config import DrivingScene


def classify_scene(vehicle_status: dict) -> dict:
    """基于车况数据判断当前驾驶场景

    Args:
        vehicle_status: 车辆状态快照，包含:
            - speed: 当前速度 (km/h)
            - gear: 当前档位 (P/R/N/D/S)
            - alerts: 报警信息列表 [{"severity": str, "description": str}]
            - battery: 电池电量 (%)
            - engine_temp: 发动机温度 (°C)
            - tire_pressure: 胎压信息 dict

    Returns:
        {
            "scene": DrivingScene 枚举值,
            "confidence": 0.0-1.0,
            "reason": 判断原因描述,
            "scene_config": SceneConfig 对应配置,
        }
    """
    speed = vehicle_status.get("speed", 0)
    gear = vehicle_status.get("gear", "P")
    alerts = vehicle_status.get("alerts", [])
    engine_temp = vehicle_status.get("engine_temp", 90)

    # ===== 1. 优先判断紧急态 =====
    # 有严重报警灯、发动机过热、电池极低
    if alerts and any(a.get("severity") == "critical" for a in alerts):
        reason = f"检测到紧急警报: {alerts[0].get('description', '未知')}"
        logger.warning(f"[场景分类] 紧急态: {reason}")
        return {
            "scene": DrivingScene.EMERGENCY,
            "confidence": 0.95,
            "reason": reason,
        }

    # 发动机过热 (>110°C)
    if engine_temp > 110:
        reason = f"发动机温度异常: {engine_temp}°C"
        logger.warning(f"[场景分类] 紧急态: {reason}")
        return {
            "scene": DrivingScene.EMERGENCY,
            "confidence": 0.90,
            "reason": reason,
        }

    # ===== 2. 基于档位判断停车态 =====
    if gear == "P":
        return {
            "scene": DrivingScene.PARKED,
            "confidence": 0.9,
            "reason": "车辆处于停车档",
        }

    # ===== 3. 基于速度判断高速/城市 =====
    if speed >= 60:
        return {
            "scene": DrivingScene.HIGHWAY,
            "confidence": 0.85,
            "reason": f"当前速度{speed:.0f}km/h，高速行驶",
        }
    elif speed > 0:
        return {
            "scene": DrivingScene.CITY_DRIVING,
            "confidence": 0.80,
            "reason": f"当前速度{speed:.0f}km/h，市区行驶",
        }

    # ===== 4. 默认回退到待机态 =====
    # speed=0 且非P档（等红灯、刚启动等）
    return {
        "scene": DrivingScene.IDLE,
        "confidence": 0.70,
        "reason": "车辆静止待机",
    }


def should_transition(current_scene: DrivingScene, new_scene: DrivingScene) -> bool:
    """判断是否需要场景切换（避免频繁来回切换）

    过渡守卫规则:
    - 紧急态 → 任何态：总是允许（紧急优先）
    - 任何态 → 紧急态：总是允许（紧急优先）
    - 高速 ↔ 城市：允许（速度变化自然切换）
    - 城市 ↔ 待机：允许（等红灯）
    - 停车 → 待机/城市：允许（出发）
    - 其他：不允许（避免不合理切换）
    """
    # 紧急态相关切换总是允许
    if current_scene == DrivingScene.EMERGENCY or new_scene == DrivingScene.EMERGENCY:
        return True

    # 合理的过渡路径
    valid_transitions = {
        (DrivingScene.IDLE, DrivingScene.CITY_DRIVING),
        (DrivingScene.IDLE, DrivingScene.PARKED),
        (DrivingScene.IDLE, DrivingScene.HIGHWAY),
        (DrivingScene.CITY_DRIVING, DrivingScene.IDLE),
        (DrivingScene.CITY_DRIVING, DrivingScene.HIGHWAY),
        (DrivingScene.HIGHWAY, DrivingScene.CITY_DRIVING),
        (DrivingScene.HIGHWAY, DrivingScene.IDLE),
        (DrivingScene.PARKED, DrivingScene.IDLE),
        (DrivingScene.PARKED, DrivingScene.CITY_DRIVING),
    }

    return (current_scene, new_scene) in valid_transitions
