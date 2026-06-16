"""
PDF 解析服务
使用 pdfplumber（MIT 协议）提取文本和元数据
"""
import logging
from pathlib import Path
from typing import Any

import pdfplumber

logger = logging.getLogger(__name__)


def parse_pdf(file_path: Path) -> dict[str, Any]:
    """
    解析 PDF 文件，提取文本和元数据

    Args:
        file_path: PDF 文件路径

    Returns:
        {
            "pages": 页数,
            "text": 完整文本,
            "metadata": 元数据字典
        }
    """
    logger.info(f"Parsing PDF: {file_path}")

    text_parts: list[str] = []
    metadata: dict[str, str] = {}

    try:
        with pdfplumber.open(str(file_path)) as pdf:
            num_pages = len(pdf.pages)
            metadata["total_pages"] = str(num_pages)

            # 提取元数据
            if pdf.metadata:
                for key, value in pdf.metadata.items():
                    if value:
                        metadata[str(key)] = str(value)

            # 逐页提取文本
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"--- 第 {i + 1} 页 ---\n{page_text}")

                # 提取表格（如果有）
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if table:
                        table_text = "\n".join(
                            " | ".join(str(cell) if cell else "" for cell in row)
                            for row in table
                        )
                        text_parts.append(
                            f"\n[表格 {i + 1}-{table_idx + 1}]\n{table_text}"
                        )

    except Exception as e:
        logger.error(f"PDF parse error: {file_path}, error={e}")
        raise

    full_text = "\n\n".join(text_parts)
    logger.info(f"PDF parsed: pages={num_pages}, text_length={len(full_text)}")

    return {
        "pages": num_pages,
        "text": full_text,
        "metadata": metadata,
    }
