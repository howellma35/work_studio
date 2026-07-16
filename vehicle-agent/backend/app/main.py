"""
AutoMind 车机智能助手 - FastAPI 服务入口

集成:
- ag_ui_langgraph 原生 AG-UI 端点（/copilotkit）— SSE, text/event-stream
- LangFuse 可观测性
- LangGraph Studio 调试支持
- 健康检查 & 状态查询接口
"""
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.graph.supervisor import get_graph
from app.utils.observability import get_langfuse_handler, setup_observability


# ===== 每日对话次数限制（基于 IP，文件持久化，每天自动重置） =====
VEHICLE_DAILY_LIMIT = 5
_limit_disabled = os.getenv("DAILY_LIMIT_DISABLED", "").lower() in ("1", "true", "yes")
_usage_file = Path("./data/usage.json")


def _load_usage() -> dict:
    """从文件读取 usage 数据"""
    if _usage_file.exists():
        try:
            return json.loads(_usage_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_usage(data: dict) -> None:
    """持久化 usage 数据到文件"""
    _usage_file.parent.mkdir(parents=True, exist_ok=True)
    _usage_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _get_client_ip(request: Request) -> str:
    # X-Forwarded-For 最后一层 nginx 添加的真实客户端 IP 在最前面
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # X-Real-IP 备选
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def _is_bypassed(ip: str) -> bool:
    """内网 IP、Docker 内部 IP 或环境变量关闭限制时跳过"""
    if _limit_disabled:
        return True
    # 内网 IP: 192.168.x.x, 10.x.x.x, 127.0.0.1
    # Docker bridge: 172.16-31.x.x (容器间通信 IP)
    if ip.startswith("192.168.") or ip.startswith("10.") or ip == "127.0.0.1":
        return True
    if ip.startswith("172."):
        # Docker 默认分配 172.16.0.0/12 范围，全部视为内部
        second_octet = ip.split(".")[1] if len(ip.split(".")) > 1 else "0"
        if 16 <= int(second_octet) <= 31:
            return True
    return False


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
    """应用生命周期：启动时初始化可观测性、RAGFlow 与 Agent 图"""
    setup_logging()
    setup_observability()
    logger.info("=" * 60)
    logger.info("AutoMind 车机智能助手启动中...")
    logger.info(f"LLM 模型: {settings.LLM_MODEL} @ {settings.LLM_API_BASE}")
    logger.info(f"MCP 传输: {settings.MCP_TRANSPORT}")
    logger.info(f"LangFuse: {'已启用' if settings.langfuse_enabled else '未配置'}")
    logger.info(f"RAGFlow: {'已配置' if settings.ragflow_enabled else '未配置'}")
    logger.info("=" * 60)

    # ===== 初始化 RAGFlow 知识库与记忆 =====
    ragflow_ok = False
    if settings.ragflow_enabled:
        try:
            from app.ragflow.client import ragflow_client
            from app.ragflow.knowledge_service import knowledge_service
            from app.ragflow.memory_service import memory_service

            ragflow_ok = ragflow_client.init()
            if ragflow_ok:
                knowledge_service.init()
                memory_service.init()
                logger.info("RAGFlow 知识库与记忆模块初始化成功")

                # 初始化模拟知识数据（仅首次）
                try:
                    from app.ragflow.init_datasets import init_mock_knowledge
                    await init_mock_knowledge()
                except Exception as e:
                    logger.warning(f"模拟知识数据初始化失败（不影响运行）: {e}")
            else:
                logger.warning("RAGFlow 连接失败，降级为本地模式")
        except Exception as e:
            logger.warning(f"RAGFlow 模块加载失败: {e}")

    # 通知 MemoryManager RAGFlow 可用状态
    memory_manager.set_ragflow_available(ragflow_ok)

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

# ===== 注册知识库和会话管理路由 =====
from app.routers.session import router as session_router
from app.routers.knowledge import router as knowledge_router

app.include_router(session_router)
app.include_router(knowledge_router)


# ===== 每日对话限制中间件 =====
@app.middleware("http")
async def daily_limit_middleware(request: Request, call_next):
    """对 POST /copilotkit 请求进行每日次数限制"""
    if request.method == "POST" and request.url.path == "/copilotkit":
        ip = _get_client_ip(request)

        if _is_bypassed(ip):
            return await call_next(request)

        today = date.today().isoformat()
        usage = _load_usage()
        record = usage.get(ip)

        if not record or record["date"] != today:
            usage[ip] = {"date": today, "count": 1}
            _save_usage(usage)
        elif record["count"] >= VEHICLE_DAILY_LIMIT:
            logger.warning(f"每日限制达到: ip={ip}, count={record['count']}/{VEHICLE_DAILY_LIMIT}")
            return JSONResponse(
                status_code=429,
                content={"detail": f"今日对话次数已用完 ({VEHICLE_DAILY_LIMIT}/{VEHICLE_DAILY_LIMIT})，请明天再来"},
            )
        else:
            usage[ip] = {"date": record["date"], "count": record["count"] + 1}
            _save_usage(usage)

    return await call_next(request)


# ===== REST API 端点 =====
@app.get("/api/vehicle/proactive")
async def proactive_sse(request: Request):
    """SSE 主动推荐推送端点

    前端通过此端点接收实时主动推荐消息。
    连接保持打开，每次评估命中规则时推送 JSON 消息。
    """
    from starlette.responses import StreamingResponse
    from app.services.proactive_engine import proactive_engine

    async def event_generator():
        """SSE 事件生成器"""
        queue = asyncio.Queue()

        # 注册推送回调
        async def callback(messages: list[dict]):
            for msg in messages:
                await queue.put(msg)

        proactive_engine.subscribe(callback)

        try:
            while True:
                # 等待推送消息或心跳
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 心跳包，保持连接
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
        except asyncio.CancelledError:
            logger.info("[SSE] 主动推荐推送连接关闭")
        finally:
            # 清理订阅
            if callback in proactive_engine._subscribers:
                proactive_engine._subscribers.remove(callback)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/vehicle/proactive/trigger")
async def proactive_trigger(request: Request):
    """手动触发主动推荐评估（用于开发调试）

    提交车况数据，引擎立即评估所有规则并返回命中结果。
    """
    from app.services.proactive_engine import proactive_engine

    body = await request.json()
    vehicle_status = body.get("vehicle_status", {})
    weather = body.get("weather", {})
    scene = body.get("scene", "idle")

    proactive_engine.update_vehicle_status(vehicle_status)
    proactive_engine.update_weather(weather)
    proactive_engine.update_scene(scene)

    messages = await proactive_engine.evaluate_and_push()
    return {"triggered_rules": len(messages), "messages": messages}


@app.get("/api/vehicle/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "automind",
        "model": settings.LLM_MODEL,
        "langfuse_enabled": settings.langfuse_enabled,
    }


@app.get("/api/vehicle/chat-count")
async def chat_count(request: Request):
    """查询当前 IP 今日剩余对话次数"""
    ip = _get_client_ip(request)
    today = date.today().isoformat()
    usage = _load_usage()
    record = usage.get(ip)
    used = record["count"] if (record and record["date"] == today) else 0
    return {
        "ip": ip,
        "date": today,
        "used": used,
        "limit": VEHICLE_DAILY_LIMIT,
        "remaining": max(0, VEHICLE_DAILY_LIMIT - used),
    }


@app.get("/api/vehicle/agent-info")
async def agent_info():
    """获取 Agent 架构信息（用于前端展示）"""
    from app.graph.scene_config import SCENE_CONFIGS, DrivingScene, get_scene_display

    # 所有场景信息（前端可用）
    all_scenes = {scene.value: get_scene_display(scene) for scene in DrivingScene}

    return {
        "agent_name": "AutoMind",
        "architecture": "supervisor(create_agent) + sub-agents as tools (A2)",
        "supervisor_tools": ["select_origin", "update_map"],
        "sub_agents": [
            {"name": "navigation_agent", "desc": "导航专家", "tools": ["plan_route", "search_poi", "get_traffic_info"]},
            {"name": "media_agent", "desc": "多媒体专家", "tools": ["play_music", "pause_music", "next_song", "set_volume", "get_playlist"]},
            {"name": "vehicle_agent", "desc": "车辆控制专家", "tools": ["control_window", "set_climate", "lock_doors", "set_seat", "get_vehicle_status"]},
            {"name": "weather_agent", "desc": "天气助手", "tools": ["get_weather", "get_forecast"]},
            {"name": "reminder_agent", "desc": "智能提醒助手", "tools": ["create_reminder", "list_reminders", "save_user_preference"]},
            {"name": "knowledge_agent", "desc": "知识库助手", "tools": ["search_knowledge", "import_knowledge", "list_knowledge_bases"]},
        ],
        "driving_scenes": all_scenes,
        "modules": {
            "memory": {"short_term": "AsyncSqliteSaver", "long_term": "ChromaDB + SQLite"},
            "mcp": "Model Context Protocol (FastMCP)",
            "observability": "LangFuse",
            "scene_machine": "LangGraph StateGraph (5态驾驶场景)",
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
