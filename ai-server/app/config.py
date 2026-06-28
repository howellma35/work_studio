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

    # Embedding API 配置（SiliconFlow）
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "https://api.siliconflow.cn/v1/embeddings")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # Qdrant 向量数据库
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # 文本分块配置
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # 上传文件限制 (bytes)
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))


settings = Settings()
