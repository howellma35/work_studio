"""
LangFuse 可观测性集成
通过环境变量自动埋点，记录每次 Agent 调用的输入/输出/token/延迟/工具调用链
"""
from loguru import logger

from app.config import settings


def setup_observability() -> None:
    """
    初始化 LangFuse 追踪

    LangFuse 通过环境变量自动捕获 LangChain/LangGraph 的所有调用：
    - 每次 LLM 调用的 prompt/completion
    - 每次工具调用的输入/输出
    - Agent 每个节点的状态变化
    - Token 消耗与延迟统计

    在 LangFuse 控制台 (默认 http://localhost:3000) 可查看完整 trace。
    """
    if settings.langfuse_enabled:
        logger.info(
            f"LangFuse 可观测性已启用 | Host: {settings.LANGFUSE_HOST} | "
            f"模型: {settings.LLM_MODEL}"
        )
    else:
        logger.warning(
            "LangFuse 未配置 PUBLIC_KEY / SECRET_KEY，可观测性未启用。"
            "请在 .env 中填写 LangFuse 凭证后重启服务。"
        )
