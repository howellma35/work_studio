"""LLM 模型工厂
统一创建 LLM 实例，支持百炼平台 OpenAI 兼容接口

自动注入 Langfuse CallbackHandler（若已配置），确保每次调用被追踪。
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI
from loguru import logger

from app.config import settings


def _get_langfuse_callback() -> list:
    """获取 Langfuse CallbackHandler（若已配置）"""
    if settings.langfuse_enabled:
        try:
            from langfuse.callback import CallbackHandler
            handler = CallbackHandler(
                publicKey=settings.LANGFUSE_PUBLIC_KEY,
                secretKey=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            logger.debug(f"Langfuse handler 已注入 LLM | session_id 可在 trace 中查看")
            return [handler]
        except Exception as e:
            logger.warning(f"Langfuse handler 创建失败: {e}")
    return []


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
        ChatOpenAI 实例（已注入 Langfuse callback）
    """
    llm = ChatOpenAI(
        model=model or settings.LLM_MODEL,
        temperature=temperature,
        streaming=streaming,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
        callbacks=_get_langfuse_callback(),
    )
    logger.debug(f"LLM 已创建 | model={llm.model_name} | callbacks={len(llm.callbacks)}个")
    return llm
