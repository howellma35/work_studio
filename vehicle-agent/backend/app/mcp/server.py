"""
MCP Server (Model Context Protocol)
统一的车载工具服务器，聚合导航/多媒体/车辆控制/天气工具

支持两种运行模式:
1. stdio: 作为子进程被 Agent 启动（开发推荐）
2. sse: 独立 HTTP 服务（生产部署）

启动方式:
    python -m app.mcp.server              # stdio 模式（默认）
    python -m app.mcp.server --sse        # sse 模式
"""
import sys

from mcp.server.fastmcp import FastMCP

from app.mcp.tools import navigation_tools, media_tools, vehicle_tools, weather_tools

# 创建统一的 MCP Server
mcp = FastMCP("AutoMindVehicleServer")

# 将所有子服务器的工具注册到主服务器
# 注意：FastMCP 工具已通过 @mcp.tool() 装饰器定义在各自模块中
# 这里通过 import 触发工具注册，并合并工具集
_all_tools = []

for tool_module in [navigation_tools, media_tools, vehicle_tools, weather_tools]:
    module_tools = tool_module.mcp._tool_manager._tools
    for name, tool in module_tools.items():
        mcp._tool_manager._tools[name] = tool
        _all_tools.append(name)


def main() -> None:
    """MCP Server 启动入口"""
    use_sse = "--sse" in sys.argv

    if use_sse:
        # SSE 模式：独立 HTTP 服务
        from app.config import settings
        mcp.run(transport="sse")
        print(f"MCP Server (SSE) 启动于 {settings.MCP_SERVER_URL}")
    else:
        # stdio 模式：作为子进程运行
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
