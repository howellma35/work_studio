"""
长期记忆模块
- 向量记忆: ChromaDB 存储用户偏好（语义召回）
- 结构化记忆: SQLite 存储确定性用户档案
"""
import json
import sqlite3
import uuid
from pathlib import Path

from loguru import logger

from app.config import settings


class LongTermMemory:
    """长期用户偏好记忆，支持向量检索 + 结构化存储"""

    def __init__(self) -> None:
        self.db_path = settings.SQLITE_DB_PATH
        self._init_sqlite()
        self._chroma_collection = None

    def _init_sqlite(self) -> None:
        """初始化 SQLite 结构化记忆表"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id     TEXT PRIMARY KEY,
                profile     TEXT NOT NULL DEFAULT '{}',
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                content     TEXT NOT NULL,
                remind_at   TEXT NOT NULL,
                is_done     INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _get_chroma_collection(self):
        """懒加载 ChromaDB 集合"""
        if self._chroma_collection is None:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
                self._chroma_collection = client.get_or_create_collection(
                    name="user_preferences",
                    metadata={"description": "用户长期偏好记忆"}
                )
                logger.info(f"ChromaDB 集合已加载: {settings.CHROMA_PERSIST_DIR}")
            except Exception as e:
                logger.error(f"ChromaDB 初始化失败，降级为仅 SQLite 模式: {e}")
                self._chroma_collection = False  # 标记不可用
        return self._chroma_collection if self._chroma_collection is not False else None

    def _embed_text(self, text: str) -> list[float] | None:
        """使用百炼平台嵌入模型生成向量"""
        try:
            from langchain_openai import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
                base_url=settings.EMBEDDING_API_BASE,
            )
            return embeddings.embed_query(text)
        except Exception as e:
            logger.warning(f"嵌入生成失败，跳过向量存储: {e}")
            return None

    def save_preference(self, user_id: str, content: str, metadata: dict | None = None) -> None:
        """
        保存用户偏好到向量记忆库

        Args:
            user_id: 用户标识
            content: 偏好文本描述（如"用户喜欢听周杰伦的歌"）
            metadata: 附加元数据（如 category=navigation/media/climate）
        """
        collection = self._get_chroma_collection()
        if collection is None:
            return

        vector = self._embed_text(content)
        if vector is None:
            return

        doc_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        meta = {"user_id": user_id, **(metadata or {})}
        collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[content],
            metadatas=[meta],
        )
        logger.debug(f"偏好已保存: user={user_id}, content={content[:50]}...")

    def recall_preferences(self, user_id: str, query: str, top_k: int = 3) -> list[str]:
        """
        基于语义相似度召回用户偏好

        Args:
            user_id: 用户标识
            query: 查询文本（如"帮我导航回家"）
            top_k: 返回数量

        Returns:
            相关偏好文本列表
        """
        collection = self._get_chroma_collection()
        if collection is None:
            return []

        vector = self._embed_text(query)
        if vector is None:
            return []

        results = collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where={"user_id": user_id},
        )
        docs = results.get("documents", [[]])[0]
        logger.debug(f"偏好召回: user={user_id}, 命中 {len(docs)} 条")
        return docs

    def get_profile(self, user_id: str) -> dict:
        """获取用户结构化档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT profile FROM user_profiles WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else {}

    def update_profile(self, user_id: str, updates: dict) -> None:
        """更新用户结构化档案（合并写入）"""
        current = self.get_profile(user_id)
        current.update(updates)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO user_profiles (user_id, profile) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET profile=excluded.profile, updated_at=CURRENT_TIMESTAMP""",
            (user_id, json.dumps(current, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
        # 同步保存到向量记忆
        for key, value in updates.items():
            self.save_preference(
                user_id,
                f"用户的{key}偏好: {value}",
                metadata={"category": key},
            )

    def add_reminder(self, user_id: str, content: str, remind_at: str) -> str:
        """添加提醒"""
        reminder_id = uuid.uuid4().hex[:8]
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO reminders (id, user_id, content, remind_at) VALUES (?, ?, ?, ?)",
            (reminder_id, user_id, content, remind_at),
        )
        conn.commit()
        conn.close()
        return reminder_id

    def get_reminders(self, user_id: str, pending_only: bool = True) -> list[dict]:
        """获取用户提醒列表"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT id, content, remind_at, is_done FROM reminders WHERE user_id = ?"
        if pending_only:
            query += " AND is_done = 0"
        query += " ORDER BY remind_at"
        cursor = conn.execute(query, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "content": r[1], "remind_at": r[2], "is_done": bool(r[3])}
            for r in rows
        ]


# 全局单例
long_term_memory = LongTermMemory()
