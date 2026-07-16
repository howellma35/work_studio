"""
动态工具注入中间件 — 根据场景+角色动态调整 LLM 可见的工具集

设计理念:
- 不是在 prompt 里写"不要调用某某工具"
- 而是**从工具列表中移除**——LLM 看不到就不会调用
- 场景注入: 紧急态注入 emergency_call 工具（正常时不暴露）
- 角色过滤: 乘客看不到锁车工具

集成方式:
- 在 supervisor.py 的 build_supervisor_graph 中，
  根据 current_scene 动态过滤 subagent_tools

当前架构是 create_agent + CopilotKitMiddleware，
动态工具注入在 dynamic_prompt（_build_prompt）中通过 scene_config.blocked_tools
注入安全规则实现。本文件提供更细粒度的工具过滤逻辑，
为未来升级到 AgentMiddleware.wrap_model_call 模式做准备。
"""
from loguru import logger

from app.graph.scene_config import DrivingScene


# ===== 场景 → 工具过滤/注入规则 =====
SCENE_TOOL_RULES = {
    DrivingScene.IDLE: {
        "remove": [],
        "add": [],
    },
    DrivingScene.CITY_DRIVING: {
        "remove": ["control_window", "set_seat"],
        "add": [],
    },
    DrivingScene.HIGHWAY: {
        "remove": ["control_window", "set_seat", "lock_doors", "set_climate"],
        "add": ["search_service_area", "get_highway_traffic"],
    },
    DrivingScene.PARKED: {
        "remove": [],
        "add": ["find_parking", "estimate_cost", "lock_doors_confirm"],
    },
    DrivingScene.EMERGENCY: {
        "remove": ["play_music", "pause_music", "next_song", "set_volume",
                    "control_window", "set_seat", "set_climate", "lock_doors"],
        "add": ["emergency_call", "find_hospital", "find_gas_station"],
    },
}

# ===== 角色 → 工具过滤规则 =====
ROLE_TOOL_RULES = {
    "driver": {
        "remove": [],
        "add": [],
    },
    "passenger": {
        "remove": ["lock_doors"],
        "add": ["play_music"],
    },
    "admin": {
        "remove": [],
        "add": ["lock_doors_confirm", "system_reset"],
    },
}


def filter_tools_by_scene(
    tool_names: list[str],
    scene: DrivingScene,
) -> dict:
    """根据场景过滤/注入工具

    Args:
        tool_names: 当前可用工具名称列表
        scene: 当前驾驶场景

    Returns:
        {
            "visible_tools": 过滤后的可见工具名称列表,
            "removed": 被移除的工具名称列表,
            "added": 被注入的新工具名称列表,
        }
    """
    rules = SCENE_TOOL_RULES.get(scene, {"remove": [], "add": []})
    removed = [t for t in rules["remove"] if t in tool_names]
    added = [t for t in rules["add"] if t not in tool_names]

    visible = [t for t in tool_names if t not in rules["remove"]]
    for t in rules["add"]:
        if t not in visible:
            visible.append(t)

    if removed or added:
        logger.info(
            f"[动态工具注入] scene={scene.value} "
            f"removed={removed} added={added} "
            f"visible={len(visible)}/{len(tool_names)}"
        )

    return {
        "visible_tools": visible,
        "removed": removed,
        "added": added,
    }


def filter_tools_by_role(
    tool_names: list[str],
    role: str = "driver",
) -> dict:
    """根据用户角色过滤工具

    Args:
        tool_names: 当前可见工具名称列表（已经过场景过滤）
        role: 用户角色（driver/passenger/admin）

    Returns:
        同 filter_tools_by_scene 返回格式
    """
    rules = ROLE_TOOL_RULES.get(role, {"remove": [], "add": []})
    removed = [t for t in rules["remove"] if t in tool_names]
    added = [t for t in rules["add"] if t not in tool_names]

    visible = [t for t in tool_names if t not in rules["remove"]]
    for t in rules["add"]:
        if t not in visible:
            visible.append(t)

    return {
        "visible_tools": visible,
        "removed": removed,
        "added": added,
    }


def get_dynamic_tools_description(scene: DrivingScene, role: str = "driver") -> str:
    """生成动态工具可见性描述（注入到 Supervisor prompt）

    让 LLM 知道当前场景下哪些工具可见/不可见，
    以及被注入的新工具的用途说明。
    """
    rules = SCENE_TOOL_RULES.get(scene, {"remove": [], "add": []})
    role_rules = ROLE_TOOL_RULES.get(role, {"remove": [], "add": []})

    all_removed = set(rules["remove"]) | set(role_rules["remove"])
    all_added = set(rules["add"]) | set(role_rules["add"])

    if not all_removed and not all_added:
        return ""

    lines = ["## 动态工具可见性"]

    if all_removed:
        lines.append(f"- 当前场景下以下工具已从可用列表中移除（你无法调用它们）:")
        for t in all_removed:
            tool_display = {
                "control_window": "开窗/关窗",
                "set_seat": "调座椅",
                "lock_doors": "锁车/解锁",
                "set_climate": "调空调",
                "play_music": "播放音乐",
                "pause_music": "暂停音乐",
                "next_song": "切歌",
                "set_volume": "调音量",
            }.get(t, t)
            lines.append(f"  - {tool_display}")

    if all_added:
        lines.append(f"- 当前场景下新增以下专用工具:")
        for t in all_added:
            tool_desc = {
                "search_service_area": "搜索高速服务区",
                "get_highway_traffic": "高速实时路况",
                "find_parking": "搜索停车场",
                "estimate_cost": "预估停车成本",
                "lock_doors_confirm": "锁车确认（需二次确认）",
                "emergency_call": "紧急呼叫",
                "find_hospital": "搜索附近医院",
                "find_gas_station": "搜索附近加油站",
                "system_reset": "系统重置",
            }.get(t, t)
            lines.append(f"  - {tool_desc} ({t})")

    return "\n".join(lines) + "\n"
