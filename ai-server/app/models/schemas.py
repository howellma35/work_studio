"""
知识库数据模型
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: str = Field(default="", max_length=500, description="知识库描述")


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    id: str
    name: str
    description: str
    file_count: int = 0
    chunk_count: int = 0
    created_at: str


class FileInfo(BaseModel):
    """文件信息"""
    file_id: str
    filename: str
    file_type: str
    size_bytes: int
    chunk_count: int
    uploaded_at: str


class KnowledgeBaseDetail(BaseModel):
    """知识库详情（含文件列表）"""
    id: str
    name: str
    description: str
    files: list[FileInfo]
    chunk_count: int
    created_at: str


class ChatRequest(BaseModel):
    """RAG 聊天请求（JSON body 版本）"""
    message: str
    model: str = "gpt-4o-mini"
    history: list[dict] = Field(default_factory=list)
    kb_id: Optional[str] = None
