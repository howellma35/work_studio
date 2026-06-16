"""
排行榜服务
使用内存实现（轻量方案，无需 Redis）
"""
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    rank: int
    user_id: str
    username: str
    avatar: str
    guess_text: str
    score: float
    timestamp: int


# 内存存储
_leaderboards: dict[int, list[dict]] = {}  # roundId -> [{score, member}]
_guess_counts: dict[str, int] = {}  # "roundId:userId" -> count


def add_guess(entry: LeaderboardEntry) -> None:
    """提交猜测到排行榜"""
    round_id = entry.rank  # rank 字段实际是 roundId
    score = entry.score * 1_000_000 - (entry.timestamp % 1_000_000) / 1_000_000
    member = json.dumps({
        "u": entry.user_id,
        "n": entry.username,
        "a": entry.avatar,
        "t": entry.guess_text,
        "s": entry.score,
        "ts": entry.timestamp,
    }, ensure_ascii=False)

    if round_id not in _leaderboards:
        _leaderboards[round_id] = []

    _leaderboards[round_id].append({"score": score, "member": member})
    _leaderboards[round_id].sort(key=lambda x: x["score"], reverse=True)


def get_leaderboard(round_id: int, top_n: int = 50) -> list[dict]:
    """获取排行榜"""
    items = _leaderboards.get(round_id, [])[:top_n]
    result = []
    for idx, item in enumerate(items):
        data = json.loads(item["member"])
        result.append({
            "rank": idx + 1,
            "userId": data["u"],
            "username": data["n"],
            "avatar": data["a"],
            "guessText": data["t"],
            "score": data["s"],
            "timestamp": data["ts"],
        })
    return result


def get_guess_count(round_id: int, user_id: str) -> int:
    """获取用户本轮猜测次数"""
    return _guess_counts.get(f"{round_id}:{user_id}", 0)


def increment_guess_count(round_id: int, user_id: str) -> None:
    """增加猜测次数"""
    key = f"{round_id}:{user_id}"
    _guess_counts[key] = _guess_counts.get(key, 0) + 1


def clear_leaderboard(round_id: int) -> None:
    """清除某轮排行榜"""
    _leaderboards.pop(round_id, None)
