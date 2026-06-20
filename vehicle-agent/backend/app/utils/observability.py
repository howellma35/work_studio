"""LangFuse 可观测性集成

使用 Langfuse V4 SDK 的官方标准方案:
- LangChain/LangGraph: 通过 CallbackHandler 自动追踪所有调用
- 自定义业务逻辑: 通过 @observe 装饰器手动追踪

追踪内容:
1. 每次 LLM 调用的 prompt/completion/token 消耗
2. 每次工具调用的输入/输出
3. Agent 每个节点的状态变化与路由决策
4. 完整的 trace 树状图，支持多层级嵌套

官方文档: https://langfuse.com/docs/integrations/langchain/tracing

配置方式: 在 .env 中填写 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL
"""
import logging
import os

from loguru import logger

from app.config import settings

# Langfuse CallbackHandler 单例
_langfuse_handler = None


def setup_observability() -> None:
    """
    初始化 LangFuse 追踪

    Langfuse V4 SDK 标准初始化流程:
    1. 设置环境变量 (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL)
    2. 创建 CallbackHandler 单例
    3. CallbackHandler 通过 LangChain 回调机制自动追踪:
       - ChatOpenAI 的所有 LLM 调用
       - LangGraph 的所有节点执行
       - 工具调用的输入/输出
       - Agent 路由决策 (transfer_to_xxx)
    """
    # Suppress OpenTelemetry noise logs (Langfuse V4 uses OTel internally)
    logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

    if settings.langfuse_enabled:
        # Set Langfuse env vars for V4 SDK auto-initialization
        # LANGFUSE_BASE_URL is the official env var name (per Langfuse docs)
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.LANGFUSE_BASE_URL)

        # Initialize CallbackHandler singleton
        try:
            from langfuse.langchain import CallbackHandler

            global _langfuse_handler
            _langfuse_handler = CallbackHandler()

            logger.info(
                f"LangFuse 可观测性已启用 | "
                f"Host: {settings.LANGFUSE_BASE_URL} | "
                f"SDK: V4 CallbackHandler | "
                f"模型: {settings.LLM_MODEL}"
            )
            logger.info(
                "追踪覆盖: LLM调用 / 工具调用 / Agent路由 / 节点执行 "
                "→ 自动生成 trace 树状图"
            )
        except Exception as e:
            logger.warning(f"LangFuse CallbackHandler 初始化失败: {e}")
            logger.warning("请检查: 1) langfuse>=4.0.0 是否安装  2) API Key 是否正确")
    else:
        logger.warning(
            "LangFuse 未配置 PUBLIC_KEY / SECRET_KEY，可观测性未启用。\n"
            "请在 .env 中填写 LangFuse 凭证后重启服务。\n"
            "自托管部署: docker compose up -d langfuse (见 deploy/docker-compose.yml)\n"
            "云服务: https://cloud.langfuse.com (免费额度)"
        )
        logger.info(
            "替代方案: 使用 LangGraph Studio 进行本地可视化调试\n"
            "  安装: pip install langgraph-cli\n"
            "  启动: langgraph dev (在 vehicle-agent/backend 目录下)"
        )


def get_langfuse_handler():
    """
    获取 Langfuse CallbackHandler 单例

    在 main.py 中注入到 LangGraphAgent 的 config.callbacks:
        agent = LangGraphAgent(
            name="automind",
            graph=graph,
            config={"callbacks": [get_langfuse_handler()]},
        )

    Returns:
        CallbackHandler 实例，或 None（如果 Langfuse 未启用）
    """
    return _langfuse_handler
