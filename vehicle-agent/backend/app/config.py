"""
AutoMind 车机智能助手 - 全局配置
所有配置项通过环境变量读取，使用 pydantic-settings 自动加载 + 类型校验
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（pydantic-settings 自动从 .env 加载，类型自动转换）"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 服务配置 =====
    PORT: int = 8001
    CORS_ORIGINS: str = "*"  #逗号分隔，运行时 split

    # ===== LLM 配置（百炼平台 OpenAI 兼容接口）=====
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "deepseek-v3"

    # ===== MCP Server 配置 =====
    MCP_TRANSPORT: str = "stdio"
    MCP_SERVER_URL: str = "http://localhost:8765"
    MAP_SERVICE_PROVIDER: str = "amap"

    # ===== 高德地图 API 配置 =====
    AMAP_API_KEY: str = ""
    AMAP_JS_KEY: str = ""
    AMAP_JS_SECRET: str = ""  # JS API 安全密钥
    AMAP_API_BASE: str = "https://restapi.amap.com/v3"

    # ===== 记忆模块配置 =====
    MEMORY_ENABLED: bool = True
    CHROMA_PERSIST_DIR: Path = Path("./data/chroma")
    SQLITE_DB_PATH: str = "./data/memory.db"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ===== LangFuse 可观测性配置 =====
    LANGFUSE_BASE_URL: str = "http://localhost:3000"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # ===== 日志 =====
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")

    # ===== Demo 默认值 =====
    DEFAULT_VEHICLE_TEMP: int = 22
    DEFAULT_VEHICLE_USER_ID: str = "demo_user_001"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS 拆分为列表"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

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
