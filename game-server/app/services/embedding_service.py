"""
Embedding 语义匹配服务
使用硅基流动 SiliconFlow API 获取文本向量，计算余弦相似度
"""
import logging
import math
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 缓存
_embedding_cache: dict[str, list[float]] = {}


async def get_embedding(text: str) -> list[float]:
    """获取文本的 Embedding 向量"""
    cached = _embedding_cache.get(text)
    if cached:
        return cached

    api_key = settings.EMBEDDING_API_KEY
    if not api_key or api_key == "your_api_key_here":
        logger.warning("Embedding API Key 未配置，使用简单字符串匹配")
        return []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            settings.EMBEDDING_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": [text],
            },
        )
        if resp.status_code != 200:
            logger.error(f"Embedding API error {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Embedding API 调用失败: {resp.status_code}")

        data = resp.json()
        embedding = data["data"][0]["embedding"]
        _embedding_cache[text] = embedding
        return embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度"""
    if len(a) != len(b):
        raise ValueError(f"向量维度不匹配: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    magnitude = norm_a * norm_b
    if magnitude == 0:
        return 0.0
    return dot / magnitude


def _edit_distance_similarity(a: str, b: str) -> float:
    """简单编辑距离相似度（无 API Key 时使用）"""
    la, lb = a.lower().strip(), b.lower().strip()
    if la == lb:
        return 1.0
    if not la or not lb:
        return 0.0

    matrix = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        matrix[i][0] = i
    for j in range(lb + 1):
        matrix[0][j] = j

    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if la[i - 1] == lb[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )

    max_len = max(len(la), len(lb))
    return 1 - matrix[len(la)][len(lb)] / max_len


async def calculate_similarity(
    guess_text: str,
    answer_text: str,
    answer_embedding: Optional[list[float]] = None,
) -> float:
    """计算猜测与答案的相似度"""
    api_key = settings.EMBEDDING_API_KEY
    if not api_key or api_key == "your_api_key_here":
        return _edit_distance_similarity(guess_text, answer_text)

    try:
        ans_vec = answer_embedding or await get_embedding(answer_text)
        guess_vec = await get_embedding(guess_text)
        return cosine_similarity(guess_vec, ans_vec)
    except Exception as e:
        logger.error(f"计算相似度失败: {e}，回退到字符串匹配")
        return _edit_distance_similarity(guess_text, answer_text)


def is_correct(similarity: float) -> bool:
    """判断是否猜对"""
    return similarity >= settings.SIMILARITY_THRESHOLD


def load_cached_embeddings(words: list[dict]) -> None:
    """从词库数据中加载已缓存的 embedding"""
    count = 0
    for w in words:
        if w.get("embedding"):
            _embedding_cache[w["word"]] = w["embedding"]
            count += 1
    logger.info(f"从词库加载了 {count} 个缓存向量")
