"""
RAGFlow SDK 客户端封装
统一管理 RAGFlow API 连接，提供健康检查、优雅降级
"""
import json
from pathlib import Path

from loguru import logger

from app.config import settings

# 持久化 RAGFlow 资源 ID（dataset/memory/chat）的本地缓存文件
_RAGFLOW_STATE_FILE = Path("./data/ragflow_state.json")


class RAGFlowClient:
    """RAGFlow SDK 客户端单例，封装所有 API 调用"""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        self._state: dict = {}

    def _load_state(self) -> dict:
        """从本地文件加载 RAGFlow 资源 ID 缓存"""
        if _RAGFLOW_STATE_FILE.exists():
            try:
                return json.loads(_RAGFLOW_STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_state(self, state: dict) -> None:
        """持久化 RAGFlow 资源 ID 缓存"""
        _RAGFLOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RAGFLOW_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def get_state(self, key: str, default: str = "") -> str:
        """获取缓存的状态值"""
        return self._state.get(key, default)

    def set_state(self, key: str, value: str) -> None:
        """设置并持久化状态值"""
        self._state[key] = value
        self._save_state(self._state)

    def init(self) -> bool:
        """
        初始化 RAGFlow SDK 连接

        Returns:
            True if connection established, False if unavailable
        """
        if not settings.ragflow_enabled:
            logger.info("RAGFlow 模块已禁用 (RAGFLOW_ENABLED=false 或无 API Key)")
            return False

        try:
            from ragflow_sdk import RAGFlow
            base_url = f"{settings.RAGFLOW_BASE_URL}/api/v1"
            self._client = RAGFlow(api_key=settings.RAGFLOW_API_KEY, base_url=base_url)
            # 健康检查：尝试列出 datasets
            datasets = self._client.list_datasets(page=1, page_size=1)
            self._available = True
            self._state = self._load_state()
            logger.info(f"RAGFlow 连接成功 | base_url={base_url} | datasets={len(datasets)}")
            return True
        except Exception as e:
            logger.warning(f"RAGFlow 连接失败，知识库功能降级为本地模式: {e}")
            self._available = False
            self._client = None
            return False

    @property
    def available(self) -> bool:
        """RAGFlow 服务是否可用"""
        return self._available and self._client is not None

    @property
    def client(self):
        """获取底层 RAGFlow SDK 客户端"""
        if not self.available:
            raise RuntimeError("RAGFlow 服务不可用")
        return self._client

    # ===== Dataset (知识库) 操作 =====

    def create_dataset(self, name: str, description: str = "") -> str:
        """
        创建知识库（RAGFlow Dataset）

        Returns:
            dataset_id
        """
        ds = self.client.create_dataset(name=name, description=description)
        logger.info(f"RAGFlow 知识库已创建: name={name}, id={ds.id}")
        return ds.id

    def list_datasets(self, page: int = 1, page_size: int = 30) -> list[dict]:
        """
        列出所有知识库

        Returns:
            [{"id": ..., "name": ..., "document_count": ..., "chunk_count": ...}]
        """
        datasets = self.client.list_datasets(page=page, page_size=page_size)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "document_count": ds.document_count,
                "chunk_count": ds.chunk_count,
            }
            for ds in datasets
        ]

    def upload_documents(self, dataset_id: str, file_paths: list[Path]) -> list[str]:
        """
        上传文件到知识库

        Args:
            dataset_id: 知识库 ID
            file_paths: 本地文件路径列表

        Returns:
            document ID 列表
        """
        # 先获取 DataSet 对象
        datasets = self.client.list_datasets(id=dataset_id)
        if not datasets:
            raise ValueError(f"Dataset {dataset_id} 不存在")
        ds = datasets[0]

        document_list = []
        for fp in file_paths:
            with open(fp, "rb") as f:
                document_list.append({
                    "display_name": fp.name,
                    "blob": f.read(),
                })

        docs = ds.upload_documents(document_list)
        logger.info(f"RAGFlow 文件已上传: dataset={dataset_id}, docs={len(docs)}")
        return [d.id for d in docs]

    def create_document_from_text(self, dataset_id: str, name: str, content: str) -> str:
        """
        从文本内容直接创建文档（无需上传文件）

        Args:
            dataset_id: 知识库 ID
            name: 文档名称
            content: 文档内容

        Returns:
            document_id
        """
        datasets = self.client.list_datasets(id=dataset_id)
        if not datasets:
            raise ValueError(f"Dataset {dataset_id} 不存在")
        ds = datasets[0]

        docs = ds.create_documents([{"name": name, "content": content}])

        if docs and len(docs) > 0:
            logger.info(f"RAGFlow 内联文档已创建: dataset={dataset_id}, name={name}, id={docs[0].id}")
            return docs[0].id
        raise Exception("RAGFlow 文档创建返回空结果")

    def retrieve(
        self,
        dataset_ids: list[str],
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.6,
    ) -> list[dict]:
        """
        检索知识库（RAGFlow 混合检索：关键词 + 向量）

        Args:
            dataset_ids: 知识库 ID 列表
            question: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 最低相似度阈值
            vector_similarity_weight: 向量检索权重 (关键词权重 = 1 - 此值)

        Returns:
            [{"content": ..., "document_name": ..., "similarity": ..., "dataset_id": ...}]
        """
        chunks = self.client.retrieve(
            dataset_ids=dataset_ids,
            question=question,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            vector_similarity_weight=vector_similarity_weight,
        )

        results = []
        for chunk in chunks:
            results.append({
                "content": chunk.content,
                "document_name": chunk.document_name,
                "similarity": chunk.similarity,
                "dataset_id": chunk.dataset_id,
                "chunk_id": chunk.id,
            })

        logger.debug(f"RAGFlow 检索: question={question[:50]}, 命中 {len(results)} 条")
        return results

    # ===== Memory (跨会话记忆) 操作 =====

    def create_memory(self, name: str, memory_type: list[str], embd_id: str, llm_id: str) -> str:
        """
        创建记忆空间

        Args:
            name: 记忆名称
            memory_type: 记忆类型列表 ["semantic", "episodic", "procedural"]
            embd_id: RAGFlow tenant 内的 Embedding model ID
            llm_id: RAGFlow tenant 内的 LLM model ID

        Returns:
            memory_id
        """
        mem = self.client.create_memory(
            name=name,
            memory_type=memory_type,
            embd_id=embd_id,
            llm_id=llm_id,
        )
        logger.info(f"RAGFlow 记忆已创建: name={name}, id={mem.id}, types={memory_type}")
        return mem.id

    def add_message(
        self,
        memory_id: str,
        agent_id: str,
        session_id: str,
        user_input: str,
        agent_response: str,
        user_id: str = "",
    ) -> None:
        """
        保存对话到记忆空间

        Args:
            memory_id: 记忆 ID
            agent_id: Agent 标识 (如 "automind")
            session_id: 会话标识
            user_input: 用户消息
            agent_response: Agent 回复
            user_id: 用户标识
        """
        self.client.add_message(
            memory_id=[memory_id],
            agent_id=agent_id,
            session_id=session_id,
            user_input=user_input,
            agent_response=agent_response,
            user_id=user_id,
        )
        logger.debug(f"RAGFlow 记忆消息已保存: session={session_id}")

    def search_message(
        self,
        query: str,
        memory_id: list[str],
        agent_id: str = None,
        session_id: str = None,
        similarity_threshold: float = 0.2,
        keywords_similarity_weight: float = 0.7,
        top_n: int = 10,
    ) -> list[dict]:
        """
        搜索记忆（跨会话）

        Args:
            query: 查询文本
            memory_id: 记忆 ID 列表
            agent_id: Agent 过滤
            session_id: 会话过滤
            similarity_threshold: 最低相似度
            keywords_similarity_weight: 关键词权重
            top_n: 返回数量

        Returns:
            记忆搜索结果列表
        """
        results = self.client.search_message(
            query=query,
            memory_id=memory_id,
            agent_id=agent_id,
            session_id=session_id,
            similarity_threshold=similarity_threshold,
            keywords_similarity_weight=keywords_similarity_weight,
            top_n=top_n,
        )
        logger.debug(f"RAGFlow 记忆搜索: query={query[:50]}, 命中 {len(results)} 条")
        return results

    def get_recent_messages(
        self,
        memory_id: list[str],
        agent_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """获取最近记忆消息"""
        return self.client.get_recent_messages(
            memory_id=memory_id,
            agent_id=agent_id,
            session_id=session_id,
            limit=limit,
        )


# 全局单例
ragflow_client = RAGFlowClient()
