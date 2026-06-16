"""
猜词游戏后端服务入口
FastAPI + Socket.IO
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.config import settings
from app.services.game_service import init_game
from app.ws.handler import register_handlers


def setup_logging() -> None:
    """配置分级日志"""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        settings.LOG_DIR / "game.log", encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


# Socket.IO
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CORS_ORIGINS,
)

sio_asgi_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=None,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Game Server 启动中...")
    logger.info(f"Embedding API: {settings.EMBEDDING_API_URL}")
    logger.info(f"相似度阈值: {settings.SIMILARITY_THRESHOLD}")

    init_game()
    register_handlers(sio)

    yield
    logger.info("Game Server 已关闭")


app = FastAPI(
    title="Mahongwei Studio Game Server",
    description="猜词游戏 WebSocket 后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "game-server"}


@app.get("/api/game/words")
async def get_words(category: str = None, difficulty: int = None):
    from app.services.game_service import list_words
    return list_words(category=category, difficulty=difficulty)


# 组合 FastAPI + Socket.IO
combined_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
)
