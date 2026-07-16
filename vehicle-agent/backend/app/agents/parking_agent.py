"""
智能停车助手 Agent — 领域专用 Agent 设计模式

四层能力:
- find_parking: 搜索附近停车场（高德POI + 停车场数据）
- estimate_cost: 预估停车成本（基于时长+费率模型）
- recommend_parking: 多维加权推荐（距离+价格+空位率+类型）
- navigate_to_parking: 导航到推荐停车场入口（而非目的地本身）
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.models.llm import create_llm

PARKING_PROMPT = """\
你是 AutoMind 的智能停车助手 Agent。

你的能力:
- find_parking: 搜索附近停车场（接入高德POI+停车场数据API）
- estimate_cost: 预估停车成本（基于时长+费率模型）
- recommend_parking: 基于多维约束推荐最优停车方案
- navigate_to_parking: 导航到推荐停车场入口

推荐策略:
1. 优先考虑空位率≥60%的停车场（避免到场无位）
2. 商务区优先推荐地下停车场（安全+遮阳）
3. 居民区优先推荐路边免费位
4. 长时间停车优先推荐便宜但远的；短时间优先推荐近的
5. 始终给出2-3个选项让用户选择"""


@tool
def find_parking(destination: str, radius_km: float = 1.0) -> str:
    """搜索目的地附近的停车场

    Args:
        destination: 目的地名称
        radius_km: 搜索半径（公里）
    """
    # 模拟停车场搜索结果
    PARKING_OPTIONS = [
        {"name": "商务中心地下停车场", "type": "地下", "distance_km": 0.2,
         "rate_first_hour": 10, "rate_additional": 5, "availability": 85, "max_hours": 24},
        {"name": "路边停车场A", "type": "路边", "distance_km": 0.5,
         "rate_first_hour": 15, "rate_additional": 10, "availability": 45, "max_hours": 4},
        {"name": "社区停车场", "type": "地面", "distance_km": 1.0,
         "rate_first_hour": 2, "rate_additional": 2, "availability": 90, "max_hours": 24},
    ]

    result_parts = []
    for p in PARKING_OPTIONS:
        avail_status = "🟢空位充足" if p["availability"] >= 70 else "🟡空位紧张" if p["availability"] >= 40 else "🔴几乎无位"
        result_parts.append(
            f"- {p['name']} ({p['type']}) | 距离{p['distance_km']}km | "
            f"首小时{p['rate_first_hour']}元/后{p['rate_additional']}元/h | "
            f"{avail_status}({p['availability']}%)"
        )

    return f"「{destination}」附近停车场搜索结果:\n{chr(10).join(result_parts)}"


@tool
def estimate_cost(parking_name: str, duration_hours: float = 2.0) -> str:
    """预估停车成本

    Args:
        parking_name: 停车场名称
        duration_hours: 预计停车时长（小时）
    """
    # 模拟费率模型
    RATE_MODEL = {
        "商务中心地下停车场": {"first_hour": 10, "additional": 5, "max_daily": 60},
        "路边停车场A": {"first_hour": 15, "additional": 10, "max_daily": None},
        "社区停车场": {"first_hour": 2, "additional": 2, "max_daily": 20},
    }

    rates = RATE_MODEL.get(parking_name, {"first_hour": 8, "additional": 4, "max_daily": 50})
    total = rates["first_hour"] + max(0, duration_hours - 1) * rates["additional"]
    if rates["max_daily"] and total > rates["max_daily"]:
        total = rates["max_daily"]

    return f"""停车成本预估:
停车场: {parking_name}
时长: {duration_hours}小时
首小时: {rates['first_hour']}元 + 后续{rates['additional']}元/h
预估总费用: {total:.0f}元{'(已封顶)' if rates.get('max_daily') and total == rates['max_daily'] else ''}"""


@tool
def recommend_parking(destination: str, duration_hours: float = 2.0, budget_priority: str = "balanced") -> str:
    """基于多维约束推荐最优停车方案

    Args:
        destination: 目的地
        duration_hours: 预计停车时长
        budget_priority: 优先级 (near/cheap/balanced)
    """
    options = [
        {"name": "商务中心地下停车场", "distance": 0.2, "cost": 15, "avail": 85, "type": "地下"},
        {"name": "路边停车场A", "distance": 0.5, "cost": 25, "avail": 45, "type": "路边"},
        {"name": "社区停车场", "distance": 1.0, "cost": 6, "avail": 90, "type": "地面"},
    ]

    # 权重配置
    weights = {"near": {"dist": 0.5, "cost": 0.2, "avail": 0.2, "type": 0.1},
               "cheap": {"dist": 0.2, "cost": 0.5, "avail": 0.2, "type": 0.1},
               "balanced": {"dist": 0.3, "cost": 0.3, "avail": 0.2, "type": 0.2}}
    w = weights.get(budget_priority, weights["balanced"])

    # 评分
    scored = []
    for o in options:
        score = (w["dist"] * (1 - o["distance"] / 2) +
                 w["cost"] * (1 - o["cost"] / 30) +
                 w["avail"] * o["avail"] / 100 +
                 w["type"] * (0.8 if o["type"] == "地下" else 0.5))
        scored.append({"name": o["name"], "score": score, "detail": o})

    scored.sort(key=lambda x: x["score"], reverse=True)

    result = f"停车推荐（优先级: {budget_priority}）:\n"
    for i, s in enumerate(scored[:3]):
        o = s["detail"]
        result += f"  {i+1}. {s['name']} | 评分{s['score']:.2f} | 距{o['distance']}km | {o['cost']}元 | 空位{o['avail']}%\n"

    return result


def create_parking_agent() -> object:
    """创建智能停车助手子Agent"""
    tools = [find_parking, estimate_cost, recommend_parking]
    return create_agent(
        model=create_llm(temperature=0.2),
        tools=tools,
        prompt=PARKING_PROMPT,
        name="parking_agent",
    )
