"""LangFuse 可观测性集成

两层可观测机制:
1. LangFuse 自动追踪: 通过 CallbackHandler 自动捕获 LangChain/LangGraph 所有调用
   - 每次 LLM 调用的 prompt/completion
   - 每次工具调用的输入/输出
   - Agent 每个节点的状态变化
   - Token 消耗与延迟统计

2. LangGraph Studio: 通过 langgraph.json 配置支持本地可视化调试
   - 在 LangGraph Studio 中打开项目即可看到图的执行流程
   - 每个节点的输入/输出/路由决策一目了然

配置方式: 在 .env 中填写 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY
"""
import os

from loguru import logger

from app.config import settings


def setup_observability() -> None:
    """
    初始化 LangFuse 追踪

    LangFuse 通过 CallbackHandler 自动捕获 LangChain/LangGraph 的所有调用。
    需要确保 LANGFUSE 的三个环境变量被正确设置:
    - LANGFUSE_PUBLIC_KEY: 项目公钥
    - LANGFUSE_SECRET_KEY: 项目密钥
    - LANGFUSE_HOST: LangFuse 服务地址（默认 http://localhost:3000）

    dotenv 加载的值会自动进入 os.environ，LangChain 在创建 LLM 时
    会读取这些环境变量并自动注入 LangfuseCallbackHandler。
    """
    if settings.langfuse_enabled:
        # 确保 LangFuse 环境变量在 os.environ 中（供 LangChain 自动检测）
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
        os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_HOST)

        # 验证: LangfuseCallbackHandler 会在 LangChain 创建 LLM 时自动注入
        # 无需手动添加 callback，ChatOpenAI 会检测环境变量并自动配置
        try:
            from langfuse.callback import CallbackHandler
            handler = CallbackHandler(
                publicKey=settings.LANGFUSE_PUBLIC_KEY,
                secretKey=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            logger.info(
                f"LangFuse 可观测性已启用 | Host: {settings.LANGFUSE_HOST} | "
                f"模型: {settings.LLM_MODEL} | Handler: {type(handler).__name__}"
            )
            logger.info("提示: 访问 LangFuse 控制台查看完整 trace 树状图、工具调用链、token 统计")
        except Exception as e:
            logger.warning(f"LangFuse 初始化失败: {e}。请检查 .env 中的密钥是否正确。")
    else:
        logger.warning(
            "LangFuse 未配置 PUBLIC_KEY / SECRET_KEY，可观测性未启用。\n"
            "请在 .env 中填写 LangFuse 凭证后重启服务。\n"
            "自托管部署: docker run -p 3000:3000 langfuse/langfuse\n"
            "云服务: https://cloud.langfuse.com (免费额度)"
        )
        # 提供无 Langfuse 时的基础调试建议
        logger.info(
            "替代方案: 使用 LangGraph Studio 进行本地可视化调试\n"
            "  安装: pip install langgraph-cli\n"
            "  启动: langgraph dev (在 vehicle-agent/backend 目录下)"
        )
