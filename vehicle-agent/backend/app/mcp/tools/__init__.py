"""MCP 工具集

官方推荐写法：使用单一 FastMCP 实例注册全部工具。
各工具模块通过 `from app.mcp.tools import mcp` 共享该实例，
用 `@mcp.tool()` 注册；server.py 直接 `mcp.run()` 即对外提供全部工具。

（旧写法是每个模块各自 `FastMCP(...)` 再在 server.py 里通过私有属性
`_tool_manager._tools` 合并，依赖私有 API、易在版本升级时失效，已弃用。）
"""
from mcp.server.fastmcp import FastMCP

# 共享 MCP Server 实例：被 server.py 运行，被各 tools 模块注册
mcp = FastMCP("AutoMindVehicleServer")

__all__ = ["mcp"]
