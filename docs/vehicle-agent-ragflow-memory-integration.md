# RAGFlow 记忆功能集成到车机 Agent (AutoMind) 技术方案

> 版本: v1.0 | 日期: 2026-07-12 | 作者: AutoMind Team

---

## 1. 背景与目标

### 1.1 现状分析

**Vehicle-Agent (AutoMind)** 当前的记忆系统：

| 层级 | 实现 | 能力 | 局限 |
|------|------|------|------|
| 短期记忆 | LangGraph `AsyncSqliteSaver` | 多轮对话状态持久化、thread_id 隔离 | 仅保存对话状态，无主动提取 |
| 长期偏好 | ChromaDB 向量库 | 语义相似度召回 Top-3 偏好 | 仅支持单一 `user_preferences` 集合，无记忆分类 |
| 结构化档案 | SQLite `user_profiles` | JSON 格式的 KV 偏好存储 | 手动通过 `save_user_preference` 工具写入，无自动提取 |
| 提醒事项 | SQLite `reminders` | 待办提醒 CRUD | 仅支持精确时间提醒，无语义检索 |

**核心缺陷**：
1. **无自动记忆提取** — 偏好需要用户明确说"记住XXX"或 Agent 主动调用工具才能保存，大量隐含信息（如"我有点冷"→偏好温度较高、"今天开了2小时高速去苏州"→常跑路线）被遗漏
2. **无记忆类型区分** — 所有偏好混在一个向量集合里，事实性知识（语义记忆）、个人经历（情景记忆）、操作流程（程序记忆）无差别存储和召回
3. **无时间有效性** — 记忆条目永久有效，无法表达"明天下午3点开会"这类有时效的信息
4. **无遗忘机制** — 旧记忆不会过期或被淘汰，长期使用后向量库膨胀导致召回质量下降
5. **无混合搜索** — 仅使用纯向量检索，关键词匹配缺失，精确术语/地名召回率低
6. **记忆写入链路不完整** — `save_user_preference` 工具只能由 reminder_agent 调用，其他子Agent无法写入记忆

### 1.2 RAGFlow 记忆系统参考

RAGFlow 实现了一套企业级多类型记忆系统，核心特性：

1. **四种记忆类型**：
   - `raw` — 原始对话记录，不做提取
   - `semantic` — 语义记忆：事实性知识、概念、关系（如"苏州市在江苏省"）
   - `episodic` — 情景记忆：具体经历、事件、个人故事（如"上周六开车去了苏州"）
   - `procedural` — 程序记忆：流程、步骤、操作方法（如"导航回家的路线是XX路转XX路"）

2. **LLM 自动提取** — 每轮对话结束后，用专门的 Prompt 让 LLM 从对话中提取结构化记忆条目（含 content/valid_at/invalid_at）

3. **时间有效性** — 每条记忆有生效时间(`valid_at`)和失效时间(`invalid_at`)，支持时间感知的召回

4. **FIFO 遗忘策略** — 记忆库大小超限后，按时间顺序淘汰最旧的记忆

5. **混合检索** — 关键词全文检索 + 语义向量检索，加权融合排序 (`keywords_similarity_weight` 默认 0.7)

6. **异步提取管线** — 原始消息先嵌入入库，异步任务队列进行 LLM 提取，避免阻塞对话

### 1.3 目标

将 RAGFlow 记忆系统的核心设计理念移植到 AutoMind 车机 Agent，实现：

- ✅ **自动记忆提取**：每轮对话后 LLM 自动提取有价值的记忆，无需用户显式指令
- ✅ **多类型记忆**：区分语义/情景/程序/偏好四种记忆类型，分别存储和检索
- ✅ **时间有效性**：支持记忆的生效/失效时间，过期记忆自然衰减
- ✅ **混合检索**：关键词 + 向量双路召回，提升精确匹配率
- ✅ **遗忘策略**：FIFO + 时间衰减，控制记忆库规模
- ✅ **车机场景适配**：针对驾驶场景优化记忆类型和提取规则
- ✅ **渐进式集成**：不破坏现有架构，分阶段上线

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CopilotKit / SSE                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Supervisor Agent (LangGraph)                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ dynamic_prompt middleware (_build_prompt)            │    │
│  │  → memory_manager.get_context(user_id, query)        │    │
│  │  → 注入记忆上下文到 system prompt                    │    │
│  └──────────┬──────────────────────────┬───────────────┘    │
│             │                          │                    │
│  ┌──────────▼──────────┐  ┌────────────▼──────────────┐     │
│  │  Sub-Agents         │  │  Post-Conversation Hook    │     │
│  │  (nav/media/veh/    │  │  (after_agent hook)        │     │
│  │   weather/reminder) │  │  → 触发记忆自动提取        │     │
│  └─────────────────────┘  └────────────┬──────────────┘     │
└────────────────────────────────────────┼────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────┐
│                  Memory Manager (重构)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Short-Term   │  │ Long-Term    │  │ Auto-Extraction  │   │
│  │ (Checkpointer│  │ (Multi-Store)│  │ Pipeline         │   │
│  │  保持不变)    │  │              │  │                  │   │
│  │              │  │ ┌──────────┐ │  │ ┌──────────────┐ │   │
│  │              │  │ │ ChromaDB │ │  │ │ LLM Extractor│ │   │
│  │              │  │ │ (vector) │◄├─┘ │ │ (async)      │ │   │
│  │              │  │ └────┬─────┘ │  │ └──────┬───────┘ │   │
│  │              │  │      │       │  │        │         │   │
│  │              │  │ ┌────▼─────┐ │  │ ┌──────▼───────┐ │   │
│  │              │  │ │ SQLite   │◄├──┤ │ Extraction   │ │   │
│  │              │  │ │ (meta +  │ │  │ │ Prompt       │ │   │
│  │              │  │ │  profile │ │  │ │ (车机定制)    │ │   │
│  │              │  │ │  +remind)│ │  │ └──────────────┘ │   │
│  │              │  │ └──────────┘ │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 记忆分类（车机场景适配版）

基于 RAGFlow 的四种记忆类型，结合车机场景进行适配：

| 记忆类型 | 车机场景示例 | 存储方式 | 生命周期 |
|----------|-------------|---------|---------|
| **semantic（语义记忆）** | "用户家在上海市浦东新区"、"车主姓李"、"公司地址是XX"、"孩子在XX小学上学" | ChromaDB 向量 + SQLite 元数据 | 长期，手动更新或失效时间到达 |
| **episodic（情景记忆）** | "上周六开车去了苏州自驾游"、"昨天在高速上堵了2小时"、"上周去4S店做了保养" | ChromaDB 向量 + SQLite 元数据 | 中期，有失效时间，FIFO淘汰 |
| **procedural（程序记忆）** | "导航去公司通常走中环"、"开长途前习惯检查胎压"、"连接蓝牙后自动播放音乐" | ChromaDB 向量 + SQLite 元数据 | 长期，可被新流程覆盖 |
| **preference（偏好记忆）** | "空调偏好24度"、"喜欢听周杰伦"、"导航偏好高速优先"、"座椅位置靠后" | ChromaDB 向量 + SQLite profile（保持现有） | 长期，可更新覆盖 |
| **raw（原始对话）** | 完整对话轮次 | SQLite 或可选向量 | 短期，FIFO 淘汰（默认保留最近 N 轮） |
| **reminder（提醒事项）** | "明天下午3点接孩子"、"下周去保养" | SQLite（保持现有） | 到期自动标记完成 |

### 2.3 记忆条目数据模型

```python
class MemoryEntry(BaseModel):
    """统一记忆条目模型"""
    id: str                    # 唯一标识 {user_id}_{uuid[:8]}
    user_id: str               # 用户标识
    memory_type: Literal[      # 记忆类型
        "semantic", "episodic", "procedural",
        "preference", "raw", "reminder"
    ]
    content: str               # 记忆文本内容
    source_id: str = ""        # 来源原始消息ID (提取的记忆指向raw消息)
    category: str = ""         # 分类标签 (navigation/media/climate/vehicle/general)
    # 时间有效性
    valid_at: datetime | None = None    # 生效时间
    invalid_at: datetime | None = None  # 失效时间
    created_at: datetime               # 创建时间
    updated_at: datetime               # 最后更新时间
    # 状态
    status: Literal["active", "forgotten", "expired"] = "active"
    forget_at: datetime | None = None  # 遗忘时间
    importance: float = 0.5            # 重要性评分 0-1 (影响召回权重和淘汰优先级)
    # 元数据
    metadata: dict = {}        # 扩展字段 (session_id, agent_id, 置信度等)
    # 向量
    embedding: list[float] | None = None  # 内容的向量嵌入
```

---

## 3. 核心模块设计

### 3.1 记忆存储层重构

#### 3.1.1 ChromaDB 集合重新设计

**现有方案**：单一集合 `user_preferences`，metadata 只有 `user_id` 和 `category`

**新方案**：按记忆类型分集合，统一元数据结构

```python
# memory/stores/vector_store.py
COLLECTIONS = {
    "semantic": {
        "name": "memory_semantic",
        "description": "语义记忆 - 事实性知识与用户基本信息",
    },
    "episodic": {
        "name": "memory_episodic",
        "description": "情景记忆 - 具体经历与事件",
    },
    "procedural": {
        "name": "memory_procedural",
        "description": "程序记忆 - 操作流程与习惯",
    },
    "preference": {
        "name": "memory_preference",
        "description": "偏好记忆 - 用户偏好设置（兼容现有）",
    },
}

# 每条向量文档的 metadata 统一结构：
METADATA_SCHEMA = {
    "user_id": str,           # 用户ID
    "memory_type": str,       # 记忆类型
    "category": str,          # 业务分类
    "valid_at": str,          # ISO8601 生效时间
    "invalid_at": str,        # ISO8601 失效时间 (空字符串表示永久)
    "created_at": str,        # 创建时间
    "importance": float,      # 重要性 0-1
    "source_id": str,         # 来源消息ID
    "status": str,            # active/forgotten/expired
}
```

#### 3.1.2 SQLite 表扩展

```sql
-- 现有表保持不变：user_profiles, reminders

-- 新增：记忆元数据表（冗余存储，支持精确查询和过滤）
CREATE TABLE IF NOT EXISTS memory_entries (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    memory_type TEXT NOT NULL,  -- semantic/episodic/procedural/preference/raw
    category    TEXT DEFAULT '',
    content     TEXT NOT NULL,
    source_id   TEXT DEFAULT '',
    valid_at    TEXT,           -- ISO8601 或 NULL
    invalid_at  TEXT,           -- ISO8601 或 NULL
    status      TEXT DEFAULT 'active',  -- active/forgotten/expired
    importance  REAL DEFAULT 0.5,
    metadata    TEXT DEFAULT '{}',     -- JSON 扩展字段
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新增：原始对话记录表（用于 raw 记忆和回溯）
CREATE TABLE IF NOT EXISTS conversation_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    thread_id   TEXT NOT NULL,     -- LangGraph thread_id
    role        TEXT NOT NULL,     -- user/assistant/tool
    content     TEXT NOT NULL,
    agent_name  TEXT DEFAULT '',   -- 哪个子Agent处理的
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新增：记忆提取任务表（异步提取状态追踪）
CREATE TABLE IF NOT EXISTS memory_extraction_tasks (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    conversation_id INTEGER NOT NULL,  -- 关联 conversation_log
    status          TEXT DEFAULT 'pending',  -- pending/processing/completed/failed
    extracted_count INTEGER DEFAULT 0,
    error_msg       TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memory_user_type ON memory_entries(user_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_entries(status, invalid_at);
CREATE INDEX IF NOT EXISTS idx_conv_user_time ON conversation_log(user_id, created_at);
```

### 3.2 LLM 自动记忆提取管线

#### 3.2.1 提取时机

采用**轮次后置触发**策略：

1. **每轮对话结束后**（Supervisor 最终回复用户后），触发异步记忆提取
2. 提取输入：本轮的 `(user_input, assistant_response)` 组合
3. 提取过程不阻塞对话响应（在 LangGraph 的 `after_agent` 钩子或后台任务中执行）
4. 为避免提取过于频繁，可设置：仅当对话内容足够"有信息量"时才触发（简单问候、确认类回复跳过）

#### 3.2.2 车机场景定制的提取 Prompt

基于 RAGFlow 的 `PromptAssembler`，针对车机场景优化：

```python
# memory/extraction/prompt.py

MEMORY_EXTRACTION_SYSTEM_PROMPT = """\
你是一个车机智能助手的**记忆提取专家**。你的任务是分析车主与车载助手的对话，提取对未来服务有价值的结构化记忆。

## 记忆类型说明

{type_instructions}

## 车机场景提取规则

1. **用户画像相关**：提取车主的个人信息（姓名、家庭住址、公司地址、常用目的地、家庭成员等）
2. **驾驶习惯相关**：提取常跑路线、驾驶偏好（速度/车道/路线偏好）、座椅/空调/音乐习惯
3. **车辆相关**：提取保养记录、车辆问题、加油/充电习惯
4. **日程/计划相关**：提取明确的时间-事件关联（如"明天下午3点去机场"）
5. **情感偏好**：提取对音乐/电台/新闻的喜好，对交互风格的偏好
6. **临时情境**：提取当前行程信息（出发地、目的地、同行人、目的）

## 不提取的内容

- 简单问候和寒暄（"你好"、"谢谢"）
- 纯操作指令（"打开空调"、"导航去XX"）→ 这些已经通过工具执行，不需要记忆
- 通用常识（"北京是中国首都"）→ 这不属于用户个人记忆
- 不确定或模糊的信息 → 不要猜测，只提取明确表达的内容
- 敏感隐私信息（密码、身份证号、银行卡号）→ 不要提取

## 输出要求

1. 输出必须是合法的 JSON 格式，不要有额外解释
2. 每个提取条目包含：content、memory_type、category、valid_at、invalid_at、importance
3. 时间格式：ISO 8601（YYYY-MM-DD HH:MM:SS）
4. 如果对话中没有值得提取的记忆，返回空对象 {{}}
5. 每种类型最多提取 3 条（总共不超过 8 条）
6. importance 评分标准：
   - 0.8-1.0：长期偏好、重要个人信息（家庭地址、音乐偏好）
   - 0.5-0.7：中期习惯、近期行程、有用的经历
   - 0.2-0.4：临时情境、短期计划
   - < 0.2：价值不大，不提取

**输出格式：**
```json
{{
  "memories": [
    {{
      "content": "清晰的记忆描述",
      "memory_type": "semantic|episodic|procedural|preference",
      "category": "navigation|media|climate|vehicle|schedule|general",
      "valid_at": "2026-07-12 14:00:00 或空字符串",
      "invalid_at": "失效时间或空字符串（永久记忆）",
      "importance": 0.0-1.0
    }}
  ]
}}
```
"""

SEMANTIC_TYPE_INSTRUCTION = """\
**语义记忆 (semantic)**：关于用户和世界的事实性信息
- 内容：用户的基本信息、家庭/公司地址、常去地点、车辆信息、人际关系
- 特点：相对稳定、长期有效、可以被未来对话反复引用
- 示例：
  - "用户家在上海市浦东新区张江镇" → valid_at=now, invalid_at="", importance=0.9
  - "车主的车是特斯拉Model Y，车牌号沪AXXXXX" → valid_at=now, invalid_at="", importance=0.8
  - "用户有一个7岁的儿子" → valid_at=now, invalid_at="", importance=0.7
"""

EPISODIC_TYPE_INSTRUCTION = """\
**情景记忆 (episodic)**：具体的事件和经历
- 内容：出行记录、车辆事件（保养/故障/事故）、具体对话场景
- 特点：有明确的时间点、可能随时间失去价值、为上下文连贯性服务
- 示例：
  - "2026年7月10日用户开车去了苏州自驾游，走了京沪高速" → valid_at=该时间, invalid_at=30天后, importance=0.5
  - "用户昨天反映刹车有异响" → valid_at=昨天, invalid_at=保养完成后, importance=0.7
"""

PROCEDURAL_TYPE_INSTRUCTION = """\
**程序记忆 (procedural)**：操作习惯和流程
- 内容：导航偏好路线、上车后的固定操作序列、常用功能组合
- 特点：可执行、目标导向、反映用户行为模式
- 示例：
  - "用户导航去公司时偏好走中环比外环" → valid_at=now, invalid_at="", importance=0.7
  - "用户上车后习惯先连接蓝牙再开音乐" → valid_at=now, invalid_at="", importance=0.6
"""

PREFERENCE_TYPE_INSTRUCTION = """\
**偏好记忆 (preference)**：用户的偏好和设置
- 内容：空调温度、音乐类型/歌手、座椅位置、导航偏好、驾驶风格偏好
- 特点：直接影响用户体验、可被主动应用
- 示例：
  - "用户空调温度偏好24度，风量二档" → valid_at=now, invalid_at="", importance=0.9
  - "用户喜欢听周杰伦和林俊杰的歌" → valid_at=now, invalid_at="", importance=0.8
  - "用户导航偏好高速优先，避开拥堵" → valid_at=now, invalid_at="", importance=0.8
"""
```

#### 3.2.3 提取流程

```
每轮对话结束 (Supervisor 发送最终响应后)
    │
    ├─→ 1. 组装 conversation_content = f"User: {user_input}\nAssistant: {assistant_response}"
    │
    ├─→ 2. 快速判断是否需要提取（关键词/长度/意图启发式过滤）
    │     - 回复长度 < 20 字 → 跳过
    │     - 纯确认类回复（"好的"、"已为您设置"）→ 跳过
    │     - 用户输入是纯操作指令 → 跳过
    │
    ├─→ 3. 调用 LLM 进行记忆提取（后台 asyncio.create_task）
    │     - system: MEMORY_EXTRACTION_SYSTEM_PROMPT (拼装类型指令)
    │     - user: f"当前时间: {now}\n\n对话:\n{conversation_content}"
    │     - temperature: 0.1 (低温度保证稳定性)
    │     - model: 使用与主对话相同的 LLM（复用配置）
    │
    ├─→ 4. 解析 LLM 返回的 JSON
    │     - 容错处理：JSON 解析失败则记录日志，不重试
    │     - 过滤校验：必填字段检查、类型枚举校验、时间格式校验
    │
    ├─→ 5. 去重检查（关键！）
    │     - 对每条新记忆，与同类现有记忆做相似度比对
    │     - 如果相似度 > 0.9（语义相似），视为更新而非新增
    │     - 更新策略：importance 取较高值，content 取较新的表述
    │
    ├─→ 6. 批量写入存储
    │     - 生成向量嵌入（复用现有 embed_text）
    │     - 写入 ChromaDB 对应集合
    │     - 写入 SQLite memory_entries 表
    │     - 同步更新 user_profiles（如果是 preference 类型）
    │
    └─→ 7. 执行遗忘策略检查
          - 检查各类型记忆总大小
          - 超限时按 importance 升序 + 创建时间升序淘汰
```

#### 3.2.4 提取管线代码框架

```python
# memory/extraction/extractor.py

class MemoryExtractor:
    """LLM 驱动的自动记忆提取器"""

    def __init__(self, llm, embeddings, vector_store, db_store):
        self.llm = llm                    # ChatOpenAI 实例
        self.embeddings = embeddings      # OpenAIEmbeddings 实例
        self.vector_store = vector_store  # ChromaDB 多集合存储
        self.db_store = db_store          # SQLite 元数据存储
        self.dedup_threshold = 0.9        # 去重相似度阈值

    async def extract_and_save(
        self,
        user_id: str,
        user_input: str,
        assistant_response: str,
        session_id: str = "",
        thread_id: str = "",
    ) -> list[MemoryEntry]:
        """从一轮对话中提取记忆并保存"""

        # 1. 快速过滤
        if not self._should_extract(user_input, assistant_response):
            return []

        # 2. 组装 prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_input, assistant_response)

        # 3. 调用 LLM
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            result = self._parse_response(response.content)
        except Exception as e:
            logger.warning(f"记忆提取 LLM 调用失败: {e}")
            return []

        if not result or not result.get("memories"):
            return []

        # 4. 去重 + 构建条目
        saved_entries = []
        for item in result["memories"]:
            entry = self._build_entry(user_id, item, session_id, thread_id)
            if entry is None:
                continue

            # 去重检查
            existing = await self._find_similar(entry)
            if existing:
                # 更新已有记忆
                entry = await self._merge_entries(existing, entry)

            # 5. 嵌入 + 存储
            await self._save_entry(entry)
            saved_entries.append(entry)

        # 6. 遗忘策略
        await self._apply_forgetting_policy(user_id)

        logger.info(f"记忆提取完成: user={user_id}, 新增/更新 {len(saved_entries)} 条")
        return saved_entries

    def _should_extract(self, user_input: str, response: str) -> bool:
        """启发式判断是否值得提取"""
        # 过短的回复不提取
        if len(response) < 15 and len(user_input) < 10:
            return False
        # 纯确认/问候模式
        skip_patterns = ["好的", "明白了", "已为您", "没问题", "不客气", "你好", "早上好"]
        if any(p in response and len(response) < 30 for p in skip_patterns):
            return False
        return True

    async def _find_similar(self, entry: MemoryEntry) -> MemoryEntry | None:
        """查找是否已有高度相似的记忆"""
        results = self.vector_store.query(
            collection=entry.memory_type,
            user_id=entry.user_id,
            query_text=entry.content,
            top_k=1,
        )
        if results and results[0]["distance"] < (1 - self.dedup_threshold):
            return self.db_store.get_entry(results[0]["id"])
        return None

    async def _merge_entries(self, old: MemoryEntry, new: MemoryEntry) -> MemoryEntry:
        """合并相似记忆：保留高 importance，更新 content 和时间"""
        return MemoryEntry(
            id=old.id,
            user_id=old.user_id,
            memory_type=old.memory_type,
            content=new.content if new.importance >= old.importance else old.content,
            category=new.category or old.category,
            valid_at=new.valid_at or old.valid_at,
            invalid_at=new.invalid_at or old.invalid_at,
            importance=max(old.importance, new.importance),
            created_at=old.created_at,
            updated_at=datetime.now(),
            status="active",
            metadata={**old.metadata, **new.metadata},
        )

    async def _apply_forgetting_policy(self, user_id: str):
        """FIFO + importance 加权遗忘策略"""
        MAX_PER_TYPE = {
            "semantic": 200,
            "episodic": 500,
            "procedural": 100,
            "preference": 100,
        }
        for mtype, max_count in MAX_PER_TYPE.items():
            entries = self.db_store.list_active(user_id, mtype)
            if len(entries) <= max_count:
                continue
            # 按 (importance ASC, created_at ASC) 排序，淘汰最旧最不重要的
            to_delete = sorted(entries, key=lambda e: (e.importance, e.created_at))
            to_delete = to_delete[:len(entries) - max_count]
            for entry in to_delete:
                await self._forget_entry(entry)
```

### 3.3 混合检索引擎

#### 3.3.1 双路召回 + 加权融合

```python
# memory/retrieval/hybrid_retriever.py

class HybridRetriever:
    """混合检索：向量语义搜索 + 关键词搜索 + 加权融合"""

    def __init__(self, vector_store, db_store, embeddings):
        self.vector_store = vector_store
        self.db_store = db_store
        self.embeddings = embeddings
        # 权重配置（参考 RAGFlow 默认 keywords_similarity_weight=0.7，
        # 注意 RAGFlow 内部权重顺序约定为 (text_weight, vector_weight)，
        # 即 keywords_similarity_weight=0.7 实际作用于向量侧。
        # 车机场景：地名/人名/品牌名等精确术语较多，适度提高关键词权重到0.4）
        self.keywords_weight = 0.4   # 关键词 (BM25/全文) 权重
        self.vector_weight = 0.6     # 向量语义权重

    async def recall(
        self,
        user_id: str,
        query: str,
        memory_types: list[str] | None = None,  # None = 所有类型
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        categories: list[str] | None = None,
        include_expired: bool = False,
    ) -> list[RetrievedMemory]:
        """
        混合检索相关记忆

        Args:
            user_id: 用户ID
            query: 查询文本
            memory_types: 限定记忆类型
            top_k: 返回数量
            similarity_threshold: 最低相似度
            categories: 限定分类
            include_expired: 是否包含已过期记忆

        Returns:
            排序后的记忆列表，每个包含融合分数
        """
        types = memory_types or ["semantic", "episodic", "procedural", "preference"]

        # 1. 向量检索（跨所有指定类型集合）
        vector_results = await self._vector_search(
            user_id, query, types, top_k=top_k * 2, categories=categories
        )

        # 2. 关键词检索（在 SQLite 中做 LIKE/FTS 搜索）
        keyword_results = await self._keyword_search(
            user_id, query, types, top_k=top_k * 2, categories=categories
        )

        # 3. 加权融合 (RRF 或 Weighted Sum)
        fused = self._weighted_fusion(vector_results, keyword_results)

        # 4. 过滤过期和低相似度
        now = datetime.now()
        filtered = []
        for item in fused:
            if not include_expired and item.invalid_at and item.invalid_at < now:
                continue
            if item.score < similarity_threshold:
                continue
            filtered.append(item)

        # 5. 时间衰减：近期记忆加分
        filtered = self._apply_time_decay(filtered, now)

        # 6. 按重要性加权
        for item in filtered:
            item.final_score = item.score * (0.6 + 0.4 * item.importance)

        filtered.sort(key=lambda x: x.final_score, reverse=True)
        return filtered[:top_k]

    async def _vector_search(self, user_id, query, types, top_k, categories):
        """向量语义检索"""
        vector = self.embeddings.embed_query(query)
        all_results = []
        for mtype in types:
            results = self.vector_store.query(
                collection=mtype,
                user_id=user_id,
                query_embedding=vector,
                top_k=top_k,
                filter_categories=categories,
            )
            for r in results:
                r["memory_type"] = mtype
                r["vector_score"] = r["distance"]
            all_results.extend(results)
        return all_results

    async def _keyword_search(self, user_id, query, types, top_k, categories):
        """关键词全文检索（SQLite FTS 或 LIKE）"""
        # 提取关键词（简单分词：按空格和标点，中文可按字符 n-gram 或用 jieba）
        keywords = self._extract_keywords(query)
        results = self.db_store.keyword_search(
            user_id=user_id,
            keywords=keywords,
            memory_types=types,
            categories=categories,
            top_k=top_k,
        )
        return results

    def _weighted_fusion(self, vector_results, keyword_results):
        """加权融合：final_score = w1 * vector_score + w2 * keyword_score"""
        # 归一化分数到 [0,1]
        scores = {}

        # 向量分数（distance 越小越相似，需要转换）
        for r in vector_results:
            mid = r["id"]
            scores[mid] = scores.get(mid, {"item": r, "v_score": 0, "k_score": 0})
            scores[mid]["v_score"] = 1.0 - r["distance"]  # 转成相似度

        # 关键词分数 (基于词频和覆盖率)
        for r in keyword_results:
            mid = r["id"]
            scores[mid] = scores.get(mid, {"item": r, "v_score": 0, "k_score": 0})
            scores[mid]["k_score"] = r["keyword_score"]

        # 加权求和
        results = []
        for mid, data in scores.items():
            item = data["item"]
            score = (self.vector_weight * data["v_score"] +
                     self.keywords_weight * data["k_score"])
            item["score"] = score
            results.append(item)

        return results

    def _apply_time_decay(self, results, now):
        """时间衰减：越近的记忆分数越高"""
        HALF_LIFE_DAYS = 90  # 90天半衰期
        for item in results:
            age_days = (now - item.created_at).total_seconds() / 86400
            decay = 1.0 / (1.0 + age_days / HALF_LIFE_DAYS)
            # 对于有 valid_at 的记忆，在有效期内不衰减
            if item.valid_at and item.invalid_at:
                if item.valid_at <= now <= item.invalid_at:
                    decay = 1.0  # 在有效期内
                elif now > item.invalid_at:
                    decay *= 0.3  # 已过期，大幅降权
            item.score *= decay
        return results
```

### 3.4 Supervisor Prompt 中记忆上下文注入优化

**现有方案**：注入 `user_profile` (dict) + `recalled_preferences` (list[str]) + `pending_reminders` (list[dict])

**新方案**：按记忆类型结构化注入，增加情景和程序性记忆

```python
# graph/supervisor.py 中的 _build_prompt 改造

SUPERVISOR_PROMPT = """\
你是 AutoMind，一个智能车载助手。你的核心职责是理解车主需求，调用合适的专业子Agent工具完成任务，并用自然语音简短回复。

{routing_description}

## 你的工作流程
...（保持现有工作流程描述不变）...

## 用户记忆上下文
请基于以下记忆信息提供个性化服务：

### 用户画像（语义记忆）
{semantic_memories}

### 用户偏好（偏好记忆）
{preference_memories}

### 行为习惯（程序记忆）
{procedural_memories}

### 近期行程与事件（情景记忆）
{episodic_memories}

### 待办提醒
{pending_reminders}

## 记忆使用规则
1. 利用用户画像进行个性化称呼和推荐（如知道姓氏可自然称呼）
2. 主动应用偏好设置（如空调温度、音乐偏好），不需要每次询问
3. 参考行为习惯提供建议（如"按您常走的中环路线为您导航"）
4. 情景记忆用于保持对话连贯性（如之前去过的地方、提到的计划）
5. 如果用户纠正了你的记忆，接受纠正并会在后续学习更新
6. 不要主动提及"根据记忆"或"我记得"，自然地融入对话

## 交互规范
- 用简洁、自然的口语回复，适合驾驶场景（单次回复控制在 50 字以内）
...（其余保持不变）...
"""

@dynamic_prompt
def _build_prompt(request) -> str:
    state = request.state
    user_id = state.get("user_id", settings.DEFAULT_VEHICLE_USER_ID)
    messages = state.get("messages", [])
    user_message = messages[-1].content if messages else ""

    # 混合检索：根据当前查询召回相关记忆
    recalled = await hybrid_retriever.recall(
        user_id=user_id,
        query=user_message,
        top_k_per_type={"semantic": 3, "preference": 3, "procedural": 2, "episodic": 2},
    )

    # 按类型分组格式化
    context = memory_manager.get_context(user_id, user_message, recalled)

    return SUPERVISOR_PROMPT.format(
        routing_description=ROUTING_DESCRIPTION,
        semantic_memories=context.format_semantic(),
        preference_memories=context.format_preferences(),
        procedural_memories=context.format_procedural(),
        episodic_memories=context.format_episodic(),
        pending_reminders=context.format_reminders(),
    )
```

### 3.5 记忆管理器 API 重构

```python
# memory/manager.py (重构)

class MemoryManager:
    """重构后的统一记忆管理器"""

    def __init__(self):
        self.checkpointer = short_term_memory  # 保持现有
        self.vector_store = VectorStore()       # 多集合 ChromaDB
        self.db_store = DBStore()               # SQLite 元数据
        self.embeddings = EmbeddingService()    # 嵌入服务
        self.retriever = HybridRetriever(       # 混合检索
            self.vector_store, self.db_store, self.embeddings
        )
        self.extractor = MemoryExtractor(       # LLM 提取器
            llm=None,  # 延迟初始化
            embeddings=self.embeddings,
            vector_store=self.vector_store,
            db_store=self.db_store,
        )

    async def get_context(
        self, user_id: str, query: str, recalled: list[RetrievedMemory] | None = None
    ) -> MemoryContext:
        """
        获取对话记忆上下文

        Args:
            user_id: 用户ID
            query: 当前用户输入
            recalled: 预召回的记忆（由 retriever 传入）
        """
        if recalled is None:
            recalled = await self.retriever.recall(user_id, query)

        # 始终获取用户档案（全量，用于基本信息）
        profile = self.db_store.get_profile(user_id)

        # 获取待处理提醒
        reminders = self.db_store.get_reminders(user_id)

        # 按类型分组召回结果
        by_type = {"semantic": [], "episodic": [], "procedural": [], "preference": []}
        for mem in recalled:
            by_type[mem.memory_type].append(mem.content)

        return MemoryContext(
            semantic=by_type["semantic"],
            preference=by_type["preference"],
            procedural=by_type["procedural"],
            episodic=by_type["episodic"],
            profile=profile,
            reminders=reminders,
        )

    async def post_conversation_hook(
        self,
        user_id: str,
        user_input: str,
        assistant_response: str,
        session_id: str = "",
        thread_id: str = "",
    ):
        """
        对话轮次后置钩子 — 触发异步记忆提取

        在 Supervisor 发送最终响应后调用，不阻塞主流程。
        """
        # 记录原始对话
        self.db_store.log_conversation(
            user_id=user_id, session_id=session_id, thread_id=thread_id,
            role="user", content=user_input,
        )
        self.db_store.log_conversation(
            user_id=user_id, session_id=session_id, thread_id=thread_id,
            role="assistant", content=assistant_response,
        )

        # 异步触发提取
        asyncio.create_task(
            self.extractor.extract_and_save(
                user_id=user_id,
                user_input=user_input,
                assistant_response=assistant_response,
                session_id=session_id,
                thread_id=thread_id,
            )
        )

    # ===== 显式记忆操作（保持兼容现有工具）=====

    def save_preference(self, user_id: str, category: str, value: str) -> None:
        """显式保存偏好（供 reminder_agent 工具调用，兼容现有 API）"""
        content = f"用户的{category}偏好: {value}"
        entry = MemoryEntry(
            id=f"{user_id}_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            memory_type="preference",
            content=content,
            category=category,
            importance=0.9,
        )
        asyncio.create_task(self._save_entry(entry))
        # 同步更新 profile（保持兼容）
        self.update_profile(user_id, {category: value})

    def update_profile(self, user_id: str, updates: dict) -> None:
        """更新用户结构化档案（保持兼容）"""
        self.db_store.update_profile(user_id, updates)

    def add_reminder(self, user_id: str, content: str, remind_at: str) -> str:
        """添加提醒（保持兼容）"""
        return self.db_store.add_reminder(user_id, content, remind_at)
```

### 3.6 对话日志与记忆提取接入点

在 Supervisor 处理完每轮对话后，需要调用 `post_conversation_hook`。接入方式：

**方案A：LangGraph 后置节点（推荐）**

```python
# graph/supervisor.py 修改 build_supervisor_graph

from langgraph.graph import END
from app.memory.post_hook import memory_post_hook_node

# 在 create_agent 构建的图外面包一层，添加后置节点
def build_supervisor_graph_with_memory(frontend_tools=None):
    inner_graph = build_supervisor_graph(frontend_tools)

    # 添加后置边：Supervisor → post_hook → END
    builder = StateGraph(AutoMindState)
    builder.add_node("agent", inner_graph)
    builder.add_node("memory_hook", memory_post_hook_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", "memory_hook")
    builder.add_edge("memory_hook", END)

    return builder.compile(
        checkpointer=checkpointer,
    )
```

**方案B：在 FastAPI 端点层触发（更简单，不改图结构）**

```python
# main.py 中 copilotkit 端点处理后触发

@app.post("/copilotkit")
async def copilotkit_endpoint(request: Request):
    # ... 现有处理逻辑 ...

    # 包装响应：在 SSE 流结束后触发记忆提取
    async def response_stream_with_memory():
        user_input = ""  # 从请求中提取
        assistant_response_parts = []

        async for chunk in original_response_iterator():
            assistant_response_parts.append(chunk)
            yield chunk

        # 流结束后，异步触发记忆提取
        full_response = "".join(assistant_response_parts)
        if user_input and full_response:
            await memory_manager.post_conversation_hook(
                user_id=current_user_id,
                user_input=user_input,
                assistant_response=full_response,
                session_id=session_id,
                thread_id=thread_id,
            )

    return StreamingResponse(response_stream_with_memory(), ...)
```

**推荐采用方案B**，因为：
1. 不需要改动 LangGraph 图结构，侵入性小
2. 能拿到完整的对话轮次（用户输入 + 完整助手回复）
3. 在 FastAPI 层做异步任务管理更方便

---

## 4. 文件结构

集成后的 `backend/app/memory/` 目录结构：

```
memory/
├── __init__.py
├── manager.py              # 重构：统一入口（MemoryManager）
├── config.py               # 新增：记忆模块配置（权重、阈值、上限等）
├── models.py               # 新增：MemoryEntry / MemoryContext / RetrievedMemory 数据模型
├── short_term.py           # 保持：LangGraph checkpointer（不改）
├── stores/                 # 新增：存储层
│   ├── __init__.py
│   ├── vector_store.py     # 新增：ChromaDB 多集合封装
│   └── db_store.py         # 新增：SQLite 元数据/对话日志/提醒 封装
├── retrieval/              # 新增：检索层
│   ├── __init__.py
│   ├── hybrid_retriever.py # 新增：混合检索引擎（向量+关键词+融合）
│   └── keywords.py         # 新增：中文分词/关键词提取
├── extraction/             # 新增：自动提取层
│   ├── __init__.py
│   ├── extractor.py        # 新增：LLM 记忆提取器
│   └── prompt.py           # 新增：车机场景定制的提取 Prompt
└── long_term.py            # 保留：现有长期记忆（重构后逻辑迁移到 stores/，保留兼容过渡）
```

---

## 5. 配置扩展

在 `config.py` 中新增记忆相关配置：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # ===== 记忆模块扩展配置 =====
    MEMORY_AUTO_EXTRACT: bool = True           # 是否启用自动记忆提取
    MEMORY_EXTRACT_MODEL: str = ""             # 提取用的模型（空=复用LLM_MODEL）
    MEMORY_EXTRACT_TEMPERATURE: float = 0.1    # 提取温度（低温度保稳定）
    MEMORY_TOP_K: int = 5                      # 默认召回数量
    MEMORY_KEYWORDS_WEIGHT: float = 0.4        # 关键词检索权重（BM25/全文）
    MEMORY_VECTOR_WEIGHT: float = 0.6          # 向量检索权重
    MEMORY_SIMILARITY_THRESHOLD: float = 0.3   # 相似度阈值
    MEMORY_DEDUP_THRESHOLD: float = 0.9        # 去重相似度阈值
    MEMORY_MAX_PER_TYPE: dict = {              # 各类型记忆上限
        "semantic": 200,
        "episodic": 500,
        "procedural": 100,
        "preference": 100,
    }
    MEMORY_TIME_DECAY_HALF_LIFE: int = 90      # 时间衰减半衰期（天）
    MEMORY_CONVERSATION_LOG_LIMIT: int = 1000  # 对话日志保留条数
    MEMORY_EXTRACT_MIN_RESPONSE_LEN: int = 15  # 触发提取的最小回复长度
```

---

## 6. 渐进式实施计划

### Phase 1：存储层重构 + 混合检索（1-2天）

**目标**：不改变现有行为，重构底层存储，实现混合检索

- [ ] 新建 `memory/models.py` 数据模型
- [ ] 新建 `memory/stores/vector_store.py` — ChromaDB 多集合封装，迁移现有 user_preferences 到 memory_preference 集合
- [ ] 新建 `memory/stores/db_store.py` — SQLite 新表创建 + CRUD，保持 user_profiles/reminders 兼容
- [ ] 新建 `memory/retrieval/hybrid_retriever.py` — 混合检索引擎
- [ ] 新建 `memory/retrieval/keywords.py` — 简单中文分词
- [ ] 重构 `memory/manager.py` — 使用新存储和检索器，保持 `get_context`/`update_profile`/`add_reminder` 接口兼容
- [ ] 增加配置项
- [ ] 单元测试：向量存储、关键词搜索、混合检索
- [ ] 数据迁移脚本：现有 ChromaDB 数据迁移到新集合结构

### Phase 2：LLM 自动记忆提取（1-2天）

**目标**：实现对话后自动提取记忆，写入存储

- [ ] 新建 `memory/extraction/prompt.py` — 车机场景提取 Prompt
- [ ] 新建 `memory/extraction/extractor.py` — LLM 提取器
- [ ] 新建对话日志表 `conversation_log` 和记录逻辑
- [ ] 在 FastAPI `/copilotkit` 端点接入后置钩子（方案B）
- [ ] 去重合并逻辑
- [ ] FIFO + importance 遗忘策略
- [ ] 时间衰减逻辑
- [ ] 集成测试：对话后自动提取

### Phase 3：Supervisor Prompt 优化（0.5-1天）

**目标**：按记忆类型结构化注入上下文，优化 Prompt

- [ ] 修改 `SUPERVISOR_PROMPT` 中的记忆上下文区块
- [ ] 修改 `_build_prompt` 使用混合检索结果
- [ ] 更新 `MemoryContext` 格式化方法
- [ ] 手动测试各种对话场景下记忆召回效果
- [ ] 调优权重和阈值

### Phase 4：记忆管理 API 与前端（可选，2-3天）

**目标**：提供记忆管理界面，让用户可以查看/编辑/删除记忆

- [ ] 新增 REST API 端点：
  - `GET /api/memories` — 列出记忆（支持类型过滤）
  - `DELETE /api/memories/{id}` — 删除单条记忆
  - `PUT /api/memories/{id}` — 编辑记忆
  - `POST /api/memories/search` — 手动搜索记忆
  - `POST /api/memories/extract` — 手动触发提取（调试用）
- [ ] 前端 CopilotKit 侧边栏添加"我的记忆"面板
- [ ] 记忆编辑/删除 UI
- [ ] 隐私合规：记忆导出/清除功能

### Phase 5：高级特性（后续迭代）

- [ ] **跨会话记忆总结**：每天/每周自动总结高频出行模式
- [ ] **记忆冲突检测**：当新记忆与旧记忆矛盾时，提示用户确认
- [ ] **多用户识别**：通过语音/座椅识别不同驾驶员，切换记忆库
- [ ] **记忆重要性的主动学习**：基于用户纠正行为调整 importance
- [ ] **Redis 缓存**：高频访问的记忆走 Redis 缓存
- [ ] **记忆分享**：家庭账号间共享常用地址等记忆

---

## 7. 关键技术决策

| 决策点 | 选项 | 选择 | 理由 |
|--------|------|------|------|
| 记忆提取触发方式 | 同步 vs 异步 | **异步（asyncio.create_task）** | 不阻塞对话响应速度 |
| 向量存储 | 单集合 vs 多集合 | **按类型分集合** | 检索时可针对性查类型，避免跨类型噪声 |
| 检索方式 | 纯向量 vs 混合 | **混合检索（向量0.6+关键词0.4）** | 车机场景地名/人名/品牌名精确匹配很重要，参考RAGFlow默认(关键词0.3)适度提升关键词权重 |
| 去重策略 | 不去重 vs 语义去重 | **语义去重(阈值0.9)** | 避免同一信息被反复提取造成冗余 |
| 遗忘策略 | 纯FIFO vs FIFO+importance | **importance加权FIFO** | 重要的长期偏好不应被淘汰 |
| 接入方式 | 改图结构 vs API层钩子 | **API层后置钩子（方案B）** | 侵入性最小，易调试 |
| 提取模型 | 专用小模型 vs 复用对话模型 | **复用对话LLM** | 减少配置，效果已足够 |
| 中文分词 | jieba vs 简单n-gram | **Phase1: 简单n-gram/字符级；Phase2+可引入jieba** | 减少依赖，先跑通再优化 |

---

## 8. 与现有代码的兼容性

### 8.1 保持兼容的接口

以下接口保持不变，不破坏现有功能：

- `memory_manager.get_context(user_id, query)` → 返回 dict（内部重构，兼容现有调用方）
- `memory_manager.update_profile(user_id, updates)` → 保持
- `memory_manager.add_reminder(user_id, content, remind_at)` → 保持
- `memory_manager.checkpointer` → 保持（LangGraph 使用）
- `save_user_preference` 工具 → 保持可用（内部走新存储）
- SQLite `user_profiles` 和 `reminders` 表 → 保持结构不变

### 8.2 数据迁移

Phase 1 启动时需要一次性迁移：

1. **ChromaDB**：现有 `user_preferences` 集合的数据迁移到新 `memory_preference` 集合
   - 添加 `memory_type="preference"`, `importance=0.7`, 时间戳等新字段
   - 原集合保留备份，验证后删除
2. **SQLite**：新建 `memory_entries` 和 `conversation_log` 表
   - 从 `user_profiles` 中把已知偏好写入 `memory_entries`（作为 semantic 类型）
3. 迁移脚本加幂等性检查，重复执行不会重复迁移

---

## 9. 车机场景记忆提取示例

### 示例1：导航场景对话

**对话**：
- 用户："导航回家"
- 助手："好的，已为您规划回家路线，走中环约25分钟。对了，您家小区的停车场入口在张杨路上对吧？"
- 用户："对的，另外记得下次帮我避开外环，上次堵了好久"

**提取结果**：
```json
{
  "memories": [
    {
      "content": "用户家小区停车场入口在张杨路上",
      "memory_type": "semantic",
      "category": "navigation",
      "valid_at": "2026-07-12 14:30:00",
      "invalid_at": "",
      "importance": 0.7
    },
    {
      "content": "用户导航偏好走中环，避开外环",
      "memory_type": "preference",
      "category": "navigation",
      "valid_at": "2026-07-12 14:30:00",
      "invalid_at": "",
      "importance": 0.8
    },
    {
      "content": "用户之前走外环遇到严重拥堵",
      "memory_type": "episodic",
      "category": "navigation",
      "valid_at": "2026-07-05 00:00:00",
      "invalid_at": "2026-10-12 00:00:00",
      "importance": 0.4
    }
  ]
}
```

### 示例2：车辆控制对话

**对话**：
- 用户："有点热，空调开大点"
- 助手："已将空调调到22度、三档风量。"
- 用户："以后默认就24度两档吧，这个温度舒服"

**提取结果**：
```json
{
  "memories": [
    {
      "content": "用户空调温度偏好24度，风量二档",
      "memory_type": "preference",
      "category": "climate",
      "valid_at": "2026-07-12 15:00:00",
      "invalid_at": "",
      "importance": 0.9
    }
  ]
}
```

### 示例3：闲聊中的信息提取

**对话**：
- 用户："周末带儿子去迪士尼玩了，玩得挺开心"
- 助手："听起来很棒！迪士尼周末人不少吧，路上顺利吗？"
- 用户："还行，早上7点出发走沪芦高速，40分钟就到了。我儿子7岁了，特别喜欢海盗船。"

**提取结果**：
```json
{
  "memories": [
    {
      "content": "用户有一个7岁的儿子",
      "memory_type": "semantic",
      "category": "general",
      "valid_at": "2026-07-12 10:00:00",
      "invalid_at": "",
      "importance": 0.7
    },
    {
      "content": "用户2026年7月11日（周六）带儿子去了迪士尼乐园，早上7点出发走沪芦高速约40分钟",
      "memory_type": "episodic",
      "category": "navigation",
      "valid_at": "2026-07-11 07:00:00",
      "invalid_at": "2026-08-12 00:00:00",
      "importance": 0.5
    },
    {
      "content": "用户儿子喜欢迪士尼的海盗船项目",
      "memory_type": "semantic",
      "category": "general",
      "valid_at": "2026-07-12 10:00:00",
      "invalid_at": "",
      "importance": 0.5
    }
  ]
}
```

### 示例4：不提取的情况

**对话**：
- 用户："你好"
- 助手："您好！我是AutoMind，有什么可以帮您？"
→ 不提取（纯问候）

**对话**：
- 用户："打开车窗"
- 助手："好的，已为您打开车窗。"
→ 不提取（纯操作指令，已通过工具执行）

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 提取错误/幻觉记忆 | 召回错误信息影响用户体验 | 1. 低温度 (0.1) 减少创造性；2. 去重机制避免重复；3. 相似度阈值过滤低质量提取；4. Phase 4 提供用户手动删除功能 |
| 记忆提取增加延迟 | 对话响应变慢 | 异步执行（asyncio.create_task），不阻塞主流程；提取在回复发送后进行 |
| 记忆库膨胀 | 向量检索变慢、成本增加 | FIFO 遗忘策略；类型上限；时间衰减降权 |
| 隐私问题 | 存储了用户不希望被记住的信息 | Phase 4 提供记忆查看/删除/全清功能；不提取敏感信息（在 Prompt 中明确禁止）；所有数据本地存储 |
| Prompt 提取不稳定 | 同一对话提取结果不一致 | 低温度；JSON 解析容错；失败静默跳过（不影响主流程）；可配置开关关闭自动提取 |
| 数据迁移风险 | 现有偏好数据丢失 | 迁移前备份；幂等迁移脚本；保留原集合作为回滚 |

---

## 11. 参考资源

### RAGFlow 记忆实现参考（e:/githubcode/ragflow/）

| 文件 | 内容 |
|------|------|
| `api/db/joint_services/memory_message_service.py` | Python 版记忆提取+混合检索核心逻辑 |
| `memory/utils/prompt_util.py` | Prompt 组装器（SYSTEM_BASE_TEMPLATE, TYPE_INSTRUCTIONS） |
| `internal/service/memory_message_service.go` | Go 版记忆保存管线（QueueSaveToMemoryTask） |
| `internal/service/memory.go` | Go 版 MemoryService（CRUD + 搜索） |
| `api/apps/services/memory_api_service.py` | REST API 服务层 |
| `api/apps/restful_apis/memory_api.py` | REST API 路由定义 |

### Vehicle-Agent 现有代码（e:/githubcode/rag_game/vehicle-agent/）

| 文件 | 内容 |
|------|------|
| `backend/app/memory/manager.py` | 现有记忆管理器（重构目标） |
| `backend/app/memory/long_term.py` | 现有长期记忆（ChromaDB + SQLite） |
| `backend/app/memory/short_term.py` | 现有短期记忆（LangGraph checkpointer） |
| `backend/app/graph/supervisor.py` | Supervisor Agent（需要修改 Prompt 和接入钩子） |
| `backend/app/graph/state.py` | LangGraph 状态定义 |
| `backend/app/agents/reminder_agent.py` | 提醒 Agent（含 save_user_preference 工具） |
| `backend/app/config.py` | 配置文件（需要添加记忆配置） |
| `backend/app/models/llm.py` | LLM 工厂 |
| `backend/app/main.py` | FastAPI 入口（需要接入 post_hook） |
