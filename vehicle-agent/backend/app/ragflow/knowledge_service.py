"""
RAGFlow 知识库服务
封装知识库检索、文档导入、来源标注格式化
"""
from pathlib import Path

from loguru import logger

from app.config import settings
from app.ragflow.client import ragflow_client


class KnowledgeService:
    """知识库检索与管理服务"""

    def __init__(self) -> None:
        self._dataset_ids: list[str] = []  # 已初始化的知识库 dataset ID 列表

    def init(self) -> None:
        """初始化知识库服务，加载已有 dataset ID"""
        if not ragflow_client.available:
            logger.info("知识库服务: RAGFlow 不可用，跳过初始化")
            return

        # 从持久化状态加载 dataset IDs
        state_key = "dataset_ids"
        cached_ids = ragflow_client.get_state(state_key, "")
        if cached_ids:
            self._dataset_ids = cached_ids.split(",")
            logger.info(f"知识库服务: 已加载 {len(self._dataset_ids)} 个知识库 ID")
        else:
            logger.info("知识库服务: 尚无已初始化的知识库")

    def search(self, query: str, top_k: int = None) -> str:
        """
        搜索知识库，返回带来源标注的结果文本

        Args:
            query: 用户查询
            top_k: 返回结果数量（默认使用配置值）

        Returns:
            格式化的检索结果字符串（含来源标注），空字符串表示无结果
        """
        if not ragflow_client.available or not self._dataset_ids:
            return ""

        top_k = top_k or settings.RAGFLOW_TOP_K

        try:
            results = ragflow_client.retrieve(
                dataset_ids=self._dataset_ids,
                question=query,
                top_k=top_k,
                similarity_threshold=settings.RAGFLOW_SIMILARITY_THRESHOLD,
                vector_similarity_weight=settings.RAGFLOW_VECTOR_SIMILARITY_WEIGHT,
            )
        except Exception as e:
            logger.warning(f"知识库检索失败: {e}")
            return ""

        if not results:
            return ""

        return self.format_with_citations(results)

    def format_with_citations(self, results: list[dict]) -> str:
        """
        将检索结果格式化为带来源标注的文本

        格式:
        查询结果（来自知识库）：
        1. [来源: xxx.pdf | 相关度: 0.85] 内容摘要...
        2. [来源: xxx.md | 相关度: 0.72] 内容摘要...
        """
        lines = ["查询结果（来自知识库）："]
        for i, r in enumerate(results, 1):
            source = r.get("document_name", "未知来源")
            similarity = r.get("similarity", 0)
            content = r.get("content", "").strip()
            # 截取内容前200字避免过长
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{i}. [来源: {source} | 相关度: {similarity:.2f}] {content}")

        return "\n".join(lines)

    def should_search_kb(self, user_message: str) -> bool:
        """
        判断是否需要检索知识库（基于关键词启发式）

        Args:
            user_message: 用户当前消息

        Returns:
            True 表示需要检索知识库
        """
        if not ragflow_client.available or not self._dataset_ids:
            return False

        # 关键词启发式匹配
        keywords = settings.RAGFLOW_KB_KEYWORDS.split(",")
        for kw in keywords:
            kw = kw.strip()
            if kw and kw in user_message:
                return True

        # 额外模式：问句模式（"xxx是什么"、"怎么xxx"、"xxx多少"）
        question_patterns = ["是什么", "怎么", "如何", "多少", "哪里", "哪个", "能不能", "可以吗", "有没有"]
        for pattern in question_patterns:
            if pattern in user_message:
                return True

        return False

    def import_content(self, dataset_id: str, name: str, content: str) -> str:
        """
        内联文本导入到知识库

        Args:
            dataset_id: 知识库 ID
            name: 文档名称
            content: 文档内容

        Returns:
            document_id
        """
        if not ragflow_client.available:
            raise RuntimeError("RAGFlow 服务不可用")

        return ragflow_client.create_document_from_text(dataset_id, name, content)

    def upload_files(self, dataset_id: str, file_paths: list[Path]) -> list[str]:
        """
        上传文件到知识库

        Returns:
            document ID 列表
        """
        if not ragflow_client.available:
            raise RuntimeError("RAGFlow 服务不可用")

        return ragflow_client.upload_documents(dataset_id, file_paths)

    def create_dataset(self, name: str, description: str = "") -> str:
        """
        创建新知识库

        Returns:
            dataset_id
        """
        if not ragflow_client.available:
            raise RuntimeError("RAGFlow 服务不可用")

        ds_id = ragflow_client.create_dataset(name, description)
        self._dataset_ids.append(ds_id)
        # 持久化更新
        ragflow_client.set_state("dataset_ids", ",".join(self._dataset_ids))
        return ds_id

    def list_datasets(self) -> list[dict]:
        """列出所有知识库"""
        if not ragflow_client.available:
            return []
        return ragflow_client.list_datasets()

    @property
    def dataset_ids(self) -> list[str]:
        """当前可用的知识库 dataset ID 列表"""
        return self._dataset_ids


# 全局单例
knowledge_service = KnowledgeService()
