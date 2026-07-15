"""
知识库管理路由
支持知识库创建、文档上传、内容导入、检索测试
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger

from app.config import settings

router = APIRouter(prefix="/api/vehicle/knowledge", tags=["knowledge"])


@router.post("/datasets")
async def create_dataset(name: str = Form(...), description: str = Form("")):
    """
    创建知识库（调用 RAGFlow）

    Args:
        name: 知识库名称
        description: 知识库描述
    """
    try:
        from app.ragflow.knowledge_service import knowledge_service
        from app.ragflow.client import ragflow_client

        if not ragflow_client.available:
            raise HTTPException(status_code=503, detail="RAGFlow 服务不可用")

        ds_id = knowledge_service.create_dataset(name, description)
        return {"status": "ok", "dataset_id": ds_id, "name": name}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库失败: {e}")


@router.get("/datasets")
async def list_datasets():
    """列出所有知识库"""
    try:
        from app.ragflow.knowledge_service import knowledge_service

        datasets = knowledge_service.list_datasets()
        return {"status": "ok", "datasets": datasets, "total": len(datasets)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"RAGFlow 服务不可用: {e}")


@router.post("/datasets/{dataset_id}/files")
async def upload_files(dataset_id: str, files: list[UploadFile] = File(...)):
    """
    上传文件到知识库

    Args:
        dataset_id: 知识库 ID
        files: 上传的文件列表
    """
    try:
        from app.ragflow.knowledge_service import knowledge_service

        # 将上传文件保存到临时目录
        temp_dir = Path("./data/temp_upload")
        temp_dir.mkdir(parents=True, exist_ok=True)

        file_paths = []
        saved_names = []
        for f in files:
            temp_path = temp_dir / f.filename
            content = await f.read()
            temp_path.write_bytes(content)
            file_paths.append(temp_path)
            saved_names.append(f.filename)

        doc_ids = knowledge_service.upload_files(dataset_id, file_paths)

        # 清理临时文件
        for fp in file_paths:
            fp.unlink(missing_ok=True)

        return {
            "status": "ok",
            "dataset_id": dataset_id,
            "document_ids": doc_ids,
            "filenames": saved_names,
            "count": len(doc_ids),
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


@router.post("/datasets/{dataset_id}/content")
async def import_content(dataset_id: str, name: str = Form(...), content: str = Form(...)):
    """
    内联文本导入到知识库（无需上传文件）

    Args:
        dataset_id: 知识库 ID
        name: 文档名称
        content: 文档内容文本
    """
    try:
        from app.ragflow.knowledge_service import knowledge_service

        doc_id = knowledge_service.import_content(dataset_id, name, content)
        return {"status": "ok", "dataset_id": dataset_id, "document_id": doc_id, "name": name}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")


@router.post("/search")
async def search_knowledge(query: str = Form(...), top_k: Optional[int] = None):
    """
    搜索知识库（测试/调试接口）

    Args:
        query: 查询文本
        top_k: 返回结果数量
    """
    try:
        from app.ragflow.knowledge_service import knowledge_service

        result = knowledge_service.search(query, top_k=top_k)
        if not result:
            return {"status": "ok", "results": [], "message": "知识库中无相关内容"}

        return {
            "status": "ok",
            "query": query,
            "results": result,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"搜索失败: {e}")


@router.get("/status")
async def knowledge_status():
    """知识库服务状态"""
    try:
        from app.ragflow.client import ragflow_client

        available = ragflow_client.available
        dataset_count = len(knowledge_service.dataset_ids) if available else 0

        return {
            "status": "ok",
            "ragflow_available": available,
            "dataset_count": dataset_count,
            "ragflow_base_url": settings.RAGFLOW_BASE_URL,
        }
    except Exception:
        return {
            "status": "ok",
            "ragflow_available": False,
            "dataset_count": 0,
            "ragflow_base_url": settings.RAGFLOW_BASE_URL,
        }
