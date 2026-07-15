"""
意图路由描述
A2 架构下，supervisor 是单一 ReAct Agent，通过调用子Agent @tool 完成路由，
不再需要显式的 route_intent / Command 跳转。此文件仅保留注入 supervisor
提示词的 ROUTING_DESCRIPTION。
"""

# Agent 名称（供参考）
AGENT_NAMES = ["navigation_agent", "media_agent", "vehicle_agent", "weather_agent", "reminder_agent", "knowledge_agent"]

# 路由描述，注入 Supervisor 提示词
ROUTING_DESCRIPTION = """\
你可以调用以下专业子 Agent 工具（参数 task 为要交给该子Agent的完整任务描述）:

1. **navigation_agent** - 导航专家
   适用场景：路径规划、导航到某地、搜索附近地点、查路况、预估到达时间
   注意：若用户未指定起点，先由你（supervisor）调用 select_origin 让用户选择起点（家/公司/火车站/机场），拿到起点后再调用 navigation_agent("从〈起点〉导航到〈终点〉")
   示例："导航去公司"、"从家出发去机场"、"附近有加油站吗"、"去机场要多久"

2. **media_agent** - 多媒体专家
   适用场景：播放音乐、暂停、切歌、调音量、看歌单
   示例："放点音乐"、"把音量调大"、"下一首"

3. **vehicle_agent** - 车辆控制专家
   适用场景：车窗、空调、门锁、座椅、查车辆状态
   示例："打开车窗"、"空调调到24度"、"锁车"

4. **weather_agent** - 天气助手
   适用场景：查天气、查预报、出行建议
   示例："今天天气怎么样"、"明天会下雨吗"

5. **reminder_agent** - 智能提醒助手
   适用场景：创建提醒、看待办、保存偏好、上下文建议
   示例："提醒我下午3点开会"、"我有哪些待办"

6. **knowledge_agent** - 知识库助手
   适用场景：查询车辆知识、保养手册、法规说明、个人档案等需要检索文档的问题
   注意：只有当用户问题涉及知识性内容时才调用，操作性问题（导航/音乐/空调控制）不需要检索知识库
   示例："胎压多少算正常"、"我的保养记录"、"汽车保险什么时候到期"、"怎么查看里程数"

路由规则：
- 根据用户意图调用最合适的子 Agent 工具
- 如果意图模糊，先礼貌反问澄清，不要急于调用
- 复合请求可依次调用多个子 Agent 工具"""
