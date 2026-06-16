"""
游戏轮次管理服务
内存 + JSON 文件持久化
"""
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.embedding_service import (
    calculate_similarity,
    is_correct,
    get_embedding,
    load_cached_embeddings,
)
from app.services.rank_service import (
    add_guess,
    get_leaderboard,
    get_guess_count,
    increment_guess_count,
    LeaderboardEntry,
)

logger = logging.getLogger(__name__)


class Word:
    def __init__(self, id: int, word: str, hint: str, category: str,
                 difficulty: int, embedding: Optional[list[float]] = None):
        self.id = id
        self.word = word
        self.hint = hint
        self.category = category
        self.difficulty = difficulty
        self.embedding = embedding

    def to_dict(self) -> dict:
        d = {
            "id": self.id, "word": self.word, "hint": self.hint,
            "category": self.category, "difficulty": self.difficulty,
        }
        if self.embedding:
            d["embedding"] = self.embedding
        return d


class Round:
    def __init__(self, id: int, word_id: int, word: str, hint: str,
                 status: str = "waiting", started_at: Optional[str] = None,
                 ended_at: Optional[str] = None, duration: int = 60):
        self.id = id
        self.word_id = word_id
        self.word = word
        self.hint = hint
        self.status = status
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration = duration

    def to_dict(self) -> dict:
        return {
            "id": self.id, "wordId": self.word_id, "word": self.word,
            "hint": self.hint, "status": self.status,
            "startedAt": self.started_at, "endedAt": self.ended_at,
            "duration": self.duration,
        }


# 全局状态
_words: list[Word] = []
_rounds: list[Round] = []
_guesses: list[dict] = []
_next_word_id = 1
_next_round_id = 1


def _data_dir() -> Path:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DATA_DIR


def _load_words() -> None:
    global _words, _next_word_id
    words_file = _data_dir() / "words.json"
    if words_file.exists():
        try:
            data = json.loads(words_file.read_text(encoding="utf-8"))
            _words = [
                Word(
                    id=w["id"], word=w["word"], hint=w["hint"],
                    category=w["category"], difficulty=w["difficulty"],
                    embedding=w.get("embedding"),
                )
                for w in data.get("words", [])
            ]
            _next_word_id = data.get("nextId", max((w.id for w in _words), default=0) + 1)
        except Exception as e:
            logger.error(f"加载词库失败: {e}")
            _words = []


def _save_words() -> None:
    words_file = _data_dir() / "words.json"
    data = {
        "words": [w.to_dict() for w in _words],
        "nextId": _next_word_id,
    }
    words_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_guesses() -> None:
    global _guesses
    guesses_file = _data_dir() / "guesses.json"
    if guesses_file.exists():
        try:
            _guesses = json.loads(guesses_file.read_text(encoding="utf-8"))
        except Exception:
            _guesses = []


def _save_guesses() -> None:
    guesses_file = _data_dir() / "guesses.json"
    guesses_file.write_text(json.dumps(_guesses, ensure_ascii=False), encoding="utf-8")


def init_game() -> None:
    """初始化游戏"""
    _load_words()
    _load_guesses()
    load_cached_embeddings([w.to_dict() for w in _words])
    logger.info(f"游戏初始化完成，词库 {_len_words()} 个词")


def _len_words() -> int:
    return len(_words)


async def create_round(
    word_id: Optional[int] = None,
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    duration: Optional[int] = None,
) -> Round:
    """创建新一轮"""
    global _next_round_id
    dur = duration or settings.ROUND_DURATION

    if word_id:
        word = next((w for w in _words if w.id == word_id), None)
        if not word:
            raise ValueError(f"词 ID {word_id} 不存在")
    else:
        candidates = _words
        if category:
            candidates = [w for w in candidates if w.category == category]
        if difficulty:
            candidates = [w for w in candidates if w.difficulty == difficulty]
        if not candidates:
            raise ValueError("词库中没有符合条件的词")
        word = random.choice(candidates)

    # 预计算 embedding
    if not word.embedding:
        try:
            word.embedding = await get_embedding(word.word)
            _save_words()
        except Exception as e:
            logger.error(f"预计算 embedding 失败: {e}")

    r = Round(
        id=_next_round_id,
        word_id=word.id,
        word=word.word,
        hint=word.hint,
        duration=dur,
    )
    _next_round_id += 1
    _rounds.append(r)
    return r


def start_round(round_id: int) -> Round:
    """开始一轮"""
    r = next((r for r in _rounds if r.id == round_id), None)
    if not r:
        raise ValueError("轮次不存在")
    r.status = "active"
    r.started_at = datetime.now(timezone.utc).isoformat()
    return r


def end_round(round_id: int) -> Round:
    """结束一轮"""
    r = next((r for r in _rounds if r.id == round_id), None)
    if not r:
        raise ValueError("轮次不存在")
    r.status = "finished"
    r.ended_at = datetime.now(timezone.utc).isoformat()
    return r


def get_round(round_id: int) -> Optional[Round]:
    return next((r for r in _rounds if r.id == round_id), None)


def get_active_round() -> Optional[Round]:
    for r in reversed(_rounds):
        if r.status == "active":
            return r
    return None


async def process_guess(
    round_id: int,
    user_id: str,
    username: str,
    avatar: str,
    guess_text: str,
) -> dict:
    """处理猜测"""
    max_guesses = settings.MAX_GUESSES_PER_ROUND

    count = get_guess_count(round_id, user_id)
    if count >= max_guesses:
        return {
            "similarity": 0, "isCorrect": False, "rank": -1,
            "message": f"本轮已用完 {max_guesses} 次猜测机会",
        }

    r = get_round(round_id)
    if not r or r.status != "active":
        return {"similarity": 0, "isCorrect": False, "rank": -1, "message": "当前没有进行中的游戏"}

    answer_word = next((w for w in _words if w.id == r.word_id), None)
    answer_embedding = answer_word.embedding if answer_word else None

    similarity = await calculate_similarity(guess_text, r.word, answer_embedding)
    correct = is_correct(similarity)

    increment_guess_count(round_id, user_id)
    ts = int(time.time() * 1000)

    entry = LeaderboardEntry(
        rank=round_id, user_id=user_id, username=username,
        avatar=avatar, guess_text=guess_text, score=similarity, timestamp=ts,
    )
    add_guess(entry)

    record = {
        "roundId": round_id, "userId": user_id, "username": username,
        "avatar": avatar, "guessText": guess_text, "similarity": similarity,
        "isCorrect": correct, "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    _guesses.append(record)
    _save_guesses()

    leaderboard = get_leaderboard(round_id)
    user_rank = next((i + 1 for i, e in enumerate(leaderboard) if e["userId"] == user_id), len(leaderboard))

    return {
        "similarity": round(similarity, 3),
        "isCorrect": correct,
        "rank": user_rank if user_rank > 0 else len(leaderboard),
        "message": (
            f"猜对了！相似度 {similarity * 100:.1f}%" if correct
            else f"相似度 {similarity * 100:.1f}%，继续加油！"
        ),
    }


def list_words(category: Optional[str] = None, difficulty: Optional[int] = None) -> list[dict]:
    result = _words
    if category:
        result = [w for w in result if w.category == category]
    if difficulty:
        result = [w for w in result if w.difficulty == difficulty]
    return [{"id": w.id, "word": w.word, "hint": w.hint, "category": w.category, "difficulty": w.difficulty} for w in result]
