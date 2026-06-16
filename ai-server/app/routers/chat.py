"""
AI 聊天路由
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.llm_service import chat_completion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models")
async def get_models():
    """获取可用模型列表"""
    return {
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
            {"id": "qwen-plus", "name": "通义千问 Plus", "provider": "Alibaba"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "DeepSeek"},
        ]
    }


@router.post("/chat")
async def chat(
    message: str = Form(...),
    model: str = Form(default="gpt-4o-mini"),
    history: str = Form(default="[]"),
    knowledge_file: UploadFile | None = File(default=None),
):
    """
    AI 聊天接口
    - message: 用户消息
    - model: 选择的模型
    - history: JSON 格式的历史消息
    - knowledge_file: 可选的知识库文件
    """
    logger.info(f"Chat request: model={model}, message_length={len(message)}")

    try:
        # 解析历史消息
        messages: list[dict[str, Any]] = json.loads(history)
    except json.JSONDecodeError:
        messages = []

    # 处理知识库文件
    knowledge_context = ""
    if knowledge_file and knowledge_file.filename:
        try:
            content = await knowledge_file.read()
            text = content.decode("utf-8", errors="ignore")
            # 截取前 8000 字符作为上下文
            knowledge_context = text[:8000]
            logger.info(f"Knowledge file loaded: {knowledge_file.filename}, {len(knowledge_context)} chars")
        except Exception as e:
            logger.warning(f"Failed to read knowledge file: {e}")

    # 构建系统消息
    system_msg = "你是一个智能助手，请用中文回答用户的问题。"
    if knowledge_context:
        system_msg += f"\n\n以下是用户提供的参考资料，请基于这些资料回答问题：\n\n---\n{knowledge_context}\n---\n\n如果参考资料中没有相关信息，请明确说明。"

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
