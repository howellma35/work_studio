"""
游戏后端配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PORT: int = int(os.getenv("GAME_PORT", "3001"))
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Embedding API
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "https://api.siliconflow.cn/v1/embeddings")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    # Game
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
    ROUND_DURATION: int = int(os.getenv("ROUND_DURATION", "60"))
    MAX_GUESSES_PER_ROUND: int = int(os.getenv("MAX_GUESSES_PER_ROUND", "3"))

    # Data
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))

    # Logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))


settings = Settings()
