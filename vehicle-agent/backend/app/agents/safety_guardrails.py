"""
车辆操作安全护栏 — 三层风险评估

架构适配说明:
当前 AutoMind 使用 create_agent + CopilotKitMiddleware 架构，
没有 LangChain 标准的 AgentMiddleware.wrap_model_call 钩子。
因此安全护栏的实现在 dynamic_prompt 中间件中完成：
1. 从 state 获取 current_scene + scene_config
2. 根据场景的 blocked_tools 注入安全规则到 supervisor prompt
3. 根据 RISK_MATRIX 标注各操作的风险等级
4. HIGH 级操作要求 LLM 先调用 confirm_dangerous_operation 前端工具

三层风险评估:
- 规则层: 风险矩阵（静态操作→风险等级映射）
- 场景层: 场景动态覆盖（高速态下开窗→BLOCKED）
- 语义层: 参数级细粒度（"全窗打开"比"单窗半开"风险更高）

风险等级:
- SAFE (0): 只读查询，无需确认
- LOW (1): 舒适调节，口头提示即可
- MEDIUM (2): 有安全影响，需确认意图
- HIGH (3): 可能危险，必须前端二次确认
- BLOCKED (4): 场景下禁止，直接拒绝
"""
from enum import IntEnum
from loguru import logger

from app.graph.scene_config import DrivingScene


class RiskLevel(IntEnum):
    """操作风险等级"""
    SAFE = 0       # 只读查询，无需确认
    LOW = 1        # 舒适调节，口头提示即可
    MEDIUM = 2     # 有安全影响，需确认意图
    HIGH = 3       # 可能危险，必须前端二次确认
    BLOCKED = 4    # 场景下禁止，直接拒绝


# ===== 规则层：操作 → 风险等级映射 =====
RISK_MATRIX = {
    "get_vehicle_status": RiskLevel.SAFE,
    "set_volume": RiskLevel.SAFE,
    "play_music": RiskLevel.SAFE,
    "pause_music": RiskLevel.SAFE,
    "next_song": RiskLevel.SAFE,
    "get_playlist": RiskLevel.SAFE,
    "get_weather": RiskLevel.SAFE,
    "get_forecast": RiskLevel.SAFE,
    "plan_route": RiskLevel.SAFE,
    "search_poi": RiskLevel.SAFE,
    "get_traffic_info": RiskLevel.SAFE,
    "set_climate": RiskLevel.LOW,
    "set_seat": RiskLevel.LOW,
    "control_window": RiskLevel.MEDIUM,
    "lock_doors": RiskLevel.HIGH,       # 解锁车门需确认
    "create_reminder": RiskLevel.SAFE,
    "list_reminders": RiskLevel.SAFE,
    "save_user_preference": RiskLevel.SAFE,
    "search_knowledge": RiskLevel.SAFE,
}

# ===== 场景层：场景 × 操作 → 风险覆盖 =====
SCENE_RISK_OVERRIDE = {
    DrivingScene.HIGHWAY: {
        "control_window": RiskLevel.BLOCKED,
        "set_seat": RiskLevel.BLOCKED,
        "lock_doors": RiskLevel.BLOCKED,         # 高速禁止解锁
        "set_climate": RiskLevel.BLOCKED,         # 高速禁止调空调（干扰驾驶）
    },
    DrivingScene.CITY_DRIVING: {
        "control_window": RiskLevel.MEDIUM,       # 城区开窗中等风险
        "set_seat": RiskLevel.BLOCKED,            # 行驶中调座椅禁止
    },
    DrivingScene.EMERGENCY: {
        "play_music": RiskLevel.BLOCKED,
        "pause_music": RiskLevel.BLOCKED,
        "next_song": RiskLevel.BLOCKED,
        "set_volume": RiskLevel.BLOCKED,
        "control_window": RiskLevel.BLOCKED,
        "set_seat": RiskLevel.BLOCKED,
        "set_climate": RiskLevel.BLOCKED,
        "lock_doors": RiskLevel.BLOCKED,
    },
}

# ===== 语义层：参数级风险评估规则 =====
# 当操作参数包含以下特征时，风险等级升级
PARAM_RISK_RULES = {
    "control_window": {
        # "全窗打开" 比单窗风险高
        "position_all_open": RiskLevel.HIGH,
        # 单窗半开是最低风险
        "position_single_half": RiskLevel.LOW,
    },
    "lock_doors": {
        # 解锁比锁定风险高
        "action_unlock": RiskLevel.HIGH,
        "action_lock": RiskLevel.SAFE,
    },
}


def evaluate_risk(tool_name: str, args: dict = {}, scene: DrivingScene = DrivingScene.IDLE) -> RiskLevel:
    """三层风险评估

    1. 规则层: 查 RISK_MATRIX 获取基础风险等级
    2. 场景层: 查 SCENE_RISK_OVERRIDE 获取场景覆盖
    3. 语义层: 查 PARAM_RISK_RULES 获取参数级评估

    Returns:
        最终风险等级
    """
    # 1. 规则层：基础风险
    base_risk = RISK_MATRIX.get(tool_name, RiskLevel.MEDIUM)

    # 2. 场景层：场景覆盖（优先级高于规则层）
    scene_overrides = SCENE_RISK_OVERRIDE.get(scene, {})
    if tool_name in scene_overrides:
        return scene_overrides[tool_name]

    # 3. 语义层：参数级评估
    param_rules = PARAM_RISK_RULES.get(tool_name, {})
    # 检查是否匹配参数特征
    if tool_name == "control_window":
        position = args.get("position", "")
        action = args.get("action", "")
        if position == "all" and action == "open":
            return RiskLevel.HIGH
        if action == "half":
            return RiskLevel.LOW

    if tool_name == "lock_doors":
        action = args.get("action", "lock")
        if action == "unlock":
            return RiskLevel.HIGH
        if action == "lock":
            return RiskLevel.SAFE

    return base_risk


def generate_safety_prompt(scene: DrivingScene, blocked_tools: list[str]) -> str:
    """基于场景和风险矩阵生成安全护栏 prompt 片段

    注入到 supervisor 的 dynamic_prompt 中，让 LLM 知道：
    1. 哪些操作在当前场景下被禁止（BLOCKED）
    2. 哪些操作需要前端二次确认（HIGH）
    3. 哪些操作需要口头提示（MEDIUM/LOW）
    """
    if not blocked_tools and scene == DrivingScene.IDLE or scene == DrivingScene.PARKED:
        # 安全等级低时，不注入冗长的安全规则
        return "## 安全规则\n- 涉及车辆控制操作时确认无误后执行\n"

    lines = ["## 安全规则（重要，必须严格遵守）"]

    # BLOCKED 级操作
    if blocked_tools:
        lines.append(f"- ⛔ **禁止执行**: 以下操作在当前场景下被禁止，用户请求时必须拒绝并说明安全原因:")
        for tool in blocked_tools:
            tool_display = {
                "control_window": "开窗/关窗",
                "set_seat": "调座椅",
                "lock_doors": "锁车/解锁",
                "set_climate": "调空调",
                "play_music": "播放音乐",
                "pause_music": "暂停音乐",
                "next_song": "切歌",
                "set_volume": "调音量",
            }.get(tool, tool)
            lines.append(f"  - {tool_display} ({tool})")
        lines.append(f"  → 拒绝时回复格式：「⚠️ 当前场景下无法执行「XX」，原因：安全风险较高」")

    # HIGH 级操作（需前端二次确认）
    high_tools = []
    for tool_name, risk in RISK_MATRIX.items():
        if risk == RiskLevel.HIGH and tool_name not in blocked_tools:
            # 检查场景覆盖是否也升级为 HIGH 或 BLOCKED
            scene_override = SCENE_RISK_OVERRIDE.get(scene, {}).get(tool_name)
            if scene_override == RiskLevel.BLOCKED:
                continue  # 已经在 BLOCKED 列表了
            if scene_override is None or scene_override >= RiskLevel.HIGH:
                tool_display = {
                    "lock_doors": "锁车/解锁车门",
                }.get(tool_name, tool_name)
                high_tools.append(tool_display)

    if high_tools:
        lines.append(f"- 🔒 **需要确认**: 以下操作需要调用 confirm_dangerous_operation 前端工具让用户二次确认:")
        for t in high_tools:
            lines.append(f"  - {t}")

    # MEDIUM 级操作（口头提示）
    medium_tools = []
    for tool_name, risk in RISK_MATRIX.items():
        if risk == RiskLevel.MEDIUM and tool_name not in blocked_tools:
            scene_override = SCENE_RISK_OVERRIDE.get(scene, {}).get(tool_name)
            if scene_override is None or scene_override == RiskLevel.MEDIUM:
                tool_display = {
                    "control_window": "开窗/关窗",
                }.get(tool_name, tool_name)
                medium_tools.append(tool_display)

    if medium_tools:
        lines.append(f"- ⚡ **口头提示**: 执行以下操作前先口头告知用户:")
        for t in medium_tools:
            lines.append(f"  - {t} → 回复如「即将打开车窗，请注意安全」")

    lines.append("")
    return "\n".join(lines)
