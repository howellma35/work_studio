"""
OTA 更新智能助手 — LLM 翻译技术说明 + 场景时机推荐 + 安全紧急标注

能力:
- explain_update: 将技术更新说明翻译为通俗语言
- recommend_timing: 基于场景推荐最佳更新时机
- compare_versions: 对比新旧版本功能差异
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.graph.scene_config import DrivingScene
from app.models.llm import create_llm

OTA_PROMPT = """\
你是 AutoMind 的 OTA 更新智能助手。

能力:
- explain_update: 将技术性更新说明翻译为车主能理解的通俗语言
- recommend_timing: 基于场景+时间推荐最佳更新时机
- compare_versions: 对比新旧版本功能差异

规则:
1. 始终用通俗语言解释技术内容
2. 绝不在行驶中推荐更新
3. 给出具体的推荐时间
4. 安全相关更新用⚠️标注"""


@tool
def explain_update(update_notes: str) -> str:
    """将技术更新说明翻译为通俗语言

    Args:
        update_notes: 技术更新说明文本
    """
    # 通俗化翻译模板
    TECH_TERMS = {
        "CAN协议栈": "车内通信系统",
        "ID345刹车延迟": "⚠️刹车响应延迟（安全相关）",
        "ADAS车道偏离预警": "新增车道偏离提醒功能",
        "OTA": "在线升级",
        "固件": "系统软件",
        "MCU": "主控芯片",
        "ECU": "电子控制单元",
        "RTOS": "实时操作系统",
        "协议栈": "通信协议软件包",
    }

    # 简单术语替换
    translated = update_notes
    for tech, plain in TECH_TERMS.items():
        translated = translated.replace(tech, plain)

    # 安全标注
    safety_keywords = ["刹车", "制动", "安全", "碰撞", "故障", "延迟"]
    has_safety = any(k in update_notes for k in safety_keywords)

    result = f"通俗翻译:\n{translated}\n"
    if has_safety:
        result += "\n⚠️ 本次更新包含安全相关内容，建议尽快更新！"

    return result


@tool
def recommend_timing(current_scene: str, update_size_mb: int = 200) -> str:
    """推荐最佳更新时机

    Args:
        current_scene: 当前驾驶场景 (idle/city/highway/parked/emergency)
        update_size_mb: 更新包大小 (MB)
    """
    scene = DrivingScene(current_scene) if current_scene in [s.value for s in DrivingScene] else DrivingScene.IDLE

    if scene in [DrivingScene.CITY_DRIVING, DrivingScene.HIGHWAY]:
        return "⚠️ 当前正在行驶，请停车后再进行更新。行驶中更新可能导致系统不稳定。"

    if scene == DrivingScene.EMERGENCY:
        return "⚠️ 当前为紧急状态，请先处理紧急事务后再考虑更新。"

    if scene == DrivingScene.PARKED or scene == DrivingScene.IDLE:
        if update_size_mb > 500:
            return f"本次更新包较大({update_size_mb}MB)，建议在家WiFi环境下更新。\n预计今晚到家后8点左右最合适。\n更新过程约需10-15分钟，更新期间车辆系统会重启。"
        else:
            return f"当前停车状态适合更新，预计需要5-10分钟完成。\n是否现在开始更新？"

    return "建议在停车状态下进行更新。"


@tool
def compare_versions(old_version: str = "V2.2.0", new_version: str = "V2.3.1") -> str:
    """对比新旧版本功能差异"""
    # 模拟版本差异
    VERSION_DIFF = {
        ("V2.2.0", "V2.3.1"): {
            "new_features": ["车道偏离预警", "智能停车辅助", "语音控制增强"],
            "bug_fixes": ["⚠️刹车响应延迟修复(ID345)", "CAN通信稳定性提升"],
            "performance": ["系统启动速度提升20%", "语音识别准确率提升15%"],
        },
    }

    diff = VERSION_DIFF.get((old_version, new_version), {
        "new_features": ["待查询具体变更"],
        "bug_fixes": ["待查询具体修复"],
        "performance": ["待查询具体优化"],
    })

    result = f"""版本对比: {old_version} → {new_version}

新增功能:
{chr(10).join(f'  ✅ {f}' for f in diff['new_features'])}

修复问题:
{chr(10).join(f'  🔧 {f}' for f in diff['bug_fixes'])}

性能优化:
{chr(10).join(f'  ⚡ {f}' for f in diff['performance'])}

总体评价: 推荐更新（包含安全修复）"""

    return result


def create_ota_agent() -> object:
    """创建OTA更新智能助手子Agent"""
    tools = [explain_update, recommend_timing, compare_versions]
    return create_agent(
        model=create_llm(temperature=0.2),
        tools=tools,
        prompt=OTA_PROMPT,
        name="ota_agent",
    )
