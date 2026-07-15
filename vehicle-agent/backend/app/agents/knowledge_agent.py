"""
知识库检索子Agent
负责知识库检索、文档导入、来源标注

当 supervisor 判断用户问题涉及知识性内容时调用此 Agent：
- 保养手册、车辆操作说明、法规说明
- 个人档案、车辆状况、里程记录
- 保险信息、故障处理等

检索结果自带来源标注（[来源: xxx | 相关度: 0.xx]），
supervisor 在回复中应引用来源文档名。
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.config import settings
from app.models.llm import create_llm
from app.ragflow.knowledge_service import knowledge_service

KNOWLEDGE_PROMPT = """\
你是 AutoMind 的知识库检索助手 Agent，专门负责从知识库中查找信息。

你的能力：
- search_knowledge: 根据关键词检索知识库，返回带来源标注的结果
- import_knowledge: 将文本内容导入到知识库
- list_knowledge_bases: 列出当前可用的知识库

工作规则：
1. 收到任务后，先用 search_knowledge 检索相关内容
2. 检索结果中每条信息都附有来源标注（文档名+相关度）
3. 如果检索结果不足，可以尝试换个关键词再次检索
4. 返回结果时，保持来源标注信息完整，不要删除 [来源: xxx] 标记
5. 如果知识库中没有相关信息，如实告知"知识库中暂无相关内容"
6. 不要编造知识库中不存在的信息

重要：你的返回内容会直接展示给车主，所以：
- 保持来源标注清晰
- 只返回确实检索到的内容
- 内容要简洁易懂"""


@tool
def search_knowledge(query: str) -> str:
    """
    从知识库检索信息（支持混合检索：关键词+向量语义）

    Args:
        query: 查询关键词或问题描述（如"胎压标准值"、"保养记录"、"保险到期时间"）

    Returns:
        带来源标注的检索结果，格式如：
        查询结果（来自知识库）：
        1. [来源: vehicle_manual.md | 相关度: 0.85] 胎压标准值：前轮2.9bar...
    """
    result = knowledge_service.search(query)
    if not result:
        return "知识库中暂无与「{}」相关的内容。请尝试其他关键词，或说明这是知识库未覆盖的内容。".format(query)
    return result


@tool
def import_knowledge(name: str, content: str) -> str:
    """
    将文本内容导入到默认知识库

    Args:
        name: 文档名称（如"我的驾驶习惯"）
        content: 文档内容文本

    Returns:
        导入结果（含文档ID）
    """
    # 使用第一个可用的 dataset，或者创建一个
    dataset_ids = knowledge_service.dataset_ids
    if not dataset_ids:
        # 没有可用 dataset，创建一个默认的
        try:
            ds_id = knowledge_service.create_dataset(
                name="automind_user_imports",
                description="用户主动导入的知识内容",
            )
            dataset_id = ds_id
        except Exception as e:
            return f"导入失败：无法创建知识库 - {e}"
    else:
        dataset_id = dataset_ids[0]

    try:
        doc_id = knowledge_service.import_content(dataset_id, name, content)
        return f"导入成功！文档「{name}」已添加到知识库（ID: {doc_id}）。后续可以通过 search_knowledge 检索到这些内容。"
    except Exception as e:
        return f"导入失败：{e}"


@tool
def list_knowledge_bases() -> str:
    """
    列出当前所有可用的知识库及其内容概况

    Returns:
        知识库列表信息
    """
    datasets = knowledge_service.list_datasets()
    if not datasets:
        return "当前没有可用的知识库。可以通过 import_knowledge 工具创建和导入内容。"

    lines = ["当前可用知识库："]
    for ds in datasets:
        lines.append(
            f"- {ds['name']}（ID: {ds['id']}）："
            f"{ds.get('document_count', 0)} 个文档，"
            f"{ds.get('chunk_count', 0)} 个文本块"
        )
    return "\n".join(lines)


def create_knowledge_agent():
    """创建知识库检索子Agent"""
    return create_agent(
        model=create_llm(temperature=0.1),  # 低温度保证检索准确性
        tools=[search_knowledge, import_knowledge, list_knowledge_bases],
        name="knowledge_agent",
        system_prompt=KNOWLEDGE_PROMPT,
    )
