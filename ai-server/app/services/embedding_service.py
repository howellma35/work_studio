"""
Embedding 服务 — 调用 SiliconFlow API 生成文本向量
"""
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def get_embedding(text: str) -> list[float]:
    """获取单个文本的 embedding 向量"""
    if not settings.EMBEDDING_API_KEY:
        raise ValueError("EMBEDDING_API_KEY 未配置，无法生成 embedding")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.EMBEDDING_API_URL,
            headers={
                "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": [text],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """批量获取文本 embedding 向量"""
    if not texts:
        return []

    if not settings.EMBEDDING_API_KEY:
        raise ValueError("EMBEDDING_API_KEY 未配置，无法生成 embedding")

    # SiliconFlow API 支持批量输入，但单次最多约 25 条
    batch_size = 25
    all_embeddings = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.post(
                settings.EMBEDDING_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.EMBEDDING_MODEL,
                    "input": batch,
                },
            )
            response.raise_for_status()
            data = response.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

    logger.info(f"Generated {len(all_embeddings)} embeddings for {len(texts)} texts")
    return all_embeddings
