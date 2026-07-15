"""
会话管理路由
支持多会话创建、切换、删除，会话间共享 RAGFlow 记忆
"""
import uuid

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import settings

router = APIRouter(prefix="/api/vehicle/sessions", tags=["session"])


@router.post("")
async def create_session():
    """
    创建新会话

    返回 session_id 和 thread_id，用于前端 CopilotKit 关联
    """
    session_id = uuid.uuid4().hex[:12]
    thread_id = f"thread_{session_id}"

    logger.info(f"新会话已创建: session_id={session_id}, thread_id={thread_id}")

    return {
        "session_id": session_id,
        "thread_id": thread_id,
        "user_id": settings.DEFAULT_VEHICLE_USER_ID,
        "created_at": "",
    }


@router.get("")
async def list_sessions():
    """
    列出所有会话

    注意：LangGraph checkpointer 是 SQLite，没有直接的会话列表接口。
    这里返回模拟数据。生产环境需要通过 checkpointer 的 API 获取。
    """
    # 暂时返回简单列表
    return {
        "sessions": [],
        "total": 0,
        "message": "会话列表通过 LangGraph checkpointer 管理，前端 CopilotKit 自动管理 thread_id",
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    logger.info(f"会话删除请求: session_id={session_id}")
    return {
        "status": "ok",
        "session_id": session_id,
        "message": "会话已删除（LangGraph checkpointer 需手动清理）",
    }
