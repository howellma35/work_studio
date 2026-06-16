"""
大模型调用服务（OpenAI 兼容接口）
支持 GPT、Claude、通义千问、DeepSeek 等模型
"""
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# 全局客户端实例
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
        )
    return _client


async def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """
    调用大模型进行对话

    Args:
        messages: 消息列表 [{"role": "system/user/assistant", "content": "..."}]
        model: 模型 ID，不传则使用默认模型
        max_tokens: 最大输出 token 数
        temperature: 采样温度

    Returns:
        模型回复文本
    """
    model = model or settings.LLM_DEFAULT_MODEL
    client = get_client()

    logger.info(f"LLM call: model={model}, messages={len(messages)}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content or ""
        logger.info(
            f"LLM response: model={model}, "
            f"tokens_in={response.usage.prompt_tokens if response.usage else '?'}, "
            f"tokens_out={response.usage.completion_tokens if response.usage else '?'}"
        )
        return content

    except Exception as e:
        logger.error(f"LLM error: model={model}, error={e}")
        raise
