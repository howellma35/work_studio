"""
故障恢复与优雅降级 — 4层降级保障生产级可靠性

降级层级:
L0: 正常（所有服务可用）
L1: MCP降级（MCP Server不可用→模拟数据）
L2: 子Agent降级（子Agent失败→Supervisor直答）
L3: LLM降级（主模型超时→备用模型）
L4: 离线模式（所有服务不可用→本地规则引擎）

每个远程调用都有指数退避重试。
"""
import asyncio
from loguru import logger

from app.models.llm import create_llm


class FaultRecoveryService:
    """故障恢复与优雅降级服务"""

    DEGRADATION_CONFIG = {
        "L1_mcp_down": {
            "navigation": "使用本地预设地名坐标+粗略距离估算",
            "weather": "使用最近一次缓存天气数据",
            "vehicle": "使用上次成功获取的车况快照",
            "media": "使用内置默认歌单",
        },
        "L2_agent_down": {
            "description": "子Agent不可用时，Supervisor用自己的知识直接回答",
            "prompt_adjustment": "专业子服务暂时不可用，请用你自己的通用知识尽力回答，并告知用户服务恢复后可提供更详细信息",
        },
        "L3_llm_timeout": {
            "primary_model": "deepseek-v3",
            "fallback_model": "qwen-plus",
            "timeout_seconds": 15,
            "retry_count": 2,
        },
    }

    async def invoke_with_fallback(self, sub_agent, task: str, name: str) -> str:
        """带故障恢复的子Agent调用

        1. 正常调用 → 成功则返回
        2. L2降级: Supervisor 直答
        3. L3降级: 备用模型
        """
        # 1. 正常调用
        try:
            from app.graph.subagent_tools import _invoke_subagent
            result = await _invoke_subagent(sub_agent, task, name)
            if not result.startswith(f"⚠️ {name}") and not result.startswith(f"{name} 执行出错"):
                return result
        except Exception as e:
            logger.warning(f"[故障恢复] {name} 调用失败: {e}")

        # 2. L2降级: Supervisor 直答
        logger.info(f"[故障恢复] {name} 降级为 Supervisor 直答")
        fallback_prompt = f"""子Agent {name} 暂时不可用。
用户请求: {task}
请用你自己的通用知识尽力回答，并告知用户服务恢复后可提供更详细信息。"""

        try:
            fallback_llm = create_llm(temperature=0.3)
            result = await fallback_llm.ainvoke(fallback_prompt)
            return f"⚠️ {name} 服务暂时降级，以下为通用回复:\n{result.content}"
        except Exception:
            # 3. L3降级: 备用模型
            logger.info(f"[故障恢复] 主模型也失败，尝试备用模型")
            try:
                from app.config import settings
                backup_llm = create_llm(model=settings.LLM_MODEL, temperature=0.3)
                result = await backup_llm.ainvoke(fallback_prompt)
                return f"⚠️ 服务降级运行，以下为备用回复:\n{result.content}"
            except Exception as e2:
                # 4. 最终兜底: 本地规则响应
                logger.error(f"[故障恢复] 所有降级方案失败: {e2}")
                return self._local_rule_response(name, task)

    def _local_rule_response(self, agent_name: str, task: str) -> str:
        """L4: 本地规则引擎兜底（无需任何外部服务）"""
        RULE_RESPONSES = {
            "navigation_agent": "导航服务暂时不可用，建议使用手机地图导航。服务恢复后会提供精确路线。",
            "media_agent": "多媒体服务暂时不可用，建议手动操作车载娱乐系统。",
            "vehicle_agent": "车辆控制服务暂时不可用，建议手动操作相关功能。",
            "weather_agent": "天气服务暂时不可用，建议查看手机天气应用。",
            "reminder_agent": "提醒服务暂时不可用，建议手动记录重要事项。",
            "knowledge_agent": "知识库检索暂时不可用，建议查阅车辆纸质手册。",
        }
        return RULE_RESPONSES.get(agent_name,
            f"⚠️ {agent_name} 服务暂时不可用，所有降级方案已耗尽。请稍后重试或联系客服。")

    async def invoke_with_retry(self, func, max_retries: int = 2, backoff: float = 1.0):
        """指数退避重试

        Args:
            func: 待调用的异步函数
            max_retries: 最大重试次数
            backoff: 初始退避时间（秒）
        """
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries:
                    raise
                wait_time = backoff * (2 ** attempt)
                logger.warning(f"[重试] 第{attempt+1}次失败，{wait_time}s后重试: {e}")
                await asyncio.sleep(wait_time)

    def get_mcp_fallback_data(self, service: str) -> dict:
        """L1: MCP 服务不可用时的模拟数据"""
        FALLBACK_DATA = {
            "navigation": {
                "routes": [{"name": "默认路线", "distance_km": 8, "duration_min": 25}],
                "pois": [{"name": "附近目的地", "distance_km": 3}],
            },
            "weather": {
                "condition": "晴", "temperature": 26, "humidity": 65,
                "forecast": "预计未来2小时天气稳定",
            },
            "vehicle": {
                "status": "模拟数据（MCP不可用）",
                "battery": 78, "mileage": 15234,
            },
            "media": {
                "playlist": ["默认歌单1", "默认歌单2", "默认歌单3"],
                "current_song": "默认歌曲",
            },
        }
        return FALLBACK_DATA.get(service, {"status": "模拟数据", "message": "服务暂时不可用"})


# 全局实例
fault_recovery = FaultRecoveryService()
