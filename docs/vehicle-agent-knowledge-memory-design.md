# AutoMind 知识库与跨会话记忆功能设计文档

> 版本: v1.0 | 日期: 2026-07-15 | 状态: 已实现

## 1. 功能概述

为 AutoMind 车机智能助手新增以下核心能力：

1. **知识库检索** — 通过 RAGFlow 实现知识性内容的混合检索（关键词+向量语义），结果附带来源标注
2. **跨会话记忆** — 使用 RAGFlow Memory API 实现多会话间共享记忆
3. **自动KB决策** — Supervisor 基于关键词启发式自动判断是否检索知识库
4. **多会话管理** — 创建/切换/删除会话，会话间记忆共享
5. **知识库导入** — 支持内联文本导入和文件上传
6. **来源标注渲染** — 前端解析 `[来源: xxx]` 格式，渲染为可点击 CitationBadge

## 2. 架构设计

### 2.1 新增子Agent架构

```
┌────────────────────────────────────┐
│  Supervisor (create_agent)          │
│  middleware=[_build_prompt,         │
│    CopilotKitMiddleware]            │
│                                    │
│  _build_prompt:                    │
│    1. memory_manager.get_context() │ ← 本地记忆（档案/偏好/提醒）
│    2. knowledge_service.search()   │ ← 知识库检索（自动判断）
│    3. memory_service.recall()       │ ← RAGFlow 跨会话记忆
│                                    │
│  tools=[                           │
│    navigation_agent,                │
│    media_agent,                     │
│    vehicle_agent,                   │
│    weather_agent,                   │
│    reminder_agent,                  │
│    knowledge_agent,   ← 新增       │
│  ]                                  │
└────────────────────────────────────┘
```

### 2.2 RAGFlow 集成层

```
┌─────────────────────────────────────────────────┐
│  RAGFlow Service Layer                           │
│  ┌──────────────┐ ┌──────────────┐              │
│  │ ragflow_      │ │ knowledge_   │              │
│  │ client.py     │ │ service.py   │              │
│  │ (SDK封装)     │ │ (检索+导入) │              │
│  └──────────────┘ └──────────────┘              │
│  ┌──────────────┐ ┌──────────────┐              │
│  │ memory_      │ │ init_        │              │
│  │ service.py   │ │ datasets.py  │              │
│  │ (跨会话记忆) │ │ (模拟数据)   │              │
│  └──────────────┘ └──────────────┘              │
│                                                  │
│  ─────→ RAGFlow v0.26.3 (localhost:9380) ─────→ │
│    retrieve() / create_dataset() / add_message() │
│    search_message() / create_memory()             │
└─────────────────────────────────────────────────┘
```

### 2.3 数据流

**知识库检索流程**：
```
用户问"胎压多少算正常"
→ supervisor _build_prompt: should_search_kb() → True (关键词匹配"胎压")
→ knowledge_service.search("胎压多少算正常")
→ ragflow_client.retrieve(dataset_ids, question)
→ RAGFlow 混合检索 → 返回 Chunks (含 document_name + similarity)
→ 格式化为 [来源: vehicle_manual_excerpts.md | 相关度: 0.85] 胎压标准...
→ 注入 supervisor 系统提示词
→ supervisor 回复: "标准胎压是前轮2.9bar、后轮3.0bar（来源：车辆手册摘录）"
→ 前端 CitationBadge 渲染来源标注
```

**跨会话记忆流程**：
```
会话1: 用户说"我喜欢听周杰伦"
→ 后端 add_message() → RAGFlow Memory 保存对话
→ RAGFlow 自动提取语义记忆

会话2: 用户问"我喜欢什么音乐"
→ memory_service.recall("我喜欢什么音乐")
→ RAGFlow search_message() 跨会话搜索
→ 返回: "用户喜欢听周杰伦的音乐"
→ 注入 supervisor 系统提示词
→ supervisor 回复: "你喜欢周杰伦的歌！要播放吗？"
```

## 3. 模拟知识数据

系统首次启动时自动创建 6 个 RAGFlow Dataset 并导入模拟数据：

| Dataset | 名称 | 内容 |
|---------|------|------|
| automind_personal_profile | 个人档案 | 车主李明，35岁，地址，家庭，通勤 |
| automind_vehicle_info | 车辆状况 | 特斯拉Model Y，里程28500km，电池68% |
| automind_maintenance | 保养记录 | 5条保养维修记录 + 下次保养计划 |
| automind_driving_habits | 驾驶习惯 | 通勤路线，周末出行，能耗，车内设置 |
| automind_vehicle_manual | 车辆手册摘录 | 胎压标准，充电模式，紧急开门，故障处理 |
| automind_preferences | 用户偏好 | 空调24度，周杰伦，导航避堵，晨间模式 |

## 4. API 端点

### 知识库管理 (`/api/vehicle/knowledge/`)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/datasets` | 创建知识库 |
| GET | `/datasets` | 列出知识库 |
| POST | `/datasets/{id}/files` | 上传文件 |
| POST | `/datasets/{id}/content` | 内联文本导入 |
| POST | `/search` | 搜索知识库（测试） |
| GET | `/status` | 知识库服务状态 |

### 会话管理 (`/api/vehicle/sessions`)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/` | 创建新会话 |
| GET | `/` | 列出会话 |
| DELETE | `/{id}` | 删除会话 |

## 5. 前置条件

在使用完整功能前需要：

1. 在 RAGFlow Web UI (localhost:9380) 注册账号并创建 API Key
2. 在 RAGFlow System Model Settings 中配置 LLM 和 Embedding 模型
3. 将 `RAGFLOW_API_KEY`、`RAGFLOW_LLM_ID`、`RAGFLOW_EMBD_ID` 填入 `deploy/.env`

**无 RAGFlow Key 时**：系统自动降级为本地模式，knowledge_agent 的搜索返回空结果，跨会话记忆使用本地 ChromaDB。

## 6. 文件清单

### 新增文件 (16)
- `backend/app/ragflow/__init__.py`
- `backend/app/ragflow/client.py` — RAGFlow SDK 封装
- `backend/app/ragflow/knowledge_service.py` — 知识库服务
- `backend/app/ragflow/memory_service.py` — 跨会话记忆服务
- `backend/app/ragflow/init_datasets.py` — 模拟数据初始化
- `backend/app/ragflow/mock_data/*.md` — 6个模拟知识文件
- `backend/app/agents/knowledge_agent.py` — 知识库子Agent
- `backend/app/routers/session.py` — 会话管理路由
- `backend/app/routers/knowledge.py` — 知识库管理路由
- `frontend/src/components/CitationBadge.tsx` — 来源标注徽章
- `frontend/src/components/SessionPanel.tsx` — 会话列表组件
- `frontend/src/components/KnowledgeImport.tsx` — 知识库导入面板

### 修改文件 (12)
- `backend/app/config.py` — 新增 RAGFlow 配置
- `backend/requirements.txt` — 新增 ragflow-sdk
- `backend/app/main.py` — 注册路由 + 初始化 RAGFlow
- `backend/app/graph/state.py` — 新增字段
- `backend/app/graph/supervisor.py` — 新增 knowledge_agent + 知识上下文
- `backend/app/graph/routing.py` — 新增第6条路由
- `backend/app/graph/subagent_tools.py` — 新增 knowledge_agent @tool
- `backend/app/memory/manager.py` — 整合 RAGFlow 记忆
- `frontend/src/App.tsx` — 会话 + 来源标注 + 知识库导入
- `deploy/.env` — 新增 RAGFlow 环境变量
- `deploy/.env.example` — 同步
- `deploy/nginx/nginx.conf` — 新增超时+大小配置
