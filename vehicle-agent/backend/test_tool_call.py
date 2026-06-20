"""
直接测试 qwen3.7-plus 思考模式下的 tool calling 能力
"""
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY", "")
API_BASE = os.getenv("LLM_API_BASE", "")
MODEL = os.getenv("LLM_MODEL", "")


async def test_direct_stream():
    """流式调用测试 - 跳过空 chunks"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=API_KEY, base_url=API_BASE)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "transfer_to_vehicle_agent",
                "description": "Ask agent 'vehicle_agent' for help",
                "parameters": {"properties": {}, "type": "object"},
            },
        },
    ]

    print("=" * 60)
    print("--- 测试: 直接 OpenAI SDK 流式 + tools ---")
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是 AutoMind 车载助手。根据用户意图调用 transfer_to_vehicle_agent。"},
            {"role": "user", "content": "播放音乐"},
        ],
        tools=tools,
        temperature=0.3,
        stream=True,
    )
    content_parts = []
    tool_calls_data = {}
    reasoning_parts = []
    finish = None
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        finish = chunk.choices[0].finish_reason
        if delta.content:
            content_parts.append(delta.content)
        # 收集 reasoning_content
        rc = getattr(delta, "reasoning_content", None)
        if rc:
            reasoning_parts.append(rc)
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_data:
                    tool_calls_data[idx] = {"id": "", "name": "", "arguments": ""}
                if tc.id:
                    tool_calls_data[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls_data[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls_data[idx]["arguments"] += tc.function.arguments

    print(f"  回复内容: {''.join(content_parts)}")
    print(f"  tool_calls: {tool_calls_data if tool_calls_data else '无'}")
    print(f"  reasoning (前100字): {''.join(reasoning_parts)[:100]}")
    print(f"  finish_reason: {finish}")


async def test_langchain_stream():
    """LangChain ChatOpenAI 流式测试"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatOpenAI(
        model=MODEL,
        temperature=0.3,
        streaming=True,
        api_key=API_KEY,
        base_url=API_BASE,
    )

    tools_lc = [
        {
            "type": "function",
            "function": {
                "name": "transfer_to_vehicle_agent",
                "description": "Ask agent 'vehicle_agent' for help",
                "parameters": {"properties": {}, "type": "object"},
            },
        },
    ]
    llm_with_tools = llm.bind_tools(tools_lc)

    print("\n--- 测试: LangChain ainvoke (内部流式) + tools ---")
    messages = [
        SystemMessage(content="你是 AutoMind 车载助手。根据用户意图调用 transfer_to_vehicle_agent。"),
        HumanMessage(content="空调温度调低一点"),
    ]

    response = await llm_with_tools.ainvoke(messages)
    print(f"  回复内容: {response.content}")
    print(f"  tool_calls: {response.tool_calls}")
    print(f"  additional_kwargs keys: {list(response.additional_kwargs.keys())}")
    if "reasoning_content" in response.additional_kwargs:
        print(f"  reasoning_content: {response.additional_kwargs['reasoning_content'][:100] if response.additional_kwargs['reasoning_content'] else None}")

    # 测试 astream
    print("\n--- 测试: LangChain astream + tools ---")
    content_parts = []
    tool_calls = []
    async for chunk in llm_with_tools.astream(messages):
        print(f"  chunk type={type(chunk).__name__}, content={chunk.content[:50] if chunk.content else ''!r}, tool_calls={getattr(chunk, 'tool_calls', [])}")
        if chunk.content:
            content_parts.append(chunk.content)
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            tool_calls.extend(chunk.tool_calls)
    print(f"  最终内容: {''.join(content_parts)}")
    print(f"  最终 tool_calls: {tool_calls}")


async def test_langchain_no_stream():
    """LangChain 非流式测试"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatOpenAI(
        model=MODEL,
        temperature=0.3,
        streaming=False,
        api_key=API_KEY,
        base_url=API_BASE,
    )

    tools_lc = [
        {
            "type": "function",
            "function": {
                "name": "transfer_to_vehicle_agent",
                "description": "Ask agent 'vehicle_agent' for help",
                "parameters": {"properties": {}, "type": "object"},
            },
        },
    ]
    llm_with_tools = llm.bind_tools(tools_lc)

    print("\n--- 测试: LangChain ainvoke (非流式) + tools ---")
    messages = [
        SystemMessage(content="你是 AutoMind 车载助手。根据用户意图调用 transfer_to_vehicle_agent。"),
        HumanMessage(content="打开车窗"),
    ]
    response = await llm_with_tools.ainvoke(messages)
    print(f"  回复内容: {response.content}")
    print(f"  tool_calls: {response.tool_calls}")


if __name__ == "__main__":
    asyncio.run(test_direct_stream())
    asyncio.run(test_langchain_stream())
    asyncio.run(test_langchain_no_stream())
