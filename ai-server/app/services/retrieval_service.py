"""
Qdrant 向量数据库服务 — 知识库存储与检索
"""
import logging
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    """获取 Qdrant 客户端单例"""
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=30,
        )
    return _client


def init_qdrant() -> None:
    """初始化 Qdrant 连接（启动时调用）"""
    try:
        client = get_client()
        client.get_collections()
        logger.info(f"Qdrant 连接成功: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    except Exception as e:
        logger.error(f"Qdrant 连接失败: {e}")
        raise


def create_collection(kb_id: str) -> None:
    """创建知识库集合"""
    client = get_client()
    try:
        client.create_collection(
            collection_name=kb_id,
            vectors_config=qmodels.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info(f"Created collection: {kb_id}")
    except UnexpectedResponse:
        logger.warning(f"Collection {kb_id} already exists")


def delete_collection(kb_id: str) -> None:
    """删除知识库集合"""
    client = get_client()
    try:
        client.delete_collection(collection_name=kb_id)
        logger.info(f"Deleted collection: {kb_id}")
    except UnexpectedResponse:
        logger.warning(f"Collection {kb_id} does not exist")


def collection_exists(kb_id: str) -> bool:
    """检查集合是否存在"""
    client = get_client()
    try:
        client.get_collection(collection_name=kb_id)
        return True
    except UnexpectedResponse:
        return False


def list_collections() -> list[str]:
    """列出所有集合"""
    client = get_client()
    collections = client.get_collections().collections
    return [c.name for c in collections]


def get_collection_info(kb_id: str) -> dict:
    """获取集合信息"""
    client = get_client()
    info = client.get_collection(collection_name=kb_id)
    return {
        "points_count": info.points_count or 0,
        "vectors_count": info.vectors_count or 0,
    }


def upsert_documents(
    kb_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    file_id: str,
    filename: str,
    file_type: str,
) -> None:
    """
    将文档块存入 Qdrant

    Args:
        kb_id: 知识库 ID（集合名）
        chunks: 文本块列表
        embeddings: 对应的 embedding 向量列表
        file_id: 文件 ID
        filename: 文件名
        file_type: 文件类型
    """
    client = get_client()

    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "file_id": file_id,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_index": i,
                    "text": chunk,
                },
            )
        )

    # 批量写入（每次 100 条）
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=kb_id, points=batch)

    logger.info(f"Upserted {len(points)} chunks for file {filename} in collection {kb_id}")


def search(
    kb_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    相似度搜索

    Returns:
        匹配的文档块列表，每项包含 text、score、filename 等
    """
    client = get_client()

    results = client.search(
        collection_name=kb_id,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "text": r.payload.get("text", ""),
            "score": r.score,
            "filename": r.payload.get("filename", ""),
            "file_id": r.payload.get("file_id", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
        }
        for r in results
    ]


def delete_file_documents(kb_id: str, file_id: str) -> None:
    """删除知识库中某个文件的所有文档块"""
    client = get_client()

    # 使用 filter 删除指定 file_id 的所有 points
    client.delete(
        collection_name=kb_id,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="file_id",
                        match=qmodels.MatchValue(value=file_id),
                    )
                ]
            )
        ),
    )
    logger.info(f"Deleted all documents for file_id={file_id} in collection {kb_id}")


def get_file_ids_in_collection(kb_id: str) -> list[dict]:
    """获取集合中所有文件的 ID 和统计信息"""
    client = get_client()

    # 滚动查询获取所有 points（取 payload）
    all_points = []
    offset = None

    while True:
        result = client.scroll(
            collection_name=kb_id,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result
        all_points.extend(points)

        if not next_offset:
            break
        offset = next_offset

    # 按 file_id 聚合
    file_stats: dict[str, dict] = {}
    for point in all_points:
        payload = point.payload or {}
        fid = payload.get("file_id", "unknown")
        if fid not in file_stats:
            file_stats[fid] = {
                "file_id": fid,
                "filename": payload.get("filename", ""),
                "file_type": payload.get("file_type", ""),
                "chunk_count": 0,
            }
        file_stats[fid]["chunk_count"] += 1

    return list(file_stats.values())
