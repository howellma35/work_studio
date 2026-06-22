"""
AutoMind 车机智能助手 - 全局配置
所有配置项通过环境变量读取，支持 ${variable_name} 自定义
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置（从环境变量加载）"""

    # ===== 服务配置 =====
    PORT: int = int(os.getenv("PORT", "8001"))
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ===== LLM 配置（百炼平台 OpenAI 兼容接口）=====
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-v3")

    # ===== MCP Server 配置 =====
    MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:8765")
    MAP_SERVICE_PROVIDER: str = os.getenv("MAP_SERVICE_PROVIDER", "amap")

    # ===== 高德地图 API 配置 =====
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")
    AMAP_JS_KEY: str = os.getenv("AMAP_JS_KEY", "")
    AMAP_JS_SECRET: str = os.getenv("AMAP_JS_SECRET", "")  # JS API 安全密钥
    AMAP_API_BASE: str = os.getenv("AMAP_API_BASE", "https://restapi.amap.com/v3")

    # ===== 记忆模块配置 =====
    MEMORY_ENABLED: bool = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
    CHROMA_PERSIST_DIR: Path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"))
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/memory.db")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_API_BASE: str = os.getenv("EMBEDDING_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    # ===== LangFuse 可观测性配置 =====
    LANGFUSE_BASE_URL: str = os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3000"))
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")

    # ===== 日志 =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))

    # ===== Demo 默认值 =====
    DEFAULT_VEHICLE_TEMP: int = int(os.getenv("DEFAULT_VEHICLE_TEMP", "22"))
    DEFAULT_VEHICLE_USER_ID: str = os.getenv("DEFAULT_VEHICLE_USER_ID", "demo_user_001")

    def ensure_dirs(self) -> None:
        """确保运行所需目录存在"""
        self.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    @property
    def langfuse_enabled(self) -> bool:
        """LangFuse 是否已配置"""
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)


settings = Settings()
