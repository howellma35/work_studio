"""
AI 后端服务入口
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, pdf


def setup_logging() -> None:
    """配置分级日志"""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 文件 handler
    file_handler = logging.FileHandler(
        settings.LOG_DIR / "app.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logging.info("AI Server 启动中...")
    logging.info(f"LLM API Base: {settings.LLM_API_BASE}")
    logging.info(f"默认模型: {settings.LLM_DEFAULT_MODEL}")
    yield
    logging.info("AI Server 已关闭")


app = FastAPI(
    title="Mahongwei Studio AI Server",
    description="AI 聊天 + PDF 解析后端服务",
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

# 路由
app.include_router(chat.router, prefix="/api/ai", tags=["AI"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ai-server"}
