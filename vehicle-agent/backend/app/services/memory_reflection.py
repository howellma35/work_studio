"""
记忆反思与结构化沉淀 — Reflective Agent 模式

每轮对话结束后，独立的反思 Agent 对交互做四维分析：
1. 隐含偏好提取：从行为模式推断偏好
2. 记忆冲突检测：新信息与已有档案矛盾标注
3. 结构化沉淀：零散偏好压缩为画像字段更新
4. 主动提醒生成：信息→可操作待办

反思不阻塞用户回复，异步执行。
"""
import json
from datetime import datetime
from loguru import logger

from app.memory.manager import memory_manager
from app.models.llm import create_llm


REFLECTION_PROMPT = """\
你是 AutoMind 的记忆反思 Agent，负责分析本轮对话并提取有价值的信息沉淀到长期记忆。

分析维度:
1. **隐含偏好**: 用户的行为模式暗示了什么偏好？
   例: 用户连续3次选择周杰伦→偏好"流行音乐/周杰伦"
   例: 用户每次导航都从家出发→偏好"默认起点=家"

2. **记忆冲突**: 本轮信息与已有档案是否矛盾？
   例: 用户说"空调25度"但档案记录"偏好22度"→标注需确认

3. **结构化沉淀**: 将零散信息压缩为结构化画像字段
   例: 3条偏好→{"music_genre": "流行", "default_origin": "家", "climate_temp": 25}

4. **提醒生成**: 信息中是否包含可操作的待办？
   例: "保养记录显示上次12000km"→创建提醒"15000km时需保养"

输入:
- 本轮对话摘要: {conversation_summary}
- 当前用户档案: {current_profile}

输出严格 JSON 格式（不要加任何其他文字）:
{
  "implicit_preferences": [
    {"preference": "偏好描述", "evidence": "证据来源", "confidence": 0.0-1.0}
  ],
  "conflicts": [
    {"new_info": "新信息", "existing": "已有信息", "field": "冲突字段", "suggestion": "建议处理方式"}
  ],
  "profile_updates": {
    "field_name": "new_value"
  },
  "reminders_to_create": [
    {"content": "提醒内容", "remind_at": "提醒时间/条件"}
  ]
}"""


class MemoryReflectionService:
    """对话后反思与记忆沉淀服务"""

    def __init__(self):
        self._reflection_llm = None

    def _get_llm(self):
        """懒加载反思 LLM（使用低成本模型）"""
        if self._reflection_llm is None:
            self._reflection_llm = create_llm(temperature=0.1)
        return self._reflection_llm

    async def reflect_and_settle(
        self,
        user_id: str,
        conversation_summary: str,
        current_profile: dict,
    ) -> dict:
        """对本轮对话做反思，返回结构化沉淀结果

        Args:
            user_id: 用户标识
            conversation_summary: 本轮对话摘要（最后几条消息的拼接）
            current_profile: 当前用户档案

        Returns:
            反思结果 dict（含 implicit_preferences, conflicts, profile_updates, reminders）
        """
        if not conversation_summary or len(conversation_summary) < 10:
            logger.debug("[记忆反思] 对话摘要太短，跳过反思")
            return {"implicit_preferences": [], "conflicts": [], "profile_updates": {}, "reminders_to_create": []}

        reflection_input = REFLECTION_PROMPT.format(
            conversation_summary=conversation_summary,
            current_profile=json.dumps(current_profile, ensure_ascii=False) if current_profile else "{}",
        )

        try:
            llm = self._get_llm()
            result = await llm.ainvoke(reflection_input)
            parsed = self._parse_reflection_result(result.content)

            # 执行沉淀
            if parsed.get("profile_updates"):
                memory_manager.update_profile(user_id, parsed["profile_updates"])
                logger.info(f"[记忆反思] 档案更新: {parsed['profile_updates']}")

            for reminder in parsed.get("reminders_to_create", []):
                remind_at = reminder.get("remind_at", "下次启动时")
                memory_manager.add_reminder(user_id, reminder["content"], remind_at)
                logger.info(f"[记忆反思] 提醒创建: {reminder['content']}")

            # 隐含偏好存入向量记忆
            for pref in parsed.get("implicit_preferences", []):
                confidence = pref.get("confidence", 0.5)
                if confidence >= 0.6:
                    memory_manager.long_term.save_preference(
                        user_id,
                        pref["preference"],
                        metadata={"evidence": pref.get("evidence", ""), "confidence": str(confidence)},
                    )

            logger.info(
                f"[记忆反思] 完成 | user={user_id} | "
                f"偏好={len(parsed.get('implicit_preferences', []))} "
                f"冲突={len(parsed.get('conflicts', []))} "
                f"更新={len(parsed.get('profile_updates', {}))} "
                f"提醒={len(parsed.get('reminders_to_create', []))}"
            )
            return parsed

        except Exception as e:
            logger.warning(f"[记忆反思] 反思失败（不影响对话）: {e}")
            return {"implicit_preferences": [], "conflicts": [], "profile_updates": {}, "reminders_to_create": []}

    def _parse_reflection_result(self, content: str) -> dict:
        """解析 LLM 输出的 JSON 反思结果"""
        # LLM 可能输出带 markdown 包裹的 JSON
        content = content.strip()
        if content.startswith("```"):
            # 去掉 markdown 包裹
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        try:
            parsed = json.loads(content)
            # 验证必要字段
            parsed.setdefault("implicit_preferences", [])
            parsed.setdefault("conflicts", [])
            parsed.setdefault("profile_updates", {})
            parsed.setdefault("reminders_to_create", [])
            return parsed
        except json.JSONDecodeError:
            logger.warning(f"[记忆反思] JSON 解析失败，原始内容: {content[:200]}")
            return {"implicit_preferences": [], "conflicts": [], "profile_updates": {}, "reminders_to_create": []}

    def extract_conversation_summary(self, messages: list) -> str:
        """从对话消息列表提取反思用的摘要

        只取最近几轮对话（避免太长浪费 token）
        """
        if not messages:
            return ""

        # 取最近 6 条消息
        recent = messages[-6:] if len(messages) > 6 else messages
        summary_parts = []
        for msg in recent:
            if hasattr(msg, "content"):
                content = msg.content
                if isinstance(content, list):
                    content = "".join(seg.get("text", "") if isinstance(seg, dict) else str(seg) for seg in content)
                role = msg.type if hasattr(msg, "type") else "unknown"
                summary_parts.append(f"[{role}] {content[:200]}")

        return "\n".join(summary_parts)


# 全局实例
memory_reflection = MemoryReflectionService()
