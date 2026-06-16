"""
PDF 解析路由
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.pdf_service import parse_pdf

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/parse")
async def upload_and_parse(file: UploadFile = File(...)):
    """
    上传并解析 PDF 文件
    返回提取的文本和元数据
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 格式文件")

    logger.info(f"PDF parse request: {file.filename}, size={file.size}")

    try:
        content = await file.read()

        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = parse_pdf(tmp_path)
            logger.info(f"PDF parsed: {file.filename}, pages={result['pages']}")
            return {
                "fileName": file.filename,
                "pages": result["pages"],
                "text": result["text"],
                "metadata": result["metadata"],
            }
        finally:
            # 清理临时文件
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {str(e)}")
