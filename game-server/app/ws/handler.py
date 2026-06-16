"""
Socket.IO 事件处理器
管理客户端连接、消息路由、定时广播排行榜
"""
import asyncio
import logging
from typing import Optional

import socketio

from app.services.game_service import (
    get_active_round, process_guess, get_round,
    start_round, end_round, create_round,
)
from app.services.rank_service import get_leaderboard, get_guess_count

logger = logging.getLogger(__name__)

# 已连接客户端
_clients: dict[str, dict] = {}  # sid -> {userId, username, avatar, role}

# 定时器任务
_leaderboard_task: Optional[asyncio.Task] = None
_round_timer_task: Optional[asyncio.Task] = None

# Socket.IO 实例（在 main.py 中设置）
_sio: Optional[socketio.AsyncServer] = None


def set_sio(sio: socketio.AsyncServer) -> None:
    global _sio
    _sio = sio


def _emit(sid: str, event: str, data: dict) -> None:
    """发送消息给单个客户端"""
    if _sio:
        asyncio.create_task(_sio.emit(event, data, room=sid))


def _broadcast(event: str, data: dict) -> None:
    """广播给所有已注册客户端"""
    if _sio:
        for sid in _clients:
            asyncio.create_task(_sio.emit(event, data, room=sid))


async def _broadcast_leaderboard(round_id: int) -> None:
    """广播排行榜"""
    leaderboard = get_leaderboard(round_id)
    _broadcast("message", {
        "type": "leaderboard",
        "data": {
            "roundId": round_id,
            "entries": leaderboard[:50],
            "totalParticipants": len(leaderboard),
        },
    })


async def _leaderboard_loop(round_id: int) -> None:
    """定时广播排行榜（每3秒）"""
    try:
        while True:
            await asyncio.sleep(3)
            await _broadcast_leaderboard(round_id)
    except asyncio.CancelledError:
        pass


async def _auto_end_round(round_id: int, duration: int) -> None:
    """自动结束轮次"""
    try:
        await asyncio.sleep(duration)
        await _finish_round(round_id)
    except asyncio.CancelledError:
        pass


async def _finish_round(round_id: int) -> None:
    """结束轮次并广播"""
    global _leaderboard_task, _round_timer_task

    if _leaderboard_task and not _leaderboard_task.done():
        _leaderboard_task.cancel()
        _leaderboard_task = None

    if _round_timer_task and not _round_timer_task.done():
        _round_timer_task.cancel()
        _round_timer_task = None

    r = get_round(round_id)
    if not r or r.status != "active":
        return

    ended = end_round(round_id)
    leaderboard = get_leaderboard(round_id)

    _broadcast("message", {
        "type": "round_end",
        "data": {
            "roundId": ended.id,
            "answer": ended.word,
            "hint": ended.hint,
            "leaderboard": leaderboard[:10],
            "totalParticipants": len(leaderboard),
        },
    })
    logger.info(f"轮次 {round_id} 结束，答案: {ended.word}，参与人数: {len(leaderboard)}")


def register_handlers(sio: socketio.AsyncServer) -> None:
    """注册 Socket.IO 事件处理器"""
    set_sio(sio)

    @sio.event
    async def connect(sid: str, environ: dict) -> None:
        logger.info(f"新连接: {sid}")

    @sio.event
    async def disconnect(sid: str) -> None:
        client = _clients.pop(sid, None)
        if client:
            logger.info(f"断开: {client.get('username', sid)}")

    @sio.event
    async def register(sid: str, data: dict) -> None:
        _clients[sid] = {
            "userId": data.get("userId", ""),
            "username": data.get("username", ""),
            "avatar": data.get("avatar", ""),
            "role": data.get("role", "viewer"),
        }
        logger.info(f"用户注册: {data.get('username')} ({data.get('role')})")

        # 发送当前活跃轮次
        active = get_active_round()
        if active:
            _emit(sid, "message", {
                "type": "new_round",
                "data": {
                    "roundId": active.id,
                    "hint": active.hint,
                    "duration": active.duration,
                    "startedAt": active.started_at,
                },
            })

    @sio.event
    async def message(sid: str, msg: dict) -> None:
        global _leaderboard_task, _round_timer_task

        client = _clients.get(sid)
        if not client:
            return

        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        try:
            if msg_type == "guess":
                await _handle_guess(sid, client, data)
            elif msg_type == "start_round":
                await _handle_start_round(client, data)
            elif msg_type == "end_round":
                await _handle_end_round(client, data)
            else:
                _emit(sid, "message", {"type": "error", "data": {"message": f"未知消息类型: {msg_type}"}})
        except Exception as e:
            logger.error(f"处理消息错误: {e}", exc_info=True)
            _emit(sid, "message", {"type": "error", "data": {"message": "服务器内部错误"}})

    async def _handle_guess(sid: str, client: dict, data: dict) -> None:
        round_id = data.get("roundId")
        text = (data.get("text") or data.get("guessText") or "").strip()

        if not text:
            _emit(sid, "message", {"type": "error", "data": {"message": "请输入猜测内容"}})
            return
        if len(text) > 50:
            _emit(sid, "message", {"type": "error", "data": {"message": "输入过长，最多50字"}})
            return

        r = get_round(round_id) if round_id else None
        if not r or r.status != "active":
            _emit(sid, "message", {"type": "error", "data": {"message": "当前没有进行中的游戏"}})
            return

        result = await process_guess(
            round_id, client["userId"], client["username"],
            client["avatar"], text,
        )

        _emit(sid, "message", {
            "type": "guess_result",
            "data": {
                "roundId": round_id,
                "text": text,
                "similarity": result["similarity"],
                "isCorrect": result["isCorrect"],
                "rank": result["rank"],
                "message": result["message"],
            },
        })

        await _broadcast_leaderboard(round_id)

    async def _handle_start_round(client: dict, data: dict) -> None:
        global _leaderboard_task, _round_timer_task

        if client["role"] != "host":
            _emit(None, "message", {"type": "error", "data": {"message": "只有主播可以开始游戏"}})
            return

        active = get_active_round()
        if active:
            return

        r = await create_round(
            word_id=data.get("wordId"),
            category=data.get("category"),
            difficulty=data.get("difficulty"),
            duration=data.get("duration"),
        )
        started = start_round(r.id)

        _broadcast("message", {
            "type": "new_round",
            "data": {
                "roundId": started.id,
                "hint": started.hint,
                "duration": started.duration,
                "startedAt": started.started_at,
            },
        })

        # 启动排行榜广播
        if _leaderboard_task and not _leaderboard_task.done():
            _leaderboard_task.cancel()
        _leaderboard_task = asyncio.create_task(_leaderboard_loop(started.id))

        # 启动自动结束倒计时
        if _round_timer_task and not _round_timer_task.done():
            _round_timer_task.cancel()
        _round_timer_task = asyncio.create_task(_auto_end_round(started.id, started.duration))

        logger.info(f"轮次 {started.id} 开始，答案: {started.word}")

    async def _handle_end_round(client: dict, data: dict) -> None:
        if client["role"] != "host":
            return
        round_id = data.get("roundId")
        if round_id:
            await _finish_round(round_id)
