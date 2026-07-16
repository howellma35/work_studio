"""
多租户用户隔离 — per-user 记忆空间 + 权限隔离 + 会话分区

隔离维度:
1. 记忆隔离: 每个用户独立的 ChromaDB collection + SQLite 行
2. 车况隔离: 每个用户独立的车辆状态快照
3. 权限隔离: 不同角色不同工具集
4. 会话隔离: thread_id 按 user_id 分区

与 DynamicToolsMiddleware 配合:
- 乘客看不见锁车工具
- 管理员看见系统管理工具
"""
from loguru import logger

from app.config import settings


# ===== 用户角色定义 =====
USER_ROLES = {
    "admin": {
        "label": "车主/管理员",
        "icon": "🧑‍💼",
        "tool_access": "all",
        "can_lock_doors": True,
        "can_system_reset": True,
    },
    "driver": {
        "label": "驾驶员",
        "icon": "👩",
        "tool_access": "standard",
        "can_lock_doors": True,
        "can_system_reset": False,
    },
    "passenger": {
        "label": "乘客",
        "icon": "🧑",
        "tool_access": "limited",
        "can_lock_doors": False,
        "can_system_reset": False,
    },
}

# ===== 驾驶员档案模板 =====
DRIVER_PROFILES = [
    {"id": "driver_001", "name": "车主", "role": "admin", "avatar": "🧑‍💼"},
    {"id": "driver_002", "name": "家人", "role": "driver", "avatar": "👩"},
    {"id": "guest", "name": "客人", "role": "passenger", "avatar": "🧑"},
]


class TenantService:
    """多租户用户隔离服务"""

    def get_isolated_memory(self, user_id: str) -> dict:
        """获取用户隔离的记忆上下文

        ChromaDB 集合命名: user_preferences_{user_id}
        SQLite 查询始终带 WHERE user_id = ?
        """
        from app.memory.manager import memory_manager

        profile = memory_manager.long_term.get_profile(user_id)
        preferences = memory_manager.long_term.recall_preferences(user_id, "", top_k=5)

        return {
            "collection_name": f"user_preferences_{user_id}",
            "profile": profile,
            "preferences": preferences,
        }

    def get_user_role(self, user_id: str) -> str:
        """获取用户角色"""
        from app.memory.manager import memory_manager
        profile = memory_manager.long_term.get_profile(user_id)
        return profile.get("role", "driver")

    def get_role_config(self, role: str) -> dict:
        """获取角色配置"""
        return USER_ROLES.get(role, USER_ROLES["driver"])

    def get_thread_id(self, user_id: str, session_id: str) -> str:
        """生成隔离的 thread_id

        格式: {user_id}_{session_id}
        保证不同用户的会话完全隔离
        """
        return f"{user_id}_{session_id}"

    def get_allowed_tools_for_role(self, role: str) -> list[str]:
        """获取角色允许的工具列表

        admin: 全部工具
        driver: 标准工具集（不含系统管理）
        passenger: 有限工具集（不含锁车等敏感操作）
        """
        ALL_TOOLS = [
            "navigation_agent", "media_agent", "vehicle_agent",
            "weather_agent", "reminder_agent", "knowledge_agent",
            "select_origin", "update_map",
        ]

        ADMIN_EXTRA = ["lock_doors_confirm", "system_reset"]
        PASSENGER_BLOCKED = ["lock_doors"]

        config = USER_ROLES.get(role, USER_ROLES["driver"])

        if config["tool_access"] == "all":
            return ALL_TOOLS + ADMIN_EXTRA
        elif config["tool_access"] == "limited":
            return [t for t in ALL_TOOLS if t not in PASSENGER_BLOCKED]
        else:
            return ALL_TOOLS

    def create_user_profile(self, user_id: str, name: str, role: str = "driver") -> dict:
        """创建用户档案"""
        from app.memory.manager import memory_manager
        profile_data = {
            "name": name,
            "role": role,
            "created_at": str(settings.DEFAULT_VEHICLE_USER_ID),
        }
        memory_manager.update_profile(user_id, profile_data)
        logger.info(f"[多租户] 用户档案创建: user={user_id}, role={role}, name={name}")
        return profile_data


# 全局实例
tenant_service = TenantService()
