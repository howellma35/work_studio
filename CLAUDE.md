# CLAUDE.md — Mahongwei Studio 项目文档

> 本文件是 Claude Code 的项目级上下文文件，随 git 仓库共享，所有协作者的 Claude Code 会话自动加载。

## 项目概述

Mahongwei Studio 是部署在 `mahongwei.com.cn`（阿里云 AlmaLinux）上的全栈 Web 应用，包含四大板块：

1. **技术博客** — 文章发布与阅读
2. **AI 聊天** — 多模型对话（DeepSeek、Qwen 等），支持知识库 RAG
3. **实用工具** — PDF 解析等
4. **互动游戏** — 抖音直播猜词互动游戏（核心功能）

另外包含独立副项目 `vehicle-agent/`（车载智能助手，LangGraph/MCP/CopilotKit）。

## 项目结构

```
rag_game/
├── web/               # React 前端 SPA (Vite + React Router + Tailwind CSS)
├── game-server/       # Python 猜词游戏后端 (FastAPI + python-socketio) ← 当前后端
├── ai-server/         # Python AI 聊天+PDF解析后端 (FastAPI + openai SDK)
├── server/            # (已弃用) Node.js/TypeScript 后端 (Express + Socket.IO + Redis)
├── deploy/            # Docker Compose 编排 + Nginx 反向代理配置
├── miniprogram/       # 抖音小程序（观众参与猜词游戏）
├── vehicle-agent/     # 独立副项目：车载智能助手 (LangGraph/MCP/CopilotKit)
├── docs/              # 用户文档（部署、使用、故障排除）
└── 小白操作手册.md     # 面向初学者的部署/直播操作指南
```

**重要**: `server/`（Node.js 后端）已弃用，`game-server/`（Python）是当前后端。修改代码时只关注 `game-server/` 和 `ai-server/`。

## 技术栈

### 前端 (`web/`)
- React 18 + TypeScript + Vite 6
- Tailwind CSS 4 (PostCSS)
- react-router-dom v7 + lucide-react
- socket.io-client 4（WebSocket 实时通信）
- 开发代理: `/api/game/*` → game-server, `/api/ai/*` → ai-server

### 游戏后端 (`game-server/`)
- Python 3.12 + FastAPI + python-socketio + httpx + uvicorn
- 向量嵌入: SiliconFlow API (BAAI/bge-m3 模型)
- 余弦相似度判定猜词，回退到编辑距离

### AI 后端 (`ai-server/`)
- Python 3.11 + FastAPI + openai SDK + pdfplumber
- 大模型: 阿里云百炼平台 (DashScope)，OpenAI 兼容接口

### 部署
- Docker Compose v3.8 + Nginx (alpine) + Let's Encrypt SSL

## 关键文件

### 前端入口
- `web/src/main.tsx` — React 挂载入口
- `web/src/App.tsx` — 路由定义
- `web/src/config/site.ts` — 集中配置（服务器URL、模型列表、ICP号、环境变量）
- `web/src/pages/games/WordGuessGame.tsx` — 猜词游戏主播控制面板
- `web/src/pages/ai/AIChat.tsx` — AI 聊天界面
- `web/src/hooks/useWebSocket.ts` — Socket.IO 客户端逻辑
- `web/vite.config.ts` — Vite 配置 + 开发代理规则

### 游戏后端入口
- `game-server/app/main.py` — FastAPI 应用（REST + Socket.IO ASGI）
- `game-server/app/config.py` — 游戏配置（嵌入端点、相似度阈值、轮次）
- `game-server/app/ws/handler.py` — Socket.IO 事件处理器
- `game-server/app/services/game_service.py` — 核心游戏逻辑
- `game-server/app/services/embedding_service.py` — 向量嵌入+相似度计算
- `game-server/app/services/rank_service.py` — 内存排行榜

### AI 后端入口
- `ai-server/app/main.py` — FastAPI 应用
- `ai-server/app/config.py` — AI 配置（LLM密钥、基础URL、默认模型）
- `ai-server/app/routers/chat.py` — AI 聊天端点
- `ai-server/app/routers/pdf.py` — PDF 解析端点
- `ai-server/app/services/llm_service.py` — OpenAI兼容客户端
- `ai-server/app/services/pdf_service.py` — pdfplumber PDF 提取

### 部署
- `deploy/docker-compose.yml` — 5服务编排 + 3数据卷
- `deploy/nginx.conf` — Nginx（SSL、路由、WebSocket升级）

## 服务通信架构

```
                    Nginx (80/443)
                   /      |       \
                  /       |        \
          web(SPA)  game-server    ai-server
                    (:3001)        (:8000)
```

- **REST**: `/api/game/*` → game-server, `/api/ai/*` + `/api/pdf/*` → ai-server
- **WebSocket**: `/socket.io/` → game-server（猜词游戏实时交互）
- 前端配置通过 Vite 环境变量 `VITE_AI_SERVER_URL` 和 `VITE_SERVER_URL`

## 猜词游戏机制

- 观众猜测文本 → SiliconFlow API (`BAAI/bge-m3`) 嵌入 → 余弦相似度
- **相似度 ≥ 0.75** → 猜对；API 不可用时回退编辑距离
- 每人每轮最多猜 3 次
- 主播通过 WebSocket 控制轮次（开始/结束），倒计时后自动结束
- 排行榜每 3 秒广播一次
- 词库和猜测记录存储在 `game-server/data/` JSON 文件中

## 编码约定

- 后端新增功能用 Python/FastAPI，路由按模块拆分到 `routers/`
- 前端用 React/Vite/Tailwind，页面组件放 `pages/`，复用逻辑放 `hooks/`
- AI 聊天调用走 OpenAI SDK（兼容接口）
- 实时交互用 Socket.IO，REST 用于 CRUD
- 环境变量变更需同步 `.env.example` 和前端 `site.ts`
- 新增服务需更新 `docker-compose.yml` 和 `nginx.conf`
