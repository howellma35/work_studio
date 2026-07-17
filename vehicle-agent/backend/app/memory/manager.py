"""
统一记忆管理器
合并短期对话记忆与长期用户偏好记忆，对外提供简洁接口
"""
from loguru import logger

from app.memory.long_term import long_term_memory


class MemoryManager:
    """记忆系统统一入口"""

    def __init__(self) -> None:
        # 短期对话记忆（checkpointer）由 supervisor 直接持有 AsyncSqliteSaver，
        # 不在此暴露；本入口仅负责长期记忆（偏好/档案/提醒）的召回与写入。
        self.long_term = long_term_memory

    def get_context(self, user_id: str, query: str) -> dict:
        """
        获取当前对话的完整记忆上下文

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
