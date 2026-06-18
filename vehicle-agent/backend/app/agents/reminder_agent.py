"""
提醒子Agent
负责日程管理、上下文感知提醒
通过记忆模块（SQLite）持久化提醒事项
"""
from datetime import datetime

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.memory.manager import memory_manager
from app.models.llm import create_llm

REMINDER_PROMPT = f"""\
你是 AutoMind 的智能提醒助手 Agent，默认用户ID为 {settings.DEFAULT_VEHICLE_USER_ID}。

你的能力：
- 创建提醒：帮用户设置日程提醒
- 查看提醒：列出待办事项
- 上下文感知：根据天气、路况主动给出建议

工作规则：
1. 创建提醒时，确认提醒时间和内容
2. 时间格式：YYYY-MM-DD HH:MM
3. 结合用户偏好主动建议（如"明天有雨，建议提前10分钟出发"）
4. 语气温暖贴心，体现关怀

你通过内置工具直接操作记忆系统，持久化用户的提醒。"""


@tool
def create_reminder(content: str, remind_at: str) -> dict:
    """
    创建一条提醒事项

    Args:
        content: 提醒内容（如"明天早上9点开会"）
        remind_at: 提醒时间，格式 YYYY-MM-DD HH:MM

    Returns:
        创建结果，含提醒ID
    """
    user_id = settings.DEFAULT_VEHICLE_USER_ID
    reminder_id = memory_manager.add_reminder(user_id, content, remind_at)
    return {"status": "ok", "reminder_id": reminder_id, "content": content, "remind_at": remind_at}


@tool
def list_reminders() -> dict:
    """
    列出当前用户所有待处理提醒

    Returns:
        提醒列表
    """
    user_id = settings.DEFAULT_VEHICLE_USER_ID
    reminders = memory_manager.long_term.get_reminders(user_id, pending_only=True)
    return {"status": "ok", "count": len(reminders), "reminders": reminders}


@tool
def save_user_preference(category: str, value: str) -> dict:
    """
    保存用户偏好到长期记忆系统

    Args:
        category: 偏好类别（如 preferred_temp/home_address/music_genre）
        value: 偏好值（如 "22"/"上海市浦东新区"/"流行音乐"）

    Returns:
        保存结果
    """
    user_id = settings.DEFAULT_VEHICLE_USER_ID
    memory_manager.update_profile(user_id, {category: value})
    return {"status": "ok", "category": category, "value": value}


def create_reminder_agent():
    """创建提醒子Agent，绑定记忆相关工具"""
    return create_react_agent(
        model=create_llm(),
        tools=[create_reminder, list_reminders, save_user_preference],
        name="reminder_agent",
        prompt=REMINDER_PROMPT,
    )
