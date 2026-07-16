"""
AutoMind Agent 状态定义
继承 CopilotKitState，支持生成式UI渲染与前后端状态同步
"""
from copilotkit import CopilotKitState


class AutoMindState(CopilotKitState):
    """
    车机智能助手的共享状态

    CopilotKitState 已包含:
    - messages: 对话消息列表（带 reducer 自动累加）
    - copilotkit: CopilotKit 前端工具/上下文通道

    扩展字段:
    - user_id: 当前用户标识（用于记忆系统）
    - user_profile: 用户档案（从长期记忆加载）
    - recalled_preferences: 召回的偏好记忆
    - pending_reminders: 待处理提醒
    - current_vehicle_status: 当前车辆状态快照
    - active_agent: 当前激活的子Agent
    - session_id: 当前会话标识（用于跨会话记忆）
    - knowledge_results: 知识库检索结果（含来源标注）
    - shared_memory: 跨会话共享记忆摘要
    - kb_search_triggered: 是否触发了知识库检索
    - current_scene: 当前驾驶场景（idle/city_driving/highway/parked/emergency）
    - scene_config: 当前场景配置（从 scene_config.py 加载）
    - scene_transition_reason: 场景切换原因

    注意：不要在此声明 remaining_steps。create_agent 会在内部自行管理该
    托管通道（managed channel），若在 state_schema 里显式声明，会被
    StateGraph 当作 Input/Output schema 的托管通道而报错：
    "Invalid managed channels detected in InputSchema: remaining_steps"。
    """

    user_id: str = "demo_user_001"
    user_profile: dict = {}
    recalled_preferences: list[str] = []
    pending_reminders: list[dict] = []
    current_vehicle_status: dict = {}
    active_agent: str = ""
    # --- 知识库与跨会话记忆新增字段 ---
    session_id: str = ""
    knowledge_results: list[dict] = []
    shared_memory: list[str] = []
    kb_search_triggered: bool = False
    # --- 驾驶场景状态机新增字段 ---
    current_scene: str = "idle"        # DrivingScene 枚举值（str 形式）
    scene_config: dict = {}            # 当前场景配置（序列化后的 SceneConfig）
    scene_transition_reason: str = ""  # 场景切换原因描述
