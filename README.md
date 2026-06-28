# Mahongwei Studio

全栈 Web 应用平台，集技术博客、AI 智能对话和 RAG 知识库于一体。

## 功能特性

- **技术博客** — Markdown 文章发布与阅读
- **AI 对话** — 多模型智能对话（DeepSeek、通义千问等 OpenAI 兼容接口）
- **RAG 知识库** — 上传文档（PDF/DOCX/TXT/MD/CSV/HTML）构建知识库，AI 自动检索相关内容进行问答
- **Langfuse 可观测性** — LLM 调用追踪与分析

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite 6 + TypeScript + Tailwind CSS 4 |
| 后端 | Python FastAPI + OpenAI SDK |
| 向量数据库 | Qdrant |
| 文本嵌入 | SiliconFlow API (BAAI/bge-m3) |
| 部署 | Docker Compose + Nginx + Let's Encrypt |

## 项目结构

```
├── web/            # React 前端
├── ai-server/      # Python AI 后端（FastAPI + RAG）
├── vehicle-agent/  # 独立副项目：车载智能助手
├── deploy/         # Docker 部署配置
└── docs/           # 项目文档
```

## 快速开始

### Docker 部署

```bash
cd deploy
cp .env.example .env
# 编辑 .env 填入 API Key
docker compose up -d --build
```

### 本地开发

```bash
# 1. 启动 Qdrant
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# 2. 启动 AI 后端
cd ai-server
python -m venv .venv && .venv/Scripts/Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 API Key
uvicorn app.main:app --reload

# 3. 启动前端
cd web
npm install
npm run dev
```

访问 http://localhost:5173

## 文档

- [使用说明](docs/usage.md)
- [本地开发指南](docs/local-dev.md)
- [Docker 部署](docs/deployment.md)
- [故障排除](docs/troubleshooting.md)

## 许可证

[Apache-2.0](LICENSE)
