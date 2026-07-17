"""
短期对话记忆模块（checkpointer）

A2 架构下，对话短时记忆由 supervisor 直接持有的 AsyncSqliteSaver 负责
（见 app/graph/supervisor.py:get_checkpointer），不再在此创建独立的
MemorySaver 单例。本模块保留为说明性占位，避免历史 import 报错。

如需切换生产级持久化，将 supervisor.get_checkpointer() 内的
AsyncSqliteSaver 替换为 AsyncPostgresSaver（同一 checkpointer 接口）。
"""
