"""
多模态知识库 Agent — Vision LLM + RAG 联合检索

流程:
1. 收到图片 → Vision LLM 识别关键信息（报警灯名称、损伤类型）
2. 将识别结果作为关键词检索知识库获取详细说明
3. 融合视觉识别 + 知识库检索给出完整回答
4. 附上来源标注和操作建议

工具:
- analyze_dashboard_image: 识别仪表盘报警灯并解释含义
- compare_with_manual: 将用户描述与车辆手册中的标准对比
- multimodal_search: 基于图片描述+文本关键词联合检索知识库
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.models.llm import create_llm

MULTIMODAL_KB_PROMPT = """\
你是 AutoMind 的多模态知识库助手，支持图片描述+文本联合检索。

能力:
- analyze_dashboard_image: 识别仪表盘报警灯并解释含义+应对措施
- compare_with_manual: 将用户描述与车辆手册中的标准对比
- multimodal_search: 基于图片描述+文本关键词联合检索知识库

规则:
1. 收到图片描述时，先识别关键信息（报警灯名称、损伤类型）
2. 将识别结果作为关键词检索知识库获取详细说明
3. 融合视觉识别+知识库检索给出完整回答
4. 附上来源标注和操作建议"""


@tool
def analyze_dashboard_image(image_description: str) -> str:
    """识别仪表盘报警灯并解释含义

    流程:
    1. 从用户提供的图片描述中识别报警灯图标
    2. 将识别结果（如"胎压报警灯亮起"）作为关键词检索知识库
    3. 融合视觉识别+知识库信息给出完整应对建议

    Args:
        image_description: 仪表盘照片的文字描述（如"红色灯亮了，像轮胎形状"）
    """
    # 常见报警灯识别映射
    DASHBOARD_LIGHT_MAP = {
        "轮胎": {"name": "胎压报警灯", "color": "黄色/红色", "severity": "高",
                  "action": "立即检查胎压，如低于2.3bar需充气或更换轮胎"},
        "发动机": {"name": "发动机故障灯", "color": "黄色", "severity": "高",
                    "action": "建议停车检查，如伴随异响需立即停驶"},
        "电池": {"name": "电池/充电系统报警灯", "color": "红色", "severity": "高",
                  "action": "检查电池和充电系统，可能需要更换电池"},
        "油壶": {"name": "机油压力报警灯", "color": "红色", "severity": "紧急",
                  "action": "⚠️立即停车！机油压力不足可能导致发动机损坏"},
        "温度": {"name": "水温报警灯", "color": "红色", "severity": "高",
                  "action": "发动机过热，建议停车等待降温后检查冷却液"},
        "ABS": {"name": "ABS制动系统报警灯", "color": "黄色", "severity": "中",
                 "action": "ABS系统可能故障，常规制动仍可用，建议尽快检修"},
        "气囊": {"name": "安全气囊报警灯", "color": "红色", "severity": "中",
                  "action": "安全气囊系统异常，碰撞时可能不触发，建议检修"},
        "刹车": {"name": "制动系统报警灯", "color": "红色", "severity": "紧急",
                  "action": "⚠️立即停车检查！制动系统可能失效"},
    }

    # 从描述中匹配报警灯
    identified = []
    for keyword, info in DASHBOARD_LIGHT_MAP.items():
        if keyword in image_description:
            identified.append(info)

    if not identified:
        # 默认识别（模糊描述）
        return f"""仪表盘报警灯初步分析:
描述: {image_description}
未能精确识别报警灯类型，建议:
1. 查看车辆手册中的报警灯说明图
2. 如报警灯为红色请立即停车检查
3. 如为黄色可继续行驶但需尽快检修
4. 可以上传更清晰的图片再做识别"""

    # 拼接识别结果 + 知识库建议
    result_parts = []
    for info in identified:
        severity_prefix = {"紧急": "🚨", "高": "⚠️", "中": "⚡", "低": "💡"}[info["severity"]]
        result_parts.append(
            f"{severity_prefix} {info['name']}（{info['color']}，严重度: {info['severity']}）\n"
            f"应对措施: {info['action']}"
        )

    return f"""仪表盘报警灯识别结果:\n{chr(10).join(result_parts)}\n\n建议: 如果多个报警灯同时亮起，请优先处理紧急级别的，并尽快联系售后。"""


@tool
def compare_with_manual(description: str) -> str:
    """将用户描述与车辆手册中的标准对比

    Args:
        description: 用户描述的问题或状态（如"刹车时有异响"）
    """
    # 车辆手册常见标准值
    MANUAL_STANDARDS = {
        "胎压": {"standard": "2.3-3.0 bar", "note": "冷车状态下测量，前轮通常2.5，后轮2.3"},
        "机油": {"standard": "每5000km或6个月更换", "note": "使用5W-30或0W-20全合成机油"},
        "刹车片": {"standard": "厚度≥3mm", "note": "低于3mm需更换，伴随异响需立即检查"},
        "电池": {"standard": "健康度≥70%", "note": "低于70%建议更换，寿命约5-8年"},
        "冷却液": {"standard": "温度90-105°C正常", "note": "超过110°C需停车降温"},
        "空调": {"standard": "制冷出风口8-15°C", "note": "不制冷需检查压缩机和冷媒"},
    }

    # 匹配相关标准
    matched = []
    for key, info in MANUAL_STANDARDS.items():
        if key in description:
            matched.append(f"{key}标准: {info['standard']}\n注意: {info['note']}")

    if not matched:
        return f"暂未找到与「{description}」直接匹配的手册标准。建议查阅完整保养手册或联系售后。"

    return f"""车辆手册标准对比:\n{chr(10).join(matched)}\n\n建议: 对照以上标准值检查车辆状态，超出范围需及时处理。"""


@tool
def multimodal_search(query: str) -> str:
    """基于描述+关键词联合检索知识库

    Args:
        query: 搜索查询（如"报警灯 胎压 红色"）
    """
    # 模拟多模态知识库检索
    # 真实实现会调用 RAGFlow knowledge_service.search()
    KB_RESULTS = {
        "胎压": "胎压标准值为2.3-3.0bar（冷车）。低于2.3bar需充气，高于3.0bar需放气。报警灯亮起时立即检查。",
        "报警灯": "仪表盘报警灯颜色含义: 红色=紧急需停车, 黄色=需尽快检修, 绿色/蓝色=正常指示。",
        "保养": "保养间隔: 每5000km或6个月。主要项目: 机油更换、滤芯检查、胎压校准、刹车片磨损检查。",
        "电池": "电池健康度标准≥70%。低于70%建议更换。电量低于20%时应立即寻找充电站。",
        "油耗": "正常油耗范围7-9L/100km。突增超过20%需检查空气滤芯、火花塞和轮胎。",
    }

    results = []
    for key, info in KB_RESULTS.items():
        if key in query:
            results.append(f"[来源: 车辆保养手册 | {key}] {info}")

    if not results:
        return f"未找到与「{query}」相关的知识库内容。"

    return "\n".join(results)


def create_multimodal_knowledge_agent() -> object:
    """创建多模态知识库子Agent"""
    tools = [analyze_dashboard_image, compare_with_manual, multimodal_search]
    return create_agent(
        model=create_llm(temperature=0.1),
        tools=tools,
        prompt=MULTIMODAL_KB_PROMPT,
        name="multimodal_knowledge_agent",
    )
