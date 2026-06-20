"""
验证修复后的 _build_prompt 返回消息列表
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.config import settings
from app.graph.supervisor import _build_prompt


async def main():
    print("=" * 60)
    print("测试: 修复后的 _build_prompt + LLM tool calling")
    print("=" * 60)

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.3,
        streaming=True,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
    )

    tools = [
        {"type": "function", "function": {"name": "transfer_to_vehicle_agent", "description": "Ask agent 'vehicle_agent' for help", "parameters": {"properties": {}, "type": "object"}}},
        {"type": "function", "function": {"name": "transfer_to_media_agent", "description": "Ask agent 'media_agent' for help", "parameters": {"properties": {}, "type": "object"}}},
        {"type": "function", "function": {"name": "transfer_to_navigation_agent", "description": "Ask agent 'navigation_agent' for help", "parameters": {"properties": {}, "type": "object"}}},
    ]
    llm_with_tools = llm.bind_tools(tools)

    from langchain_core.runnables import RunnableLambda
    chain = RunnableLambda(_build_prompt) | llm_with_tools

    # 测试 1: 单轮
    print("\n--- 测试 1: 单轮 '空调温度调低一点' ---")
    state1 = {"messages": [HumanMessage(content="空调温度调低一点")], "user_id": "demo_user_001"}
    resp1 = await chain.ainvoke(state1)
    print(f"  tool_calls: {resp1.tool_calls}")
    print(f"  content: {resp1.content[:100] if resp1.content else '(empty)'}")

    # 测试 2: 单轮 '播放音乐'
    print("\n--- 测试 2: 单轮 '播放音乐' ---")
    state2 = {"messages": [HumanMessage(content="播放音乐")], "user_id": "demo_user_001"}
    resp2 = await chain.ainvoke(state2)
    print(f"  tool_calls: {resp2.tool_calls}")
    print(f"  content: {resp2.content[:100] if resp2.content else '(empty)'}")

    # 测试 3: 多轮对话
    print("\n--- 测试 3: 多轮 '导航去公司' ---")
    state3 = {
        "messages": [
            HumanMessage(content="你好"),
            AIMessage(content="您好！我是 AutoMind。", name="supervisor"),
            HumanMessage(content="导航去公司"),
        ],
        "user_id": "demo_user_001",
    }
    resp3 = await chain.ainvoke(state3)
    print(f"  tool_calls: {resp3.tool_calls}")
    print(f"  content: {resp3.content[:100] if resp3.content else '(empty)'}")


asyncio.run(main())
