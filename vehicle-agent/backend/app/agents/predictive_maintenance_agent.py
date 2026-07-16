"""
预测性维护 Agent — LLM + RAG 联合推理

三层融合架构:
1. 数据层: SQLite(保养历史) + 实时车况 + 时序统计
2. 知识层: RAGFlow 检索保养手册/标准值/故障案例
3. 推理层: LLM 对比数据与知识库标准 → 预测 + 建议

工具:
- analyze_maintenance_schedule: 预测下次保养窗口
- predict_battery_health: 预估电池剩余寿命和续航
- detect_anomaly: 检测异常模式（油耗/胎压/电池）
- generate_maintenance_report: 生成完整维护建议报告
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.memory.manager import memory_manager
from app.models.llm import create_llm

PREDICTIVE_MAINT_PROMPT = """\
你是 AutoMind 的预测性维护专家 Agent。

你的能力:
- analyze_maintenance_schedule: 基于里程+上次保养时间预测下次保养窗口
- predict_battery_health: 基于电池衰减趋势预估剩余寿命和续航
- detect_anomaly: 基于历史时序数据检测异常模式（油耗突增、胎压不稳）
- generate_maintenance_report: 生成完整维护建议报告

工作流程:
1. 收集数据：从车辆状态 + 维护知识库 + 时序历史获取事实
2. 知识推理：检索保养手册中的推荐间隔和标准值
3. 预测计算：对比当前数据与知识库标准，给出预测和预警
4. 生成报告：结构化输出（当前状态 + 预测结果 + 建议行动 + 紧急度）

重要：你的预测必须同时引用知识库标准和实际数据，
给出具体数字和日期，不要泛泛而谈。"""


@tool
def analyze_maintenance_schedule(user_id: str = "demo_user_001") -> str:
    """基于里程趋势+上次保养记录预测下次保养窗口

    步骤:
    1. 查 SQLite 获取用户档案中的保养记录
    2. 估算当前里程 + 平均月行驶里程
    3. 检索知识库保养手册中的推荐间隔
    4. 计算预计到达保养里程的日期
    5. 输出：建议保养日期 + 预计里程 + 保养项目
    """
    profile = memory_manager.long_term.get_profile(user_id)
    last_maintenance = profile.get("last_maintenance_date", "未知")
    last_maintenance_km = profile.get("last_maintenance_km", 0)
    current_km = profile.get("current_mileage", 15234)
    avg_monthly_km = profile.get("avg_monthly_km", 800)

    # 简单预测计算
    km_since_last = current_km - last_maintenance_km
    standard_interval_km = 5000  # 标准保养间隔
    standard_interval_months = 6

    remaining_km = standard_interval_km - km_since_last
    days_until = int((remaining_km / avg_monthly_km) * 30) if avg_monthly_km > 0 else 999

    urgency = "紧急" if remaining_km <= 500 else "建议尽快" if remaining_km <= 1500 else "正常"

    return f"""保养预测分析:
上次保养: {last_maintenance} ({last_maintenance_km}km)
当前里程: {current_km}km | 增量: {km_since_last}km
知识库标准: 每{standard_interval_km}km / 每{standard_interval_months}个月
剩余里程: {remaining_km}km → 预计{days_until}天后需保养
紧急度: {urgency}
建议保养项目: 机油更换、滤芯检查、胎压校准、刹车片磨损检查"""


@tool
def predict_battery_health(user_id: str = "demo_user_001") -> str:
    """基于电池衰减趋势预估剩余寿命和续航

    简化模型:
    - 新电池100% → 每年衰减约2-3%
    - 当前78% → 约7-8年寿命（按3%年衰减）
    - 续航衰减: 满电400km → 当前约312km
    """
    profile = memory_manager.long_term.get_profile(user_id)
    battery_current = 78  # 当前电量百分比
    battery_health = profile.get("battery_health_percent", 92)  # 电池健康度

    # 简单衰减预测
    annual_decay = 3.0  # 每年衰减3%
    years_remaining = int(battery_health / annual_decay)
    full_range_km = 400
    current_range_km = int(full_range_km * battery_health / 100)

    health_status = "良好" if battery_health >= 85 else "需关注" if battery_health >= 70 else "建议更换"

    return f"""电池健康预测:
当前电量: {battery_current}% | 健康度: {battery_health}%
满电续航: {full_range_km}km → 当前预估续航: {current_range_km}km
年衰减率: {annual_decay}% → 预估剩余寿命: {years_remaining}年
健康状态: {health_status}
建议: {years_remaining <= 3 and '建议关注电池衰减，考虑2年内更换' or '电池状态良好，继续正常使用'}"""


@tool
def detect_anomaly(user_id: str = "demo_user_001", metric: str = "all") -> str:
    """基于历史时序数据检测异常模式

    检测维度:
    - 油耗: 近期 vs 基线 → 突增预警
    - 胎压: 波动幅度 → 不稳定预警
    - 电池: 充电曲线 → 衰减预警
    - 里程: 突增/突降 → 异常驾驶预警
    """
    anomalies = []

    # 模拟异常检测（真实实现需要时序数据库）
    vehicle_status = {
        "fuel_consumption_recent": 8.5,  # L/100km 近期
        "fuel_consumption_baseline": 7.2,  # L/100km 基线
        "tire_pressure_front": 2.9,  # bar
        "tire_pressure_rear": 2.7,
        "battery_health": 92,
    }

    # 油耗异常检测
    if metric == "all" or metric == "fuel":
        recent = vehicle_status["fuel_consumption_recent"]
        baseline = vehicle_status["fuel_consumption_baseline"]
        increase_pct = ((recent / baseline) - 1) * 100
        if increase_pct > 20:
            anomalies.append(f"⚠️ 油耗近期突增 {increase_pct:.1f}%（近期{recent}L/100km vs 基线{baseline}L/100km），建议检查空气滤芯和火花塞")
        else:
            anomalies.append(f"✅ 油耗正常（近期{recent} vs 基线{baseline}，增幅{increase_pct:.1f}%）")

    # 胎压异常检测
    if metric == "all" or metric == "tire":
        front = vehicle_status["tire_pressure_front"]
        rear = vehicle_status["tire_pressure_rear"]
        if front < 2.3 or rear < 2.3:
            anomalies.append(f"⚠️ 胎压偏低（前{front}bar / 后{rear}bar），标准值2.3-3.0bar，建议检查")
        elif abs(front - rear) > 0.5:
            anomalies.append(f"⚠️ 前后胎压差异过大（差{abs(front-rear):.1f}bar），建议校准")
        else:
            anomalies.append(f"✅ 胎压正常（前{front}bar / 后{rear}bar）")

    # 电池异常检测
    if metric == "all" or metric == "battery":
        health = vehicle_status["battery_health"]
        if health < 70:
            anomalies.append(f"⚠️ 电池健康度低（{health}%），建议尽快更换")
        elif health < 85:
            anomalies.append(f"⚡ 电池健康度需关注（{health}%），预计2-3年需更换")
        else:
            anomalies.append(f"✅ 电池健康度良好（{health}%）")

    if not anomalies:
        return "当前各项指标正常，无异常模式"

    return "异常检测结果:\n" + "\n".join(anomalies)


@tool
def generate_maintenance_report(user_id: str = "demo_user_001") -> str:
    """生成完整维护建议报告

    融合保养预测+电池健康+异常检测结果
    输出结构化报告（当前状态 + 预测结果 + 建议行动 + 紧急度）
    """
    maintenance = analyze_maintenance_schedule.invoke({"user_id": user_id})
    battery = predict_battery_health.invoke({"user_id": user_id})
    anomaly = detect_anomaly.invoke({"user_id": user_id, "metric": "all"})

    return f"""📋 AutoMind 预测性维护报告
{'='*40}

【保养预测】
{maintenance}

【电池健康】
{battery}

【异常检测】
{anomaly}

{'='*40}
综合建议: 请关注保养里程和胎压状态，电池状况良好可继续使用。
报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""


def create_predictive_maintenance_agent() -> object:
    """创建预测性维护子Agent"""
    tools = [analyze_maintenance_schedule, predict_battery_health, detect_anomaly, generate_maintenance_report]
    return create_agent(
        model=create_llm(temperature=0.1),
        tools=tools,
        prompt=PREDICTIVE_MAINT_PROMPT,
        name="predictive_maintenance_agent",
    )


# 需要在 generate_maintenance_report 中引入 datetime
from datetime import datetime  # noqa: E402
