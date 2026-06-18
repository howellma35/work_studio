"""
LLM 模型工厂
统一创建 LLM 实例，支持百炼平台 OpenAI 兼容接口
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache(maxsize=1)
def create_llm(
    model: str | None = None,
    temperature: float = 0.7,
    streaming: bool = True,
) -> ChatOpenAI:
    """
    创建 LLM 实例（单例，默认走百炼平台 OpenAI 兼容接口）

    Args:
        model: 模型名称，默认从配置读取 ${LLM_MODEL}
        temperature: 温度参数
        streaming: 是否流式输出

    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=model or settings.LLM_MODEL,
        temperature=temperature,
        streaming=streaming,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
    )
