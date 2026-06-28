# CLAUDE.md — Mahongwei Studio 项目文档

> 本文件是 Claude Code 的项目级上下文文件，随 git 仓库共享，所有协作者的 Claude Code 会话自动加载。

## 项目概述

Mahongwei Studio 是部署在 `mahongwei.com.cn`（阿里云 AlmaLinux）上的全栈 Web 应用，包含三大板块：

1. **技术博客** — 文章发布与阅读
2. **AI 聊天** — 多模型对话（DeepSeek、Qwen 等），支持知识库 RAG 检索增强
3. **RAG 知识库** — 上传文档构建知识库，AI 自动检索相关内容进行问答

另外包含独立副项目 `vehicle-agent/`（车载智能助手，LangGraph/MCP/CopilotKit）。

## 项目结构

```
rag_game/
├── web/               # React 前端 SPA (Vite + React Router + Tailwind CSS)
├── ai-server/         # Python AI 后端 (FastAPI + Qdrant + OpenAI SDK)
├── vehicle-agent/     # 独立副项目：车载智能助手 (LangGraph/MCP/CopilotKit)
├── deploy/            # Docker 部署配置（统一入口）
│   ├── docker-compose.yml    # 多服务编排
│   ├── .env.example          # 统一环境变量模板
│   ├── nginx/nginx.conf      # Nginx 反向代理
│   └── docs/                 # 部署文档
├── docs/              # 用户文档（使用、本地开发、故障排除）
└── CLAUDE.md          # 项目级 Claude Code 上下文
```

## 技术栈

### 前端 (`web/`)
- React 18 + TypeScript + Vite 6
- Tailwind CSS 4 (`@tailwindcss/vite` 插件)
- react-router-dom v7 + lucide-react + react-dropzone
- react-markdown + remark-gfm
- 开发代理: `/api/ai/*` → ai-server, `/api/knowledge/*` → ai-server

### AI 后端 (`ai-server/`)
- Python 3.11 + FastAPI + uvicorn
- LLM: OpenAI SDK（兼容接口，支持百炼/DeepSeek/OpenAI 等）
- 向量数据库: Qdrant (qdrant-client)
- 文本嵌入: SiliconFlow API (BAAI/bge-m3 模型, 1024 维)
- 文件解析: pdfplumber (PDF), python-docx (DOCX), chardet (编码检测), beautifulsoup4 (HTML)
- 文本分块: 自定义递归字符分割（500 字符/块, 50 字符重叠）

### 部署
- Docker Compose + Nginx (alpine) + Let's Encrypt SSL
- Qdrant 向量数据库 (qdrant/qdrant:latest)
- Langfuse V3 可观测性平台

## 关键文件

### 前端入口
- `web/src/main.tsx` — React 挂载入口
- `web/src/App.tsx` — 路由定义
- `web/src/config/site.ts` — 集中配置（模型列表、ICP号、环境变量）
- `web/src/pages/ai/AIChat.tsx` — AI 聊天界面（支持知识库 RAG）
- `web/src/pages/knowledge/KnowledgeList.tsx` — 知识库列表页
- `web/src/pages/knowledge/KnowledgeDetail.tsx` — 知识库详情（文件管理）
- `web/vite.config.ts` — Vite 配置 + 开发代理规则

### AI 后端入口
- `ai-server/app/main.py` — FastAPI 应用入口（Qdrant 初始化、路由注册）
- `ai-server/app/config.py` — 配置（LLM、Embedding、Qdrant、Chunking）
- `ai-server/app/routers/chat.py` — AI 聊天端点（支持 RAG 检索）
- `ai-server/app/routers/knowledge.py` — 知识库 CRUD + 文件上传
- `ai-server/app/services/llm_service.py` — OpenAI 兼容客户端
- `ai-server/app/services/embedding_service.py` — SiliconFlow 向量嵌入
- `ai-server/app/services/chunking_service.py` — 文本分块
- `ai-server/app/services/file_parser_service.py` — 多格式文件解析
- `ai-server/app/services/retrieval_service.py` — Qdrant 存储与检索
- `ai-server/app/models/schemas.py` — Pydantic 数据模型

### 部署
- `deploy/docker-compose.yml` — 服务编排（ai-server, web, nginx, qdrant, langfuse 栈）
- `deploy/.env.example` — 统一环境变量模板
- `deploy/nginx/nginx.conf` — Nginx 反向代理（SSL、路由）

## 服务通信架构

```
                    Nginx (80/443)
                   /      |       \
                  /       |        \
          web(SPA)    ai-server    Qdrant
            (:80)     (:8000)     (:6333)
```

- **REST**: `/api/ai/*` + `/api/knowledge/*` → ai-server
- 前端配置通过 Vite 环境变量 `VITE_AI_SERVER_URL`

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/ai/models` | 获取可用模型列表 |
| POST | `/api/ai/chat` | AI 对话（FormData: message, model, history, kb_id?, knowledge_file?） |
| POST | `/api/knowledge/` | 创建知识库 |
| GET | `/api/knowledge/` | 列出所有知识库 |
| GET | `/api/knowledge/{kb_id}` | 获取知识库详情（含文件列表） |
| DELETE | `/api/knowledge/{kb_id}` | 删除知识库 |
| POST | `/api/knowledge/{kb_id}/files` | 上传文件（解析→分块→嵌入→存储） |
| DELETE | `/api/knowledge/{kb_id}/files/{file_id}` | 删除知识库中的文件 |

## RAG 知识库机制

**文件上传管道**: 文件上传 → 格式检测 → 文本提取 → 分块(500字符) → 嵌入(SiliconFlow BAAI/bge-m3) → 存入 Qdrant

**RAG 检索管道**: 用户消息 → 嵌入 → Qdrant 相似度搜索(top-5) → 注入上下文 → LLM 生成 → 返回

**支持文件格式**: PDF, DOCX, TXT, MD, CSV, HTML

## 编码约定

- 后端用 Python/FastAPI，路由按模块拆分到 `routers/`，服务逻辑放 `services/`
- 前端用 React/Vite/Tailwind，页面组件放 `pages/`，复用逻辑放 `hooks/`
- AI 聊天走 OpenAI SDK 兼容接口（百炼/DeepSeek/OpenAI 均可）
- 环境变量变更需同步 `deploy/.env.example` 和 `ai-server/.env.example`
- 新增服务需更新 `deploy/docker-compose.yml` 和 `deploy/nginx/nginx.conf`
