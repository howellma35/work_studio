"""
AutoMind 车机智能助手 - FastAPI 服务入口

集成:
- ag_ui_langgraph 原生 AG-UI 端点（/copilotkit）— SSE, text/event-stream
- LangFuse 可观测性
- LangGraph Studio 调试支持
- 健康检查 & 状态查询接口
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.graph.supervisor import get_graph
from app.utils.observability import get_langfuse_handler, setup_observability


# ===== 日志配置 =====
def setup_logging() -> None:
    """配置 Loguru 分级日志（控制台 + 文件）"""
    settings.ensure_dirs()
    logger.remove()  # 移除默认 handler
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> | {message}",
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    logger.add(
        settings.LOG_DIR / "automind.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化可观测性与 Agent 图"""
    setup_logging()
    setup_observability()
    logger.info("=" * 60)
    logger.info("AutoMind 车机智能助手启动中...")
    logger.info(f"LLM 模型: {settings.LLM_MODEL} @ {settings.LLM_API_BASE}")
    logger.info(f"MCP 传输: {settings.MCP_TRANSPORT}")
    logger.info(f"LangFuse: {'已启用' if settings.langfuse_enabled else '未配置'}")
    logger.info("=" * 60)

    # 预构建 Supervisor 图（会加载 MCP 工具）
    logger.info("正在构建 LangGraph Supervisor 图...")
    graph = await get_graph()
    logger.info("Supervisor 图构建完成")

    # 注册 AG-UI 原生端点
    #
    # 架构: Frontend → CopilotSseRuntime(Node:4000) → HttpAgent → POST /copilotkit
    #
    # HttpAgent(@ag-ui/client) 发送: Content-Type: application/json, Accept: text/event-stream
    # 请求体: RunAgentInput JSON
    # 期望响应: SSE 流（text/event-stream, "data: {...}\n\n" 格式）
    #
    # add_langgraph_fastapi_endpoint 正是提供此行为的官方 best practice：
    #   - 使用 EventEncoder 将 Pydantic 事件对象编码为 "data: {json}\n\n"
    #   - 返回 StreamingResponse(media_type="text/event-stream")
    #   - 每请求 clone() agent，避免并发状态污染
    #   - LangGraphAGUIAgent.langgraph_default_merge_state() 自动将 RunAgentInput.tools
    #     存入 state["copilotkit"]["actions"]，供 CopilotKitMiddleware 注入给子 Agent
    from ag_ui_langgraph import add_langgraph_fastapi_endpoint
    from copilotkit import LangGraphAGUIAgent

    langfuse_handler = get_langfuse_handler()
    agent_config = {}
    if langfuse_handler:
        agent_config = {"callbacks": [langfuse_handler]}
        logger.info("Langfuse CallbackHandler 已注入到 LangGraphAGUIAgent")

    agent = LangGraphAGUIAgent(
        name="default",
        description="AutoMind 智能车机助手 - 支持导航、音乐、车辆控制、天气、提醒",
        graph=graph,
        config=agent_config,
    )
    add_langgraph_fastapi_endpoint(app, agent, path="/copilotkit")
    logger.info("AG-UI 端点已注册: POST /copilotkit（SSE, text/event-stream）")
    logger.info("AG-UI 健康检查: GET /copilotkit/health")
    logger.info("=" * 60)
    logger.info("AutoMind 服务就绪")
    logger.info("=" * 60)

    yield

    # 关闭持久化 checkpointer
    from app.graph.supervisor import close_checkpointer
    await close_checkpointer()

    logger.info("AutoMind 服务已关闭")


# ===== FastAPI 应用 =====
app = FastAPI(
    title="AutoMind 智能车机助手",
    description="基于 LangGraph + MCP + CopilotKit 的工业级车载智能助手平台",
    version="1.0.0",
    lifespan=lifespan,
    # redirect_slashes=False,  # 避免 POST /copilotkit → 307 → HttpAgent 不跟重定向
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== REST API 端点 =====
@app.get("/api/vehicle/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "automind",
        "model": settings.LLM_MODEL,
        "langfuse_enabled": settings.langfuse_enabled,
    }


@app.get("/api/vehicle/agent-info")
async def agent_info():
    """获取 Agent 架构信息（用于前端展示）"""
    return {
        "agent_name": "AutoMind",
        "sub_agents": [
            {"name": "navigation_agent", "desc": "导航专家", "tools": ["plan_route", "search_poi", "get_traffic_info", "update_map", "select_origin"]},
            {"name": "media_agent", "desc": "多媒体专家", "tools": ["play_music", "pause_music", "next_song", "set_volume", "get_playlist"]},
            {"name": "vehicle_agent", "desc": "车辆控制专家", "tools": ["control_window", "set_climate", "lock_doors", "set_seat", "get_vehicle_status"]},
            {"name": "weather_agent", "desc": "天气助手", "tools": ["get_weather", "get_forecast"]},
            {"name": "reminder_agent", "desc": "智能提醒助手", "tools": ["create_reminder", "list_reminders", "save_user_preference"]},
        ],
        "modules": {
            "memory": {"short_term": "AsyncSqliteSaver", "long_term": "ChromaDB + SQLite"},
            "mcp": "Model Context Protocol (FastMCP)",
            "observability": "LangFuse",
        },
        # 高德地图 Key（前端地图渲染需要）
        "amap_js_key": settings.AMAP_JS_KEY,
        "amap_js_secret": settings.AMAP_JS_SECRET,
    }


def main():
    """启动服务"""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
