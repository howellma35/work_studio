"""
AutoMind Agent 状态定义
继承 CopilotKitState，支持生成式UI渲染与前后端状态同步
"""
from typing import Annotated

from copilotkit import CopilotKitState
from langgraph.graph.message import add_messages


class AutoMindState(CopilotKitState):
    """
    车机智能助手的共享状态

    CopilotKitState 已包含:
    - messages: 对话消息列表（带 reducer 自动累加）
    - copilotkit_messages: CopilotKit UI 消息

    扩展字段:
    - user_id: 当前用户标识（用于记忆系统）
    - user_profile: 用户档案（从长期记忆加载）
    - recalled_preferences: 召回的偏好记忆
    - pending_reminders: 待处理提醒
    - current_vehicle_status: 当前车辆状态快照
    - active_agent: 当前激活的子Agent
    """

    user_id: str
    user_profile: dict
    recalled_preferences: list[str]
    pending_reminders: list[dict]
    current_vehicle_status: dict
    active_agent: str
