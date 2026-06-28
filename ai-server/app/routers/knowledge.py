"""
知识库管理路由 — CRUD + 文件上传
"""
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseInfo,
    KnowledgeBaseDetail,
    FileInfo,
)
from app.services import (
    embedding_service,
    chunking_service,
    file_parser_service,
    retrieval_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=KnowledgeBaseInfo)
async def create_knowledge_base(req: KnowledgeBaseCreate):
    """创建知识库"""
    kb_id = f"kb_{uuid.uuid4().hex[:12]}"

    try:
        retrieval_service.create_collection(kb_id)
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise HTTPException(status_code=500, detail=f"创建知识库失败: {str(e)}")

    logger.info(f"Created knowledge base: {kb_id} ({req.name})")

    return KnowledgeBaseInfo(
        id=kb_id,
        name=req.name,
        description=req.description,
        file_count=0,
        chunk_count=0,
        created_at=datetime.now().isoformat(),
    )


@router.get("/", response_model=list[KnowledgeBaseInfo])
async def list_knowledge_bases():
    """列出所有知识库"""
    try:
        collection_names = retrieval_service.list_collections()
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=f"获取知识库列表失败: {str(e)}")

    results = []
    for name in collection_names:
        if not name.startswith("kb_"):
            continue
        try:
            info = retrieval_service.get_collection_info(name)
            files = retrieval_service.get_file_ids_in_collection(name)
            results.append(
                KnowledgeBaseInfo(
                    id=name,
                    name=name,
                    description="",
                    file_count=len(files),
                    chunk_count=info["points_count"],
                    created_at="",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to get info for collection {name}: {e}")

    return results


@router.get("/{kb_id}", response_model=KnowledgeBaseDetail)
async def get_knowledge_base(kb_id: str):
    """获取知识库详情"""
    if not retrieval_service.collection_exists(kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        info = retrieval_service.get_collection_info(kb_id)
        files = retrieval_service.get_file_ids_in_collection(kb_id)

        file_infos = [
            FileInfo(
                file_id=f["file_id"],
                filename=f["filename"],
                file_type=f["file_type"],
                size_bytes=0,
                chunk_count=f["chunk_count"],
                uploaded_at="",
            )
            for f in files
        ]

        return KnowledgeBaseDetail(
            id=kb_id,
            name=kb_id,
            description="",
            files=file_infos,
            chunk_count=info["points_count"],
            created_at="",
        )
    except Exception as e:
        logger.error(f"Failed to get knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取知识库详情失败: {str(e)}")


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除知识库"""
    if not retrieval_service.collection_exists(kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        retrieval_service.delete_collection(kb_id)
        logger.info(f"Deleted knowledge base: {kb_id}")
        return {"message": f"知识库 {kb_id} 已删除"}
    except Exception as e:
        logger.error(f"Failed to delete knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"删除知识库失败: {str(e)}")


@router.post("/{kb_id}/files")
async def upload_file(kb_id: str, file: UploadFile = File(...)):
    """
    上传文件到知识库
    支持格式: PDF, DOCX, TXT, MD, CSV, HTML
    流程: 解析 → 分块 → 嵌入 → 存入 Qdrant
    """
    if not retrieval_service.collection_exists(kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 获取文件扩展名
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    supported_types = {"pdf", "docx", "txt", "md", "markdown", "csv", "html", "htm"}

    if file_ext not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: .{file_ext}，支持: {', '.join(sorted(supported_types))}",
        )

    # 写入临时文件
    file_id = f"file_{uuid.uuid4().hex[:8]}"
    temp_file = None

    try:
        content = await file.read()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}")
        temp_file.write(content)
        temp_file.close()

        file_size = len(content)

        # 1. 解析文件
        text = file_parser_service.parse_file(Path(temp_file.name), file_ext)
        if not text.strip():
            raise HTTPException(status_code=400, detail="文件内容为空或无法提取文本")

        # 2. 分块
        chunks = chunking_service.chunk_text(text)
        if not chunks:
            raise HTTPException(status_code=400, detail="文本分块后无内容")

        # 3. 嵌入
        embeddings = await embedding_service.get_embeddings_batch(chunks)

        # 4. 存入 Qdrant
        retrieval_service.upsert_documents(
            kb_id=kb_id,
            chunks=chunks,
            embeddings=embeddings,
            file_id=file_id,
            filename=file.filename,
            file_type=file_ext,
        )

        logger.info(
            f"File uploaded to {kb_id}: {file.filename} "
            f"({file_size} bytes, {len(chunks)} chunks)"
        )

        return {
            "file_id": file_id,
            "filename": file.filename,
            "file_type": file_ext,
            "size_bytes": file_size,
            "chunk_count": len(chunks),
            "message": f"文件 {file.filename} 已成功上传并处理",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")
    finally:
        if temp_file:
            Path(temp_file.name).unlink(missing_ok=True)


@router.delete("/{kb_id}/files/{file_id}")
async def delete_file(kb_id: str, file_id: str):
    """从知识库中删除指定文件"""
    if not retrieval_service.collection_exists(kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        retrieval_service.delete_file_documents(kb_id, file_id)
        logger.info(f"Deleted file {file_id} from {kb_id}")
        return {"message": f"文件 {file_id} 已从知识库中删除"}
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
