"""
MCP Client 集成
使用 langchain-mcp-adapters 连接 MCP Server，将工具转为 LangChain BaseTool

工具发现流程:
1. Agent 启动时创建 MCP Client
2. 连接 MCP Server（stdio 子进程 或 SSE 远程）
3. 调用 get_tools() 获取所有可用工具
4. 将工具分配给对应子Agent
"""
import sys
from pathlib import Path

from langchain_core.tools import BaseTool
from loguru import logger

from app.config import settings


async def load_mcp_tools() -> list[BaseTool]:
    """
    从 MCP Server 加载所有车辆工具

    根据 ${MCP_TRANSPORT} 配置选择连接方式:
    - stdio: 启动 MCP Server 子进程（开发推荐）
    - sse: 连接远程 MCP Server

    Returns:
        LangChain BaseTool 列表，可直接传给 Agent
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient

    if settings.MCP_TRANSPORT == "sse":
        # SSE 模式：连接远程 MCP Server
        server_config = {
            "vehicle": {
                "url": settings.MCP_SERVER_URL,
                "transport": "sse",
            }
        }
    else:
        # stdio 模式：启动本地 MCP Server 子进程
        server_config = {
            "vehicle": {
                "command": sys.executable,  # 当前 Python 解释器
                "args": ["-m", "app.mcp.server"],
                "transport": "stdio",
            }
        }

    client = MultiServerMCPClient(server_config)
    tools = await client.get_tools()

    tool_names = [t.name for t in tools]
    logger.info(f"MCP 工具已加载 ({len(tools)} 个): {tool_names}")
    return tools


def filter_tools_by_keyword(tools: list[BaseTool], keywords: list[str]) -> list[BaseTool]:
    """
    按工具名关键词筛选工具，用于分配给不同子Agent

    Args:
        tools: 全部工具列表
        keywords: 工具名关键词（如 ["plan_route", "search_poi", "traffic"]）

    Returns:
        匹配的子集工具
    """
    return [t for t in tools if any(kw in t.name for kw in keywords)]
