"""
并行 Agent 编排器 — asyncio.gather 并行独立子任务

核心设计:
- 复合请求时，任务依赖分析器判断哪些子任务可独立执行
- 独立任务用 asyncio.gather 并行调用（延迟从 sum 降到 max）
- 依赖任务仍串行（如"导航后找停车场"需先拿到导航终点）

集成方式:
- 在 Supervisor routing_description 中添加并行调用规则
- 在 subagent_tools.py 的 @tool wrapper 中支持并行 invoke
"""
import asyncio
from langchain_core.messages import HumanMessage
from loguru import logger


# ===== 任务依赖关系映射 =====
# key: (agent_a, agent_b) → True 表示 b 依赖 a 的结果
TASK_DEPENDENCY_MAP = {
    # POI搜索依赖导航终点
    ("navigation_agent", "search_poi_after_nav"): True,
    # 以下组合是独立的，可以并行
    ("navigation_agent", "weather_agent"): False,
    ("navigation_agent", "media_agent"): False,
    ("navigation_agent", "vehicle_agent"): False,
    ("weather_agent", "media_agent"): False,
    ("weather_agent", "vehicle_agent"): False,
    ("media_agent", "vehicle_agent"): False,
    ("reminder_agent", "weather_agent"): False,
    ("reminder_agent", "media_agent"): False,
}


class ParallelOrchestrator:
    """并行子Agent编排器"""

    async def dispatch_parallel(
        self,
        tasks: list[dict],
        agents: dict,
    ) -> list[str]:
        """并行调用多个独立子Agent

        Args:
            tasks: [{"agent": "navigation_agent", "task": "..."}, ...]
            agents: 子Agent实例字典

        Returns:
            各子Agent返回结果列表（异常时返回错误消息）
        """
        async_calls = []
        for task_spec in tasks:
            agent_name = task_spec["agent"]
            task_desc = task_spec["task"]
            agent_instance = agents.get(agent_name)
            if agent_instance is None:
                async_calls.append(self._fallback_result(agent_name, task_desc, "Agent未找到"))
                continue

            from app.graph.subagent_tools import _invoke_subagent
            async_calls.append(_invoke_subagent(agent_instance, task_desc, agent_name))

        # asyncio.gather 并行执行
        results = await asyncio.gather(*async_calls, return_exceptions=True)

        # 处理异常
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = tasks[i]["agent"]
                logger.warning(f"[并行编排] {agent_name} 执行失败: {result}")
                processed.append(f"⚠️ {agent_name} 执行出错: {result}")
            else:
                processed.append(result)

        return processed

    def analyze_task_dependencies(self, agent_names: list[str]) -> dict:
        """分析任务依赖关系，决定并行/串行策略

        Args:
            agent_names: 需要调用的Agent名称列表

        Returns:
            {
                "parallel_groups": [[独立Agent组], ...],
                "sequential_chain": [需串行的Agent列表],
                "strategy": "parallel" | "mixed" | "sequential"
            }
        """
        if len(agent_names) <= 1:
            return {
                "parallel_groups": [agent_names],
                "sequential_chain": [],
                "strategy": "sequential",
            }

        # 检查是否有依赖关系
        has_dependency = False
        for a in agent_names:
            for b in agent_names:
                if TASK_DEPENDENCY_MAP.get((a, b), False):
                    has_dependency = True

        if not has_dependency:
            # 全部独立 → 一次性并行
            return {
                "parallel_groups": [agent_names],
                "sequential_chain": [],
                "strategy": "parallel",
            }
        else:
            # 有依赖 → 串行+并行混合
            return {
                "parallel_groups": [agent_names],
                "sequential_chain": agent_names,
                "strategy": "mixed",
            }


# 全局实例
parallel_orchestrator = ParallelOrchestrator()

# ===== Supervisor 并行路由描述补充 =====
PARALLEL_ROUTING_ADDON = """\

## 并行调用规则（重要）
- 复合请求中，如果多个子任务互相独立，可以在同一轮回复中同时调用多个子Agent工具
- 例："导航去公司并查天气" → 同时调用 navigation_agent 和 weather_agent
- 例："开空调并放点音乐" → 同时调用 vehicle_agent 和 media_agent
- 有依赖关系的任务必须串行："导航去公司然后找停车场" → 先导航，拿到终点后再搜POI
- 并行调用时，每个子Agent仍然是独立的 @tool 调用，系统会自动并行执行"""
