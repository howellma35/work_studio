# AutoMind - 智能车机助手平台

> 基于 **LangGraph 多Agent编排 + MCP协议 + CopilotKit 生成式UI** 的工业级车载智能助手，具备记忆、规划、工具调用与全链路可观测能力。

## 核心特性

- **多Agent编排**: Supervisor 模式调度 5 个专业子Agent（导航/媒体/车辆控制/天气/提醒）
- **MCP 协议**: 基于 Anthropic Model Context Protocol 标准化工具层
- **双层记忆**: 短期对话记忆 (LangGraph Checkpoint) + 长期偏好记忆 (ChromaDB 向量 + SQLite 结构化)
- **生成式 UI**: CopilotKit 实现自然语言驱动的动态界面渲染
- **全链路可观测**: LangFuse 平台追踪每步输入输出、Token 消耗、调用链路
- **可视化调试**: LangGraph Studio 支持单步执行、状态时间旅行

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + Vite 6 + TailwindCSS 4 + CopilotKit |
| 后端 | Python 3.11 + FastAPI + LangGraph |
| MCP | FastMCP + langchain-mcp-adapters |
| 记忆 | ChromaDB (向量) + SQLite (结构化) |
| 可观测 | LangFuse (自托管) |
| LLM | 百炼平台 OpenAI 兼容接口 (DeepSeek/Qwen) |

## 快速开始

```bash
# 1. 后端
cd backend
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 API Key
python -m uvicorn app.main:app --port 8001 --reload

# 2. 前端
cd frontend
npm install
npm run dev  # http://localhost:5174

# 3. (可选) LangFuse 可观测平台
cd deploy && docker compose up -d langfuse langfuse-db  # http://localhost:3000
```

详见 [本地开发与调试指南](docs/local-dev.md) 和 [架构设计文档](docs/architecture.md)。

## 项目结构

```
vehicle-agent/
├── backend/          # FastAPI + LangGraph + MCP 后端
├── frontend/         # CopilotKit React 前端
├── deploy/           # Docker Compose 全栈部署
└── docs/             # 开发文档与架构说明
```

## License

MIT
