"""
文本分块服务 — 递归字符分割，保持语义完整性
"""
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

# 分割符优先级：段落 > 句子 > 子句 > 单词 > 字符
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ",", " ", ""]


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """
    将文本分割成带重叠的块

    Args:
        text: 原始文本
        chunk_size: 目标块大小（字符数），默认使用配置
        chunk_overlap: 重叠字符数，默认使用配置

    Returns:
        文本块列表
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    # 清理多余空白
    text = re.sub(r"\s+", " ", text).strip()

    chunks = _recursive_split(text, chunk_size, chunk_overlap, _SEPARATORS)

    # 过滤空块
    chunks = [c.strip() for c in chunks if c.strip()]

    logger.info(f"Split text into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks


def _recursive_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    """递归分割文本"""
    if len(text) <= chunk_size:
        return [text]

    # 尝试当前分隔符
    sep = separators[0] if separators else ""
    remaining_seps = separators[1:] if len(separators) > 1 else [""]

    if sep == "":
        # 没有分隔符可用，按字符硬切
        return _hard_split(text, chunk_size, chunk_overlap)

    parts = text.split(sep)

    # 如果分割后只有一部分或每部分都很大，换下一个分隔符
    if len(parts) <= 1:
        return _recursive_split(text, chunk_size, chunk_overlap, remaining_seps)

    # 合并小块到 chunk_size 以内
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 如果单个 part 超过 chunk_size，递归分割
            if len(part) > chunk_size:
                sub_chunks = _recursive_split(part, chunk_size, chunk_overlap, remaining_seps)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    # 添加重叠
    if chunk_overlap > 0 and len(chunks) > 1:
        chunks = _add_overlap(chunks, chunk_overlap)

    return chunks


def _hard_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """按字符硬切分"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    """为相邻块添加重叠"""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
        result.append(prev_tail + " " + chunks[i])
    return result
