"""
AI 后端服务配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置"""

    # 服务端口
    PORT: int = int(os.getenv("AI_PORT", "8000"))

    # CORS 允许的源
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # LLM API 配置（OpenAI 兼容接口）
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    LLM_DEFAULT_MODEL: str = os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini")

    # 上传文件限制 (bytes)
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))


settings = Settings()
