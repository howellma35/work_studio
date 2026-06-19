"""
AutoMind 车机智能助手 - FastAPI 服务入口

集成:
- AG-UI SSE 端点（暴露 /agent 端点，通过 ag-ui-langgraph 直接流式输出）
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
from app.utils.observability import setup_observability


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
    await get_graph()
    logger.info("Supervisor 图构建完成")

    # 注册 AG-UI SSE 端点（标准协议，无需自定义适配器）
    from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

    agent = LangGraphAgent(
        name="automind",
        description="AutoMind 智能车机助手 - 支持导航、音乐、车辆控制、天气、提醒",
        graph=await get_graph(),
    )
    add_langgraph_fastapi_endpoint(app, agent, "/agent")
    logger.info("AG-UI SSE 端点已注册: POST /agent")
    logger.info("=" * 60)
    logger.info("AutoMind 服务就绪")
    logger.info("=" * 60)

    yield

    logger.info("AutoMind 服务已关闭")


# ===== FastAPI 应用 =====
app = FastAPI(
    title="AutoMind 智能车机助手",
    description="基于 LangGraph + MCP + CopilotKit 的工业级车载智能助手平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
            {"name": "navigation_agent", "desc": "导航专家", "tools": ["plan_route", "search_poi", "get_traffic_info"]},
            {"name": "media_agent", "desc": "多媒体专家", "tools": ["play_music", "pause_music", "next_song", "set_volume", "get_playlist"]},
            {"name": "vehicle_agent", "desc": "车辆控制专家", "tools": ["control_window", "set_climate", "lock_doors", "set_seat", "get_vehicle_status"]},
            {"name": "weather_agent", "desc": "天气助手", "tools": ["get_weather", "get_forecast"]},
            {"name": "reminder_agent", "desc": "智能提醒助手", "tools": ["create_reminder", "list_reminders", "save_user_preference"]},
        ],
        "modules": {
            "memory": {"short_term": "MemorySaver", "long_term": "ChromaDB + SQLite"},
            "mcp": "Model Context Protocol (FastMCP)",
            "observability": "LangFuse",
        },
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
