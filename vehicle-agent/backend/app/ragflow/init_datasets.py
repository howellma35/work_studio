"""
RAGFlow 知识库初始化脚本
首次启动时创建默认知识库并导入模拟数据
"""
from pathlib import Path

from loguru import logger

from app.ragflow.client import ragflow_client
from app.ragflow.knowledge_service import knowledge_service

# 模拟数据目录
MOCK_DATA_DIR = Path(__file__).parent / "mock_data"

# 知识库定义：名称 → 文件名
DATASET_DEFINITIONS = {
    "automind_personal_profile": ("个人档案", "personal_profile.md"),
    "automind_vehicle_info": ("车辆状况", "vehicle_status.md"),
    "automind_maintenance": ("保养记录", "maintenance_records.md"),
    "automind_driving_habits": ("驾驶习惯", "driving_habits.md"),
    "automind_vehicle_manual": ("车辆手册摘录", "vehicle_manual_excerpts.md"),
    "automind_preferences": ("用户偏好", "user_preferences.md"),
}


async def init_mock_knowledge() -> None:
    """
    初始化模拟知识数据

    仅在首次启动时执行（检查持久化状态中是否已有 dataset_ids）。
    如果已有，跳过初始化。
    """
    if not ragflow_client.available:
        logger.info("模拟知识数据初始化：RAGFlow 不可用，跳过")
        return

    # 检查是否已初始化
    initialized = ragflow_client.get_state("mock_data_initialized", "")
    if initialized == "true":
        logger.info("模拟知识数据已初始化，跳过重复导入")
        return

    logger.info("开始初始化模拟知识数据...")

    created_ids = []
    for ds_name, (display_name, filename) in DATASET_DEFINITIONS.items():
        filepath = MOCK_DATA_DIR / filename
        if not filepath.exists():
            logger.warning(f"模拟数据文件不存在: {filepath}")
            continue

        try:
            # 创建知识库
            ds_id = ragflow_client.create_dataset(
                name=ds_name,
                description=f"AutoMind {display_name} - 车载助手模拟知识数据",
            )
            created_ids.append(ds_id)
            logger.info(f"知识库已创建: {ds_name} (ID: {ds_id})")

            # 读取文件内容
            content = filepath.read_text(encoding="utf-8")

            # 创建文档（内联文本导入）
            doc_id = ragflow_client.create_document_from_text(
                dataset_id=ds_id,
                name=display_name,
                content=content,
            )
            logger.info(f"文档已导入: {display_name} → {ds_name} (doc_id: {doc_id})")

        except Exception as e:
            logger.warning(f"知识库 {ds_name} 创建/导入失败: {e}")

    # 持久化 dataset IDs
    if created_ids:
        ragflow_client.set_state("dataset_ids", ",".join(created_ids))
        knowledge_service._dataset_ids = created_ids
        logger.info(f"模拟知识数据初始化完成: {len(created_ids)} 个知识库")

    # 标记已初始化
    ragflow_client.set_state("mock_data_initialized", "true")
