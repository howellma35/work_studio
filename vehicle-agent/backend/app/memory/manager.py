"""
统一记忆管理器
合并短期对话记忆、长期用户偏好记忆与 RAGFlow 跨会话记忆，对外提供简洁接口
"""
from loguru import logger

from app.memory.long_term import long_term_memory
from app.memory.short_term import short_term_memory


class MemoryManager:
    """记忆系统统一入口"""

    def __init__(self) -> None:
        self.checkpointer = short_term_memory
        self.long_term = long_term_memory
        self._ragflow_available = False

    def set_ragflow_available(self, available: bool) -> None:
        """标记 RAGFlow 是否可用（由 main.py lifespan 设置）"""
        self._ragflow_available = available

    def get_context(self, user_id: str, query: str) -> dict:
        """
        获取当前对话的完整记忆上下文（本地记忆）

        合并以下信息注入到 Agent state:
        1. 用户长期偏好（向量召回）
        2. 用户结构化档案（SQLite）
        3. 待处理提醒事项

        Args:
            user_id: 用户标识
            query: 当前用户输入（用于语义召回相关偏好）

        Returns:
            包含 preferences / profile / reminders 的上下文字典
        """
        preferences = self.long_term.recall_preferences(user_id, query)
        profile = self.long_term.get_profile(user_id)
        reminders = self.long_term.get_reminders(user_id)

        context = {
            "recalled_preferences": preferences,
            "user_profile": profile,
            "pending_reminders": reminders,
        }
        logger.debug(
            f"记忆上下文加载 | user={user_id} | "
            f"偏好={len(preferences)} 档案keys={len(profile)} 提醒={len(reminders)}"
        )
        return context

    def get_combined_context(self, user_id: str, query: str, session_id: str = "") -> dict:
        """
        获取合并记忆上下文（本地 + RAGFlow 跨会话记忆）

        在 RAGFlow 不可用时降级为 get_context()

        Args:
            user_id: 用户标识
            query: 当前用户输入
            session_id: 当前会话 ID（用于 RAGFlow 记忆关联）

        Returns:
            包含 preferences / profile / reminders / shared_memory 的上下文字典
        """
        # 先获取本地记忆
        context = self.get_context(user_id, query)

        # 如果 RAGFlow 可用，叠加跨会话记忆
        if self._ragflow_available:
            try:
                from app.ragflow.memory_service import memory_service

                if memory_service.available:
                    shared_memory = memory_service.recall(query, top_n=3)
                    context["shared_memory"] = shared_memory
                    logger.debug(
                        f"合并记忆上下文 | user={user_id} | "
                        f"跨会话记忆={len(shared_memory)}"
                    )
            except Exception as e:
                logger.warning(f"RAGFlow 记忆合并失败，降级为本地模式: {e}")

        return context

    def update_profile(self, user_id: str, updates: dict) -> None:
        """更新用户档案（同步写入 SQLite + ChromaDB）"""
        self.long_term.update_profile(user_id, updates)
        logger.info(f"用户档案已更新 | user={user_id} | keys={list(updates.keys())}")

    def add_reminder(self, user_id: str, content: str, remind_at: str) -> str:
        """添加提醒"""
        reminder_id = self.long_term.add_reminder(user_id, content, remind_at)
        logger.info(f"提醒已创建 | user={user_id} | when={remind_at} | content={content}")
        return reminder_id


# 全局单例
memory_manager = MemoryManager()
