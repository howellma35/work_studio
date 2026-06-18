"""
短期对话记忆模块
基于 LangGraph checkpointer 实现多轮对话状态持久化
- 开发环境: MemorySaver（内存）
- 生产环境: 可切换 PostgresSaver / RedisSaver
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

from app.config import settings


def create_checkpointer() -> BaseCheckpointSaver:
    """
    创建 LangGraph checkpointer

    通过 thread_id 区分不同会话，实现多轮对话上下文保持。
    每次对话会自动保存到 checkpoint，支持状态时间旅行调试。

    生产环境可替换为:
        from langgraph.checkpoint.postgres import PostgresSaver
        from langgraph.checkpoint.redis import RedisSaver
    """
    logger.info("短期记忆 checkpointer 已创建 (MemorySaver)")
    return MemorySaver()


# 全局 checkpointer 单例
short_term_memory = create_checkpointer()
