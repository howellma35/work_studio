"""
流式语音交互管道 — ASR → VAD → Agent → TTS 端到端

架构:
┌─────┐   ┌─────┐   ┌─────────┐   ┌─────┐
│ ASR │ → │ VAD │ → │  Agent  │ → │ TTS │
│实时  │   │检测  │   │ 流式处理 │   │实时  │
│转写  │   │完成  │   │         │   │播报  │
└─────┘   └─────┘   └─────────┘   └─────┘

ASR: 百炼 Paraformer / Whisper
VAD: Silero VAD (轻量端侧模型，800ms沉默检测)
TTS: 百炼 CosyVoice / Edge TTS

核心设计: "边想边说"——Agent 流式回复的每个文字块立即送 TTS 合成
"""
import asyncio
from loguru import logger

from app.models.llm import create_llm


class VADDetector:
    """语音活动检测（Silero VAD 模拟）

    真实部署使用 Silero VAD 模型（torch hub），
    这里用简化版本: 基于 PCM 能量检测。
    """

    def __init__(self, silence_threshold_ms: int = 800, energy_threshold: float = 0.02):
        self.silence_threshold_ms = silence_threshold_ms
        self.energy_threshold = energy_threshold

    async def wait_for_completion(self, audio_stream) -> bytes:
        """等待用户说完（沉默超过阈值视为说完）

        Args:
            audio_stream: 音频帧异步迭代器

        Returns:
            完整语音段 bytes
        """
        buffer = bytearray()
        silence_duration = 0.0

        async for chunk in audio_stream:
            buffer.extend(chunk)
            is_speech = self._detect_speech_simple(chunk)
            if not is_speech:
                # 假设每帧约 100ms
                silence_duration += 0.1
                if silence_duration > self.silence_threshold_ms / 1000:
                    logger.info("[VAD] 检测到语音结束，沉默 {:.1f}s".format(silence_duration))
                    break
            else:
                silence_duration = 0.0

        return bytes(buffer)

    def _detect_speech_simple(self, chunk: bytes) -> bool:
        """简化版语音检测（基于 PCM 能量阈值）

        真实版用 Silero VAD 模型
        """
        if len(chunk) < 2:
            return False
        # 计算简单能量（16-bit PCM）
        energy = sum(abs(int.from_bytes(chunk[i:i+2], 'little', signed=True))
                      for i in range(0, min(len(chunk), 320), 2)) / max(1, len(chunk) // 2)
        return energy > self.energy_threshold * 1000


class ASRService:
    """语音转文字服务

    真实部署使用百炼 Paraformer 或 Whisper
    """

    async def transcribe(self, audio_bytes: bytes) -> str:
        """音频转文字

        Args:
            audio_bytes: PCM/WAV 音频数据

        Returns:
            转写文本
        """
        # 模拟 ASR（真实实现调用百炼 Paraformer API）
        logger.info(f"[ASR] 接收音频 {len(audio_bytes)} bytes，模拟转写")
        # 这里返回模拟结果，真实实现会调用 ASR API
        return "（语音转写结果 — 需接入百炼 Paraformer API）"


class TTSService:
    """文字转语音服务

    真实部署使用百炼 CosyVoice 或 Edge TTS
    """

    async def synthesize_chunk(self, text_chunk: str) -> bytes:
        """流式合成语音片段（边生成边播报）

        Args:
            text_chunk: Agent 回复的一个文字片段

        Returns:
            音频 bytes（PCM 或压缩格式）
        """
        # 模拟 TTS（真实实现调用百炼 CosyVoice 或 Edge TTS）
        logger.debug(f"[TTS] 合成片段: {text_chunk[:30]}")
        return b""  # 模拟返回空音频


class VoicePipeline:
    """端到端语音交互管道"""

    def __init__(self):
        self._asr = ASRService()
        self._tts = TTSService()
        self._vad = VADDetector()

    async def process_voice_input(self, audio_stream, agent_graph=None) -> bytes:
        """完整语音处理管道

        1. VAD 检测用户说完 → 截取完整语音段
        2. ASR 转写为文字
        3. Agent 流式处理文字 → 流式文字输出
        4. TTS 流式合成语音 → 实时播报

        Returns:
            完整语音播报 bytes
        """
        # Step 1-2: VAD + ASR
        complete_audio = await self._vad.wait_for_completion(audio_stream)
        text = await self._asr.transcribe(complete_audio)
        logger.info(f"[语音管道] ASR转写: {text}")

        # Step 3: Agent 处理（如果提供了 graph）
        if agent_graph:
            from langchain_core.messages import HumanMessage
            result = await agent_graph.ainvoke({"messages": [HumanMessage(content=text)]})
            # 提取回复
            messages = result.get("messages", [])
            agent_text = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.type == "ai":
                    agent_text = msg.content
                    break
        else:
            agent_text = f"收到语音输入: {text}"

        # Step 4: TTS 合成
        audio_output = await self._tts.synthesize_chunk(agent_text)

        logger.info(f"[语音管道] 完整处理完成，回复: {agent_text[:50]}")
        return audio_output


# 全局实例
voice_pipeline = VoicePipeline()
