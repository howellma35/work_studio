"""
驾驶场景配置 — 每种场景对应不同的工具集、回复风格和安全等级

5 种驾驶场景:
- idle:        车辆静止待机（刚启动、等红灯）
- city_driving: 市区行驶 (speed < 60km/h)
- highway:     高速行驶 (speed ≥ 60km/h)
- parked:      停车档 (gear = P)
- emergency:   紧急事件（故障、事故、报警灯亮）

每种场景配置:
- max_response_words:  最大回复字数（驾驶中越短越好）
- allowed_tools:       该场景下允许的子 Agent 工具关键词
- blocked_tools:       该场景下禁止的子 Agent 工具关键词
- safety_level:        安全等级 (low/medium/high/critical)
- proactive_interval:  主动推荐间隔（秒），0 = 立即推送
- response_style:      回复风格描述，注入 supervisor prompt
- scene_label:         前端显示的场景名称
- scene_icon:          前端显示的场景图标
"""
from dataclasses import dataclass, field
from enum import Enum


class DrivingScene(str, Enum):
    """驾驶场景枚举"""
    IDLE = "idle"
    CITY_DRIVING = "city_driving"
    HIGHWAY = "highway"
    PARKED = "parked"
    EMERGENCY = "emergency"


class SafetyLevel(str, Enum):
    """安全等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SceneConfig:
    """单个驾驶场景的配置"""
    max_response_words: int = 100
    allowed_tools: list[str] = field(default_factory=lambda: ["all"])
    blocked_tools: list[str] = field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.LOW
    proactive_interval: int = 300
    response_style: str = "friendly_detailed"
    scene_label: str = ""
    scene_icon: str = ""


# ===== 场景 → 配置映射 =====
SCENE_CONFIGS: dict[DrivingScene, SceneConfig] = {
    DrivingScene.IDLE: SceneConfig(
        max_response_words=100,
        allowed_tools=["all"],
        blocked_tools=[],
        safety_level=SafetyLevel.LOW,
        proactive_interval=300,
        response_style="friendly_detailed",
        scene_label="待机",
        scene_icon="🅿️",
    ),
    DrivingScene.CITY_DRIVING: SceneConfig(
        max_response_words=50,
        allowed_tools=["navigation", "weather", "media_basic", "vehicle_basic"],
        blocked_tools=["control_window", "set_seat"],
        safety_level=SafetyLevel.MEDIUM,
        proactive_interval=60,
        response_style="brief_actionable",
        scene_label="市区行驶",
        scene_icon="🚗",
    ),
    DrivingScene.HIGHWAY: SceneConfig(
        max_response_words=30,
        allowed_tools=["navigation", "weather"],
        blocked_tools=["control_window", "set_seat", "lock_doors", "set_climate"],
        safety_level=SafetyLevel.HIGH,
        proactive_interval=120,
        response_style="minimal_alert",
        scene_label="高速行驶",
        scene_icon="🛣️",
    ),
    DrivingScene.PARKED: SceneConfig(
        max_response_words=150,
        allowed_tools=["all"],
        blocked_tools=[],
        safety_level=SafetyLevel.LOW,
        proactive_interval=600,
        response_style="relaxed_conversational",
        scene_label="停车",
        scene_icon="🅿️",
    ),
    DrivingScene.EMERGENCY: SceneConfig(
        max_response_words=20,
        allowed_tools=["navigation", "weather"],
        blocked_tools=["play_music", "pause_music", "next_song", "set_volume",
                        "control_window", "set_seat", "set_climate", "lock_doors"],
        safety_level=SafetyLevel.CRITICAL,
        proactive_interval=0,
        response_style="emergency_directive",
        scene_label="紧急",
        scene_icon="🚨",
    ),
}


# ===== 场景配置 → Supervisor Prompt 片段 =====
SCENE_PROMPT_TEMPLATES: dict[DrivingScene, str] = {
    DrivingScene.IDLE: """
## 当前驾驶场景：待机（车辆静止）
- 回复风格：友好详细，可以多解释一点
- 允许所有子Agent工具
- 主动建议间隔：5分钟
""",
    DrivingScene.CITY_DRIVING: """
## 当前驾驶场景：市区行驶（速度 < 60km/h）
- 回复风格：简短可操作，控制在50字以内，聚焦用户需要的动作
- 允许的子Agent：导航、天气、基础多媒体、基础车辆控制
- 禁止的操作：开窗、调座椅（行驶中安全风险）
- 主动建议间隔：1分钟（路况更新）
""",
    DrivingScene.HIGHWAY: """
## 当前驾驶场景：高速行驶（速度 ≥ 60km/h）
- ⚠️ 安全优先！回复风格：极简提醒，控制在30字以内，只说最关键的信息
- 允许的子Agent：仅导航、天气
- 禁止的操作：开窗、调座椅、锁/解锁车门、调空调（高速中安全风险极高）
- 主动建议间隔：2分钟（路况/服务区提醒）
""",
    DrivingScene.PARKED: """
## 当前驾驶场景：停车状态
- 回复风格：轻松对话，可以详细回答，控制在150字以内
- 允许所有子Agent工具
- 主动建议间隔：10分钟
""",
    DrivingScene.EMERGENCY: """
## 当前驾驶场景：紧急状态（故障/事故/报警灯亮）
- ⚠️ 紧急！回复风格：紧急指令，控制在20字以内，只说安全相关指导
- 允许的子Agent：仅导航、天气
- 禁止所有娱乐和舒适类操作
- 主动推送：立即（0间隔）
""",
}


def get_scene_config(scene: DrivingScene) -> SceneConfig:
    """获取场景配置"""
    return SCENE_CONFIGS.get(scene, SCENE_CONFIGS[DrivingScene.IDLE])


def get_scene_prompt(scene: DrivingScene) -> str:
    """获取场景对应的 Supervisor prompt 片段"""
    return SCENE_PROMPT_TEMPLATES.get(scene, SCENE_PROMPT_TEMPLATES[DrivingScene.IDLE])


def get_scene_display(scene: DrivingScene) -> dict:
    """获取前端展示信息"""
    config = get_scene_config(scene)
    return {
        "scene": scene.value,
        "label": config.scene_label,
        "icon": config.scene_icon,
        "safety_level": config.safety_level.value,
        "max_response_words": config.max_response_words,
    }
