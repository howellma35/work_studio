"""
MCP Server (Model Context Protocol)
统一的车载工具服务器，聚合导航/多媒体/车辆控制/天气工具

所有工具注册到 app.mcp.tools 共享的单一 FastMCP 实例上（官方推荐写法），
本模块只需导入各工具模块（触发 @mcp.tool() 注册）后调用 mcp.run()。

支持两种运行模式:
1. stdio: 作为子进程被 Agent 启动（开发推荐）
2. sse: 独立 HTTP 服务（生产部署）

启动方式:
    python -m app.mcp.server              # stdio 模式（默认）
    python -m app.mcp.server --sse        # sse 模式
"""
import sys

# 导入共享实例与各工具模块：导入即触发 @mcp.tool() 注册到同一实例
from app.mcp.tools import mcp
from app.mcp.tools import (  # noqa: F401  (导入用于副作用：注册工具)
    media_tools,
    navigation_tools,
    vehicle_tools,
    weather_tools,
)


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
