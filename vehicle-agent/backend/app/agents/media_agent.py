"""
多媒体子Agent
负责音乐播放控制、音量调节、歌单管理
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from app.models.llm import create_llm

MEDIA_PROMPT = """\
你是 AutoMind 的多媒体专家 Agent，专注于音乐播放和娱乐控制。

你的能力：
- 播放/暂停音乐
- 切歌、播放指定歌曲
- 调节音量
- 查看播放列表

工作规则：
1. 用户说"放点音乐"时，主动从播放列表选择
2. 调节音量时确认当前音量值
3. 适合车机语音播报，回复简洁
4. 如遇歌曲不存在，推荐相似歌曲

请以自然、亲切的语气回复，模拟真实车机助手的体验。"""


def create_media_agent(tools: list[BaseTool]):
    """创建多媒体子Agent，绑定播放器相关工具"""
    media_tools = [
        t for t in tools
        if any(kw in t.name for kw in ["music", "song", "volume", "playlist"])
    ]
    return create_agent(
        model=create_llm(temperature=0.3),
        tools=media_tools,
        name="media_agent",
        system_prompt=MEDIA_PROMPT,
    )
