"""
RAGFlow 跨会话记忆服务
使用 RAGFlow Memory API 实现跨会话记忆存储和检索
"""
from loguru import logger

from app.config import settings
from app.ragflow.client import ragflow_client


class MemoryService:
    """跨会话记忆服务"""

    def __init__(self) -> None:
        self._memory_id: str = ""  # 默认记忆空间 ID

    def init(self) -> None:
        """
        初始化记忆服务

        尝试从缓存加载 memory_id，若无则创建新记忆空间
        """
        if not ragflow_client.available:
            logger.info("记忆服务: RAGFlow 不可用，使用本地记忆降级")
            return

        # 从持久化状态加载
        cached_id = ragflow_client.get_state("memory_id", "")
        if cached_id:
            self._memory_id = cached_id
            logger.info(f"记忆服务: 已加载记忆空间 ID={cached_id}")
            return

        # 创建新记忆空间
        if settings.RAGFLOW_LLM_ID and settings.RAGFLOW_EMBD_ID:
            try:
                mem_id = ragflow_client.create_memory(
                    name="automind_shared_memory",
                    memory_type=settings.ragflow_memory_types_list,
                    embd_id=settings.RAGFLOW_EMBD_ID,
                    llm_id=settings.RAGFLOW_LLM_ID,
                )
                self._memory_id = mem_id
                ragflow_client.set_state("memory_id", mem_id)
                logger.info(f"记忆服务: 新记忆空间已创建 ID={mem_id}")
            except Exception as e:
                logger.warning(f"记忆服务: 创建记忆空间失败: {e}")
        else:
            logger.warning(
                "记忆服务: RAGFLOW_LLM_ID 和 RAGFLOW_EMBD_ID 未配置，"
                "无法创建记忆空间。请在 RAGFlow Web UI 配置模型后填入。"
            )

    def save_conversation(
        self,
        session_id: str,
        user_input: str,
        agent_response: str,
        user_id: str = "",
    ) -> None:
        """
        保存对话到记忆空间（异步调用，不阻塞对话）

        Args:
            session_id: 会话标识
            user_input: 用户消息
            agent_response: Agent 回复
            user_id: 用户标识
        """
        if not self._memory_id or not ragflow_client.available:
            return

        try:
            ragflow_client.add_message(
                memory_id=self._memory_id,
                agent_id="automind",
                session_id=session_id,
                user_input=user_input,
                agent_response=agent_response,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"记忆保存失败（不影响对话）: {e}")

    def recall(self, query: str, top_n: int = 5) -> list[str]:
        """
        搜索跨会话记忆

        Args:
            query: 查询文本
            top_n: 返回数量

        Returns:
            相关记忆摘要文本列表
        """
        if not self._memory_id or not ragflow_client.available:
            return []

        try:
            results = ragflow_client.search_message(
                query=query,
                memory_id=[self._memory_id],
                agent_id="automind",
                similarity_threshold=0.2,
                keywords_similarity_weight=0.7,
                top_n=top_n,
            )
            memories = []
            for r in results:
                # search_message 返回的每条记忆有 content/summary 等字段
                content = r.get("content", "") or r.get("summary", "") or str(r)
                if content and content.strip():
                    memories.append(content.strip())

            logger.debug(f"跨会话记忆召回: query={query[:50]}, 命中 {len(memories)} 条")
            return memories
        except Exception as e:
            logger.warning(f"记忆召回失败: {e}")
            return []

    def get_recent(self, limit: int = 10) -> list[str]:
        """
        获取最近的记忆消息

        Returns:
            最近记忆摘要列表
        """
        if not self._memory_id or not ragflow_client.available:
            return []

        try:
            results = ragflow_client.get_recent_messages(
                memory_id=[self._memory_id],
                agent_id="automind",
                limit=limit,
            )
            memories = []
            for r in results:
                content = r.get("content", "") or r.get("summary", "") or str(r)
                if content and content.strip():
                    memories.append(content.strip())
            return memories
        except Exception as e:
            logger.warning(f"获取最近记忆失败: {e}")
            return []

    @property
    def available(self) -> bool:
        """记忆服务是否可用"""
        return bool(self._memory_id) and ragflow_client.available

    @property
    def memory_id(self) -> str:
        """当前记忆空间 ID"""
        return self._memory_id


# 全局单例
memory_service = MemoryService()
