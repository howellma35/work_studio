"""
实时车况流处理与事件驱动 — 模拟 CAN Bus 数据流

架构:
- TelemetrySimulator: 每秒生成一组车况数据（速度/电池/胎压/里程）
- WebSocket 端点: 前端订阅实时车况
- 事件触发: 数据变化 → 场景切换 + 主动推荐评估

真实部署时替换模拟器为 CAN Bus 解析器，整体架构不变。
"""
import asyncio
import random
from datetime import datetime
from loguru import logger

from app.config import settings


class TelemetrySimulator:
    """车况数据实时模拟器

    模拟 CAN Bus 数据流，每隔1秒生成一组车况数据:
    - 速度: 基于当前场景变化
    - 电池: 每小时衰减0.5%
    - 胎压: 微波动 ±0.01bar
    - 里程: 速度积分累加

    真实部署时替换为 CAN Bus 解析器
    """

    def __init__(self):
        self._state = {
            "speed": 0,
            "battery": 78,
            "mileage": 15234,
            "tire_pressure": {"front": 2.5, "rear": 2.3},
            "engine_temp": 90,
            "gear": "P",
            "fuel_consumption": 7.5,
        }
        self._subscribers: list = []  # WebSocket 客户端列表
        self._running = False
        self._driving_mode = "parked"  # parked / city / highway

    def set_driving_mode(self, mode: str):
        """切换驾驶模式（模拟器用）

        Args:
            mode: "parked" / "city" / "highway"
        """
        self._driving_mode = mode
        if mode == "parked":
            self._state["gear"] = "P"
            self._state["speed"] = 0
        elif mode == "city":
            self._state["gear"] = "D"
            self._state["speed"] = 30
        elif mode == "highway":
            self._state["gear"] = "D"
            self._state["speed"] = 80
        logger.info(f"[遥测模拟] 驾驶模式切换: {mode}")

    def _update_state(self):
        """模拟车况变化"""
        if self._driving_mode == "parked":
            # 停车状态: 速度0，电池缓慢自放电
            self._state["speed"] = 0
            self._state["battery"] -= random.uniform(0, 0.002)
        elif self._driving_mode == "city":
            # 城市驾驶: 速度20-50km/h随机漫步
            self._state["speed"] += random.uniform(-8, 8)
            self._state["speed"] = max(5, min(55, self._state["speed"]))
            self._state["battery"] -= random.uniform(0.01, 0.05)
        elif self._driving_mode == "highway":
            # 高速驾驶: 速度60-120km/h
            self._state["speed"] += random.uniform(-5, 5)
            self._state["speed"] = max(60, min(120, self._state["speed"]))
            self._state["battery"] -= random.uniform(0.02, 0.08)

        # 电池衰减下限
        self._state["battery"] = max(5, self._state["battery"])

        # 里程累加
        if self._state["speed"] > 0:
            self._state["mileage"] += self._state["speed"] / 3600

        # 胎压微波动
        for key in self._state["tire_pressure"]:
            self._state["tire_pressure"][key] += random.uniform(-0.01, 0.01)
            self._state["tire_pressure"][key] = max(1.8, min(3.5, self._state["tire_pressure"][key]))

        # 发动机温度
        if self._state["speed"] > 0:
            self._state["engine_temp"] += random.uniform(-0.5, 1.0)
            self._state["engine_temp"] = max(80, min(115, self._state["engine_temp"]))
        else:
            self._state["engine_temp"] -= random.uniform(0, 0.5)
            self._state["engine_temp"] = max(75, min(95, self._state["engine_temp"]))

    async def start_stream(self):
        """启动数据流（每秒推送车况更新）"""
        self._running = True
        logger.info("[遥测模拟] 数据流启动")
        while self._running:
            self._update_state()
            await self._broadcast()
            await asyncio.sleep(1)

    def stop_stream(self):
        """停止数据流"""
        self._running = False
        logger.info("[遥测模拟] 数据流停止")

    def get_current_state(self) -> dict:
        """获取当前车况快照"""
        return {
            "type": "telemetry_update",
            "data": self._state.copy(),
            "timestamp": datetime.now().isoformat(),
        }

    async def _broadcast(self):
        """向所有订阅者推送当前车况"""
        payload = self.get_current_state()
        for callback in self._subscribers:
            try:
                await callback(payload)
            except Exception:
                self._subscribers.remove(callback)

    def subscribe(self, callback):
        """注册推送回调"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        """取消推送回调"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)


# 全局实例
telemetry_simulator = TelemetrySimulator()
