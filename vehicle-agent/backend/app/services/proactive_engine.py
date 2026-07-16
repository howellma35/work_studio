"""
场景感知主动推荐引擎 — 从被动响应升级为主动推送

架构:
┌─────────────────────────────────────────────┐
│  APScheduler (定时触发)                       │
│    ├─ 每60s: 检查车况异常                      │
│    ├─ 每300s: 天气/路况变化检测                  │
│    ├─ 每600s: 长途驾驶疲劳提醒                  │
│    └──────────────────────────────────────────│
│  事件驱动 (WebSocket 推送)                     │
│    ├─ 电池<20% → 推送充电建议                  │
│    ├─ 蛋压异常 → 推送安全提醒                  │
│    ├─ 进入高速 → 切换场景+推送路况              │
└─────────────────────────────────────────────┘

推送通道:
- SSE via /api/vehicle/proactive (HTTP 长连接)
- 未来可接入 WebSocket 或 AG-UI push

规则有 cooldown 防重复推送，优先级分级决定推送形式。
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any

from loguru import logger

from app.graph.scene_config import DrivingScene


class ProactiveRule:
    """主动推荐规则"""
    def __init__(
        self,
        id: str,
        trigger_field: str,
        trigger_op: str,
        trigger_value: Any,
        agent: str,
        task: str,
        priority: str = "medium",
        cooldown: int = 600,
        condition_field: str = "",
        condition_op: str = "",
        condition_value: Any = None,
    ):
        self.id = id
        self.trigger_field = trigger_field
        self.trigger_op = trigger_op
        self.trigger_value = trigger_value
        self.agent = agent
        self.task = task
        self.priority = priority
        self.cooldown = cooldown  # 秒，防重复推送
        self.condition_field = condition_field
        self.condition_op = condition_op
        self.condition_value = condition_value


# ===== 主动推荐规则库 =====
DEFAULT_RULES = [
    ProactiveRule(
        id="low_battery",
        trigger_field="battery",
        trigger_op="lt",
        trigger_value=20,
        agent="navigation_agent",
        task="搜索附近充电站并推荐最近的3个",
        priority="high",
        cooldown=600,  # 10分钟不重复推送
    ),
    ProactiveRule(
        id="low_battery_warning",
        trigger_field="battery",
        trigger_op="lt",
        trigger_value=30,
        agent="navigation_agent",
        task="提醒用户电量偏低，建议规划充电路线",
        priority="medium",
        cooldown=1800,
    ),
    ProactiveRule(
        id="tire_pressure_alert",
        trigger_field="tire_pressure_front",
        trigger_op="lt",
        trigger_value=2.3,
        agent="vehicle_agent",
        task="提醒用户胎压偏低，建议检查轮胎",
        priority="high",
        cooldown=1800,
    ),
    ProactiveRule(
        id="engine_temp_high",
        trigger_field="engine_temp",
        trigger_op="gt",
        trigger_value=105,
        agent="vehicle_agent",
        task="提醒用户发动机温度偏高，建议停车检查散热系统",
        priority="high",
        cooldown=600,
    ),
    ProactiveRule(
        id="rain_alert",
        trigger_field="weather_condition",
        trigger_op="contains",
        trigger_value="雨",
        agent="weather_agent",
        task="提醒用户带雨具，建议降低车速，查询是否有积水路段",
        priority="medium",
        cooldown=1800,
    ),
    ProactiveRule(
        id="fatigue_reminder",
        trigger_field="driving_duration_min",
        trigger_op="gt",
        trigger_value=120,
        agent="navigation_agent",
        task="提醒用户休息，搜索前方最近服务区",
        priority="high",
        cooldown=1800,
    ),
    ProactiveRule(
        id="morning_departure",
        trigger_field="time",
        trigger_op="between",
        trigger_value=["7:00", "8:30"],
        agent="weather_agent",
        task="播报今日天气+通勤路况，给出出行建议",
        priority="low",
        cooldown=3600,
        condition_field="scene",
        condition_op="eq",
        condition_value="parked",
    ),
    ProactiveRule(
        id="highway_enter",
        trigger_field="scene",
        trigger_op="eq",
        trigger_value="highway",
        agent="navigation_agent",
        task="自动推送前方路况信息和最近服务区距离",
        priority="medium",
        cooldown=300,
    ),
]


class ProactiveEngine:
    """场景感知主动推荐引擎"""

    def __init__(self, rules: list[ProactiveRule] = None):
        self._rules = rules or DEFAULT_RULES
        self._push_history: dict[str, float] = {}  # rule_id → last_push_time
        self._subscribers: list = []  # SSE 推送订阅者
        self._vehicle_status: dict = {}  # 当前车况快照
        self._weather_data: dict = {}  # 当前天气数据
        self._scene: str = "idle"  # 当前驾驶场景
        self._driving_start_time: float = 0  # 驾驶开始时间
        self._running = False

    def update_vehicle_status(self, status: dict):
        """更新车况数据（来自 MCP vehicle_tools 或 WebSocket 推送）"""
        old_speed = self._vehicle_status.get("speed", 0)
        new_speed = status.get("speed", 0)

        # 检测驾驶开始（从静止到行驶）
        if old_speed == 0 and new_speed > 0:
            self._driving_start_time = time.time()
            logger.info(f"[主动推荐] 驾驶开始记录: speed={new_speed}")

        self._vehicle_status = status

    def update_weather(self, weather: dict):
        """更新天气数据"""
        self._weather_data = weather

    def update_scene(self, scene: str):
        """更新驾驶场景"""
        self._scene = scene

    def _get_field_value(self, field: str) -> Any:
        """从车况/天气/时间数据中获取字段值"""
        # 车况字段
        if field in self._vehicle_status:
            return self._vehicle_status[field]
        # 胎压特殊处理
        if field == "tire_pressure_front":
            tp = self._vehicle_status.get("tire_pressure", {})
            return tp.get("front", 2.9)
        # 天气字段
        if field == "weather_condition":
            return self._weather_data.get("condition", "晴")
        # 场景字段
        if field == "scene":
            return self._scene
        # 时间字段
        if field == "time":
            now = datetime.now()
            return f"{now.hour:02d}:{now.minute:02d}"
        # 驾驶时长
        if field == "driving_duration_min":
            if self._driving_start_time > 0 and self._vehicle_status.get("speed", 0) > 0:
                return (time.time() - self._driving_start_time) / 60
            return 0
        return None

    def _check_trigger(self, rule: ProactiveRule) -> bool:
        """检查触发条件"""
        value = self._get_field_value(rule.trigger_field)
        if value is None:
            return False

        if rule.trigger_op == "lt":
            return float(value) < float(rule.trigger_value)
        elif rule.trigger_op == "gt":
            return float(value) > float(rule.trigger_value)
        elif rule.trigger_op == "eq":
            return str(value) == str(rule.trigger_value)
        elif rule.trigger_op == "contains":
            return str(rule.trigger_value) in str(value)
        elif rule.trigger_op == "between":
            if isinstance(rule.trigger_value, list) and len(rule.trigger_value) == 2:
                return str(rule.trigger_value[0]) <= str(value) <= str(rule.trigger_value[1])
        return False

    def _check_condition(self, rule: ProactiveRule) -> bool:
        """检查附加条件"""
        if not rule.condition_field:
            return True
        value = self._get_field_value(rule.condition_field)
        if value is None:
            return False
        if rule.condition_op == "eq":
            return str(value) == str(rule.condition_value)
        elif rule.condition_op == "ne":
            return str(value) != str(rule.condition_value)
        return True

    def _check_cooldown(self, rule_id: str) -> bool:
        """检查冷却时间（防重复推送）"""
        last_push = self._push_history.get(rule_id, 0)
        rule = next((r for r in self._rules if r.id == rule_id), None)
        cooldown = rule.cooldown if rule else 600
        return (time.time() - last_push) >= cooldown

    async def evaluate_and_push(self) -> list[dict]:
        """评估所有规则，命中则生成推送消息

        Returns:
            推送消息列表 [{"type", "priority", "rule_id", "message", "suggested_actions"}]
        """
        pushed = []
        for rule in self._rules:
            if not self._check_trigger(rule):
                continue
            if not self._check_condition(rule):
                continue
            if not self._check_cooldown(rule.id):
                continue

            # 生成推送消息
            priority_icons = {
                "low": "💡",
                "medium": "⚡",
                "high": "⚠️",
                "critical": "🚨",
            }
            icon = priority_icons.get(rule.priority, "💡")

            message = f"{icon} [{rule.priority.upper()}] {rule.task}"
            proactive_msg = {
                "type": "proactive_recommendation",
                "priority": rule.priority,
                "rule_id": rule.id,
                "message": message,
                "agent": rule.agent,
                "suggested_actions": [],
                "timestamp": datetime.now().isoformat(),
            }

            # 标记已推送
            self._push_history[rule.id] = time.time()
            pushed.append(proactive_msg)

            logger.info(
                f"[主动推荐] rule={rule.id} priority={rule.priority} "
                f"agent={rule.agent} message={message[:80]}"
            )

        return pushed

    def subscribe(self, callback):
        """注册推送回调（用于 SSE 或 WebSocket 推送）"""
        self._subscribers.append(callback)

    async def _notify_subscribers(self, messages: list[dict]):
        """通知所有订阅者"""
        for callback in self._subscribers:
            try:
                await callback(messages)
            except Exception as e:
                logger.warning(f"[主动推荐] 推送回调失败: {e}")

    async def start_periodic_check(self, interval: int = 60):
        """启动定时评估循环

        Args:
            interval: 评估间隔（秒），默认60秒
        """
        self._running = True
        logger.info(f"[主动推荐] 定时评估启动，间隔={interval}秒")

        while self._running:
            try:
                messages = await self.evaluate_and_push()
                if messages:
                    await self._notify_subscribers(messages)
            except Exception as e:
                logger.error(f"[主动推荐] 评估循环异常: {e}")

            await asyncio.sleep(interval)

    def stop(self):
        """停止定时评估"""
        self._running = False
        logger.info("[主动推荐] 定时评估已停止")


# ===== 全局实例 =====
proactive_engine = ProactiveEngine()
