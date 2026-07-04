"""
AI 聊天路由 — 支持 RAG 知识库检索增强
"""
import json
import logging
import os
from datetime import date
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.services.llm_service import chat_completion
from app.services import embedding_service, retrieval_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ===== 每日对话次数限制（基于 IP，内存存储，每天自动重置） =====
DAILY_LIMIT = 5
_limit_disabled = os.getenv("DAILY_LIMIT_DISABLED", "").lower() in ("1", "true", "yes")
_usage: dict[str, dict] = {}  # { ip: {"date": "2026-07-04", "count": 3} }


def _is_bypassed(ip: str) -> bool:
    """内网 IP 或环境变量关闭限制时跳过"""
    if _limit_disabled:
        return True
    # 内网 IP 段自动免限制（开发调试用）
    return ip.startswith("192.168.") or ip.startswith("10.") or ip == "127.0.0.1"


def _get_client_ip(request: Request) -> str:
    # 通过 nginx 代理时从 X-Forwarded-For 获取真实 IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_daily_limit(ip: str) -> int:
    """检查并增加 IP 的每日对话计数，返回剩余次数。超出则 raise HTTPException"""
    if _is_bypassed(ip):
        return DAILY_LIMIT  # 免限制
    today = date.today().isoformat()
    record = _usage.get(ip)

    if not record or record["date"] != today:
        _usage[ip] = {"date": today, "count": 1}
        return DAILY_LIMIT - 1

    if record["count"] >= DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"今日对话次数已用完 ({DAILY_LIMIT}/{DAILY_LIMIT})，请明天再来",
        )

    record["count"] += 1
    return DAILY_LIMIT - record["count"]


@router.get("/models")
async def get_models():
    """获取可用模型列表"""
    return {
        "models": [
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "provider": "百炼"},
            {"id": "deepseek-v3", "name": "DeepSeek V3", "provider": "百炼"},
            {"id": "qwen-plus", "name": "通义千问 Plus", "provider": "百炼"},
            {"id": "qwen-max", "name": "通义千问 Max", "provider": "百炼"},
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
        ]
    }


@router.get("/chat-count")
async def chat_count(request: Request):
    """查询当前 IP 今日剩余对话次数"""
    ip = _get_client_ip(request)
    today = date.today().isoformat()
    record = _usage.get(ip)
    used = record["count"] if (record and record["date"] == today) else 0
    return {
        "ip": ip,
        "date": today,
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used),
    }


@router.post("/chat")
async def chat(
    request: Request,
    message: str = Form(...),
    model: str = Form(default="gpt-4o-mini"),
    history: str = Form(default="[]"),
    kb_id: str = Form(default=""),
    knowledge_file: UploadFile | None = File(default=None),
):
    """
    AI 聊天接口（支持 RAG）

    - message: 用户消息
    - model: 选择的模型
    - history: JSON 格式的历史消息
    - kb_id: 可选的知识库 ID，指定后进行 RAG 检索增强
    - knowledge_file: 可选的临时知识文件（向后兼容）
    """
    # 每日限制检查
    client_ip = _get_client_ip(request)
    remaining = _check_daily_limit(client_ip)
    logger.info(f"Chat request: ip={client_ip}, model={model}, remaining={remaining}/{DAILY_LIMIT}")

    try:
        messages: list[dict[str, Any]] = json.loads(history)
    except json.JSONDecodeError:
        messages = []

    # RAG 检索上下文
    knowledge_context = ""

    # 优先使用知识库 RAG
    if kb_id:
        try:
            knowledge_context = await _rag_retrieve(kb_id, message)
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            knowledge_context = ""

    # 兼容旧的 knowledge_file 参数
    if not knowledge_context and knowledge_file and knowledge_file.filename:
        try:
            content = await knowledge_file.read()
            text = content.decode("utf-8", errors="ignore")
            knowledge_context = text[:8000]
            logger.info(f"Knowledge file loaded: {knowledge_file.filename}, {len(knowledge_context)} chars")
        except Exception as e:
            logger.warning(f"Failed to read knowledge file: {e}")

    # 构建系统消息
    system_msg = "你是一个智能助手，请用中文回答用户的问题。"
    if knowledge_context:
        system_msg += (
            f"\n\n以下是从知识库中检索到的相关资料，请优先基于这些资料回答问题。"
            f"如果资料中没有相关信息，请结合你的知识进行回答，并说明哪些内容来自知识库、哪些来自你的知识。\n\n"
            f"---\n{knowledge_context}\n---"
        )

    # 构建完整消息列表
    full_messages = [{"role": "system", "content": system_msg}]
    for msg in messages:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            full_messages.append({"role": msg["role"], "content": msg["content"]})
    full_messages.append({"role": "user", "content": message})

    try:
        reply = await chat_completion(full_messages, model)
        logger.info(f"Chat response: model={model}, reply_length={len(reply)}")
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")


async def _rag_retrieve(kb_id: str, query: str, top_k: int = 5) -> str:
    """RAG 检索：从知识库中获取相关文档片段"""
    if not retrieval_service.collection_exists(kb_id):
        logger.warning(f"Knowledge base {kb_id} does not exist")
        return ""

    # 1. 嵌入用户查询
    query_embedding = await embedding_service.get_embedding(query)

    # 2. 搜索相关文档
    results = retrieval_service.search(kb_id, query_embedding, top_k=top_k)

    if not results:
        logger.info(f"No relevant documents found in {kb_id}")
        return ""

    # 3. 拼接检索结果
    context_parts = []
    for i, result in enumerate(results):
        source = result.get("filename", "未知来源")
        score = result.get("score", 0)
        text = result.get("text", "")
        context_parts.append(f"[来源: {source}, 相关度: {score:.2f}]\n{text}")

    context = "\n\n".join(context_parts)
    logger.info(f"RAG retrieved {len(results)} chunks from {kb_id}, total {len(context)} chars")
    return context
