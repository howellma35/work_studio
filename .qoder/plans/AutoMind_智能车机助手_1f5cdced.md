# AutoMind - 智能车机助手平台

> **定位**: 基于 LangGraph 多Agent编排 + MCP协议 + CopilotKit 生成式UI 的车载智能助手，具备记忆、规划、工具调用与全链路可观测能力。

---

## 架构总览

```
用户浏览器 (CopilotKit React UI)
        │  AG-UI Protocol (HTTP/SSE)
        ▼
┌─────────────────────────────────────────────┐
│ FastAPI 服务 (端口 8000)                        │
│  CopilotKit Runtime + LangGraph Agent          │
│                                               │
│  ┌──────────────────────────────────────┐     │
│  │  Supervisor Agent (路由/规划/澄清)      │     │
│  │   ├─ Navigation Agent (导航子Agent)    │     │
│  │   ├─ Media Agent (音乐/多媒体)          │     │
│  │   ├─ Vehicle Agent (车窗/空调/门锁)     │     │
│  │   ├─ Weather Agent (天气查询)           │     │
│  │   └─ Reminder Agent (日程/提醒)         │     │
│  └──────────────────────────────────────┘     │
│  ┌──────────────┐   ┌──────────────────┐      │
│  │ Memory Module │   │ MCP Client       │      │
│  │ (短期+长期)    │   │ (langchain-mcp)  │      │
│  └──────────────┘   └────────┬─────────┘      │
│                              │ stdio/SSE        │
└──────────────────────────────┼──────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ MCP Server (FastMCP) │
                    │ 车辆工具集           │
                    └─────────────────────┘
         │                              │
   ┌─────▼─────┐               ┌───────▼────────┐
   │ ChromaDB  │               │ LangFuse       │
   │ (向量记忆) │               │ (可观测平台)    │
   └───────────┘               └────────────────┘
```

---

## Task 1: 项目脚手架与配置文件

**创建目录结构** `vehicle-agent/`:

```
vehicle-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口 + CopilotKit Runtime
│   │   ├── config.py               # Settings 配置
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── state.py            # AgentState 定义 (继承 CopilotKitState)
│   │   │   ├── supervisor.py       # 主编排 Agent 构建
│   │   │   └── routing.py          # 意图路由逻辑
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── navigation_agent.py
│   │   │   ├── media_agent.py
│   │   │   ├── vehicle_agent.py
│   │   │   ├── weather_agent.py
│   │   │   └── reminder_agent.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py         # 统一记忆管理器
│   │   │   ├── short_term.py      # 短期对话记忆 (LangGraph checkpoint)
│   │   │   └── long_term.py       # 长期偏好记忆 (ChromaDB + SQLite)
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   ├── server.py           # FastMCP 车辆工具服务器
│   │   │   ├── client.py          # MCP Client 集成
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── navigation_tools.py
│   │   │       ├── media_tools.py
│   │   │       ├── vehicle_tools.py
│   │   │       └── weather_tools.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── llm.py             # LLM 工厂 (百炼平台 OpenAI兼容)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── observability.py   # LangFuse 追踪集成
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── langgraph.json             # LangGraph Studio 配置
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── lib/
│   │   │   └── copilotkit.ts      # CopilotKit Provider 配置
│   │   ├── components/
│   │   │   ├── VehicleDashboard.tsx   # 车机仪表盘主页
│   │   │   ├── ChatPanel.tsx          # 对话面板
│   │   │   ├── NavigationCard.tsx     # 导航生成式UI卡片
│   │   │   ├── MediaCard.tsx          # 音乐播放器卡片
│   │   │   ├── VehicleControlCard.tsx # 车辆控制卡片
│   │   │   └── WeatherCard.tsx        # 天气展示卡片
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── deploy/
│   ├── docker-compose.yml         # 全栈编排 (含 LangFuse + ChromaDB)
│   └── nginx.conf                 # 车机助手路由
└── docs/
    ├── README.md
    ├── local-dev.md               # 本地开发与调试指南
    └── architecture.md           # 架构设计文档
```

**关键配置文件**:
- `backend/requirements.txt`: langgraph, langchain-openai, copilotkit, langchain-mcp-adapters, mcp, chromadb, langfuse, fastapi, uvicorn, python-dotenv
- `backend/.env.example`: 所有 `${variable_name}` 可配置项
- `frontend/package.json`: @copilotkit/react-core, @copilotkit/react-ui, @copilotkit/runtime

---

## Task 2: 后端核心 - FastAPI + CopilotKit Runtime

**文件**: `backend/app/main.py`

核心逻辑:
- 创建 FastAPI 应用
- 集成 LangFuse 可观测性 (OTEL)
- 注册 CopilotKit `CopilotKitRemoteEndpoint`，暴露 `/copilotkit` 端点
- 暴露 `/api/vehicle/health` 健康检查
- CORS 配置

关键代码模式:
```python
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent

sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="automind",
            description="智能车机助手",
            graph=build_supervisor_graph(),
        )
    ],
)
add_fastapi_endpoint(app, sdk, "/copilotkit")
```

**文件**: `backend/app/config.py`
- Settings 类，所有配置从环境变量读取
- 可配置变量: `${LLM_API_KEY}`, `${LLM_API_BASE}`, `${LLM_MODEL}`, `${MCP_SERVER_URL}`, `${CHROMA_PERSIST_DIR}`, `${LANGFUSE_HOST}`, `${LANGFUSE_PUBLIC_KEY}`, `${LANGFUSE_SECRET_KEY}`

---

## Task 3: 记忆模块 (Memory Module)

### 3.1 短期对话记忆 - `backend/app/memory/short_term.py`
- 基于 LangGraph `MemorySaver` (开发) / `PostgresSaver` (生产)
- Thread 级别状态隔离，通过 `thread_id` 区分会话
- 维护最近 N 轮对话上下文，自动滑窗

### 3.2 长期用户偏好记忆 - `backend/app/memory/long_term.py`
- **向量记忆**: ChromaDB 存储用户偏好 (常用目的地、空调温度习惯、音乐偏好)
  - 用户每次交互后，提取偏好信息 → embed → 存入 ChromaDB
  - 查询时通过语义相似度召回相关偏好
- **结构化记忆**: SQLite 存储确定性的用户档案
  - 表结构: `user_profiles` (user_id, preferred_temp, home_address, work_address, favorite_music_genre...)
- 提供统一的 `recall_preferences(query)` 和 `save_preference(content)` 接口

### 3.3 统一记忆管理器 - `backend/app/memory/manager.py`
- 对外暴露 `MemoryManager` 类
- `get_context(user_id, query)`: 合并短期+长期记忆，注入 Agent state
- `update(user_id, key, value)`: 更新偏好

---

## Task 4: MCP 模块 (Model Context Protocol)

### 4.1 MCP 工具服务器 - `backend/app/mcp/server.py`
使用 **FastMCP** 构建车辆工具 MCP Server，暴露以下工具:

**导航工具** (`mcp/tools/navigation_tools.py`):
- `plan_route(origin, destination)`: 路径规划 (模拟高德API `${MAP_SERVICE_PROVIDER}`)
- `search_poi(keyword, location)`: POI 搜索
- `get_traffic_info(route_id)`: 实时路况

**多媒体工具** (`mcp/tools/media_tools.py`):
- `play_music(song_name, artist)`: 播放音乐
- `pause_music()`, `next_song()`, `set_volume(level)`: 播放控制
- `get_playlist()`: 当前播放列表

**车辆控制工具** (`mcp/tools/vehicle_tools.py`):
- `control_window(position, action)`: 车窗控制
- `set_climate(temperature, mode)`: 空调控制
- `lock_doors(action)`, `get_vehicle_status()`: 门锁与状态

**天气工具** (`mcp/tools/weather_tools.py`):
- `get_weather(city)`, `get_forecast(city, days)`: 天气查询

### 4.2 MCP Client 集成 - `backend/app/mcp/client.py`
- 使用 `langchain-mcp-adapters` 的 `MultiServerMCPClient`
- stdio 传输方式连接本地 MCP Server
- 动态加载工具，转为 LangChain `BaseTool` 格式

关键模式:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "vehicle": {
        "command": "python",
        "args": ["-m", "app.mcp.server"],
        "transport": "stdio",
    }
})
tools = await client.get_tools()
```

---

## Task 5: 子Agent模块 (Sub-Agent Module)

每个子Agent用 `create_react_agent` 构建，绑定特定工具集和系统提示:

### 5.1 导航Agent - `agents/navigation_agent.py`
- 工具: navigation_tools + MCP 导航工具
- 能力: 路径规划、POI搜索、ETA预估、避开拥堵

### 5.2 多媒体Agent - `agents/media_agent.py`
- 工具: media_tools
- 能力: 音乐播放控制、歌单管理、音量调节

### 5.3 车辆控制Agent - `agents/vehicle_agent.py`
- 工具: vehicle_tools
- 能力: 车窗/空调/门锁/座椅控制、状态查询

### 5.4 天气Agent - `agents/weather_agent.py`
- 工具: weather_tools
- 能力: 实时天气、未来预报、出行建议

### 5.5 提醒Agent - `agents/reminder_agent.py`
- 工具: 记忆模块 + 日程管理
- 能力: 上下文感知提醒 (如"明天有会议建议提前出发")

---

## Task 6: LangGraph 编排 (Supervisor 模式)

**文件**: `backend/app/graph/supervisor.py`

使用 **langgraph-supervisor** 库构建多Agent编排:

```python
from langgraph_supervisor import create_supervisor

graph = create_supervisor(
    agents=[navigation_agent, media_agent, vehicle_agent, weather_agent, reminder_agent],
    model=llm,
    prompt=SUPERVISOR_PROMPT,
)
```

**状态定义** - `backend/app/graph/state.py`:
```python
from copilotkit import CopilotKitState

class AutoMindState(CopilotKitState):
    user_id: str
    user_preferences: dict
    current_vehicle_status: dict
    active_tasks: list
```

**路由逻辑** - `backend/app/graph/routing.py`:
- 意图识别: LLM 分类用户意图
- 动态路由到对应子Agent
- 模糊意图澄清: 当置信度低时，反问用户
- 失败重试: 工具调用失败后最多重试 2 次

**Supervisor 系统提示** 包含:
- 角色定义 (车载智能助手)
- 用户偏好注入 (从记忆模块加载)
- 路由规则
- 错误恢复策略

---

## Task 7: LLM 模型工厂与可观测性

**文件**: `backend/app/models/llm.py`
- 使用百炼平台 OpenAI 兼容接口
- `create_llm()` 工厂方法，支持模型切换 `${LLM_MODEL}`
- 默认 DeepSeek-V4 / Qwen

**文件**: `backend/app/utils/observability.py`
- LangFuse 集成 (通过 OTEL 自动埋点)
- 每次调用自动记录: 输入、输出、token、延迟、工具调用链
- 环境变量配置 LangFuse endpoint

---

## Task 8: CopilotKit 前端 - 车机仪表盘UI

**文件**: `frontend/src/lib/copilotkit.ts`
- 配置 CopilotKit Provider，连接 `/copilotkit` 端点

**核心组件**:
- `VehicleDashboard.tsx`: 主布局，左侧仪表盘 + 右侧聊天面板
- `ChatPanel.tsx`: CopilotKit `<CopilotChat>` 封装，支持流式响应
- **生成式UI卡片**: Agent 通过 `render` 指令动态渲染:
  - `NavigationCard.tsx`: 导航路线展示 (地图模拟 + 路线信息)
  - `MediaCard.tsx`: 音乐播放器 (歌曲信息 + 控制按钮)
  - `VehicleControlCard.tsx`: 车辆状态面板 (车窗/空调/门锁状态可视化)
  - `WeatherCard.tsx`: 天气信息卡片

**设计风格**: 暗色玻璃拟态 (Glassmorphism)，符合现有项目设计规范

**Vite 配置**: 代理 `/copilotkit` 到后端 8000 端口

---

## Task 9: LangFuse 可观测平台

**文件**: `deploy/docker-compose.yml` 新增 LangFuse 服务:
- langfuse-server (Web UI + API)
- postgres (LangFuse 数据库)

用户可访问 `http://server:3000` 查看:
- 每次 Agent 调用的完整 trace
- 每个节点的输入/输出
- Token 消耗与延迟
- 工具调用链路图
- 多轮对话回放

---

## Task 10: Docker 全栈部署

**文件**: `deploy/docker-compose.yml`
新增 vehicle-agent 相关服务:
- `vehicle-backend`: FastAPI + LangGraph + CopilotKit Runtime (端口 8001)
- `vehicle-frontend`: Vite 构建的静态前端 (通过 nginx)
- `langfuse`: 可观测平台 (端口 3000)
- `chromadb`: 向量数据库 (端口 8002)
- `langfuse-db`: PostgreSQL

**文件**: `deploy/nginx.conf` 新增路由:
- `location /vehicle/` → vehicle-frontend
- `location /copilotkit` → vehicle-backend
- `location /vehicle/api/` → vehicle-backend

---

## Task 11: 文档 - 本地开发与调试指南

**文件**: `docs/local-dev.md`

内容包括:
1. **环境准备**: Python venv, Node.js, 依赖安装
2. **配置说明**: `.env` 所有 `${variable_name}` 项
3. **本地启动**: 后端 uvicorn + 前端 vite dev
4. **LangGraph Studio 调试**: `langgraph dev` 可视化单步调试
5. **LangFuse 观测**: 如何查看每步输入输出、token、延迟
6. **新增功能指南**: 如何添加新的子Agent、新的MCP工具
7. **MCP Server 开发**: FastMCP 工具定义方法
8. **生成式UI开发**: 如何新增前端卡片组件

**文件**: `docs/architecture.md`
- 完整架构图 (Mermaid)
- 各模块职责说明
- 技术选型理由 (为何 LangGraph、为何 MCP、为何 CopilotKit)
- 数据流说明

---

## 技术选型理由

| 选型 | 理由 |
|------|------|
| **LangGraph** | 状态机编排，支持循环/分支/人在回路，工业级 Agent 框架首选 |
| **MCP (Model Context Protocol)** | Anthropic 主导的标准协议，2025 Agent 领域最前沿，工具层解耦 |
| **CopilotKit** | 原生 Generative UI + AG-UI 协议，3万+星，Google/LangChain 官方合作 |
| **ChromaDB** | MIT 协议，轻量向量库，商业友好 |
| **LangFuse** | MIT 协议，开源可自托管，全链路追踪 |
| **FastMCP** | MCP Python SDK，装饰器风格开发工具服务器 |
| **百炼平台** | 商业合规，OpenAI 兼容，支持 DeepSeek/Qwen 等多模型 |

---

## 实施顺序

1. Task 1 (脚手架) → 2. Task 3 (记忆模块) → 3. Task 4 (MCP模块) → 4. Task 5 (子Agent) → 5. Task 6 (编排) → 6. Task 2 (FastAPI入口) → 7. Task 8 (前端) → 8. Task 9 (LangFuse) → 9. Task 10 (Docker) → 10. Task 11 (文档)

每个 Task 完成后验证可运行，再进入下一步。
