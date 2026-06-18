"""
MCP 多媒体工具集
模拟音乐播放器，提供播放控制能力
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MediaTools")

# 模拟播放器状态（内存中维护）
_player_state = {
    "is_playing": False,
    "current_song": None,
    "current_artist": None,
    "volume": 30,
    "playlist": [
        {"title": "稻香", "artist": "周杰伦"},
        {"title": "七里香", "artist": "周杰伦"},
        {"title": "夜曲", "artist": "周杰伦"},
        {"title": "晴天", "artist": "孙燕姿"},
        {"title": "遇见", "artist": "孙燕姿"},
    ],
    "current_index": 0,
}


@mcp.tool()
def play_music(song_name: str = "", artist: str = "") -> dict:
    """
    播放音乐

    Args:
        song_name: 歌曲名（可选，不指定则继续播放列表）
        artist: 歌手名（可选）

    Returns:
        当前播放状态
    """
    if song_name:
        _player_state["current_song"] = song_name
        _player_state["current_artist"] = artist or "未知歌手"
        _player_state["is_playing"] = True
        return {"status": "ok", "action": "play", "song": song_name, "artist": artist}
    else:
        current = _player_state["playlist"][_player_state["current_index"]]
        _player_state["is_playing"] = True
        _player_state["current_song"] = current["title"]
        _player_state["current_artist"] = current["artist"]
        return {"status": "ok", "action": "resume", "song": current["title"], "artist": current["artist"]}


@mcp.tool()
def pause_music() -> dict:
    """暂停当前播放"""
    _player_state["is_playing"] = False
    return {"status": "ok", "action": "pause"}


@mcp.tool()
def next_song() -> dict:
    """播放下一首"""
    _player_state["current_index"] = (_player_state["current_index"] + 1) % len(_player_state["playlist"])
    current = _player_state["playlist"][_player_state["current_index"]]
    _player_state["current_song"] = current["title"]
    _player_state["current_artist"] = current["artist"]
    _player_state["is_playing"] = True
    return {"status": "ok", "action": "next", "song": current["title"], "artist": current["artist"]}


@mcp.tool()
def set_volume(level: int) -> dict:
    """
    调节音量

    Args:
        level: 音量级别 0-100

    Returns:
        当前音量
    """
    level = max(0, min(100, level))
    _player_state["volume"] = level
    return {"status": "ok", "action": "volume", "volume": level}


@mcp.tool()
def get_playlist() -> dict:
    """获取当前播放列表"""
    return {
        "status": "ok",
        "is_playing": _player_state["is_playing"],
        "current_song": _player_state["current_song"],
        "current_artist": _player_state["current_artist"],
        "volume": _player_state["volume"],
        "playlist": _player_state["playlist"],
        "current_index": _player_state["current_index"],
    }
