"""LLM 模型工厂
统一创建 LLM 实例，支持百炼平台 OpenAI 兼容接口

Langfuse V4 SDK 通过 CallbackHandler 自动追踪 LLM 调用:
- CallbackHandler 在 main.py 中注入到 LangGraphAgent config
- 所有 ChatOpenAI 调用、工具调用、Agent 路由自动被追踪
- 无需在此处手动注入任何 handler
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI
from loguru import logger

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

    Note:
        Langfuse 追踪通过 CallbackHandler 实现（注入到 LangGraphAgent config），
        不在此处注入。环境变量在 setup_observability() 中已设置。
    """
    llm = ChatOpenAI(
        model=model or settings.LLM_MODEL,
        temperature=temperature,
        streaming=streaming,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
    )
    logger.debug(f"LLM 已创建 | model={llm.model_name}")
    return llm
