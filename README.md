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

### Docker 部署（生产环境）

```bash
cd deploy
cp .env.example .env
nano .env  # 填入所有 API Key 和密码
docker compose up -d --build
```

访问 https://mahongwei.com.cn

### 本地开发

```bash
# 1. 启动 Qdrant（向量数据库）
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# 2. 启动 AI 后端
cd ai-server
python -m venv .venv && .venv/Scripts/Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 API Key
uvicorn app.main:app --reload --port 8000

# 3. 启动前端
cd web
npm install
npm run dev
```

访问 http://localhost:5173

---

## Docker 运维命令速查

> 以下命令均在 `deploy/` 目录下执行

### 构建 & 启动

```bash
# 构建并启动全部服务
docker compose up -d --build

# 只重新构建某个服务（改了代码后用）
docker compose up -d --build web              # 主站前端
docker compose up -d --build ai-server        # AI 后端
docker compose up -d --build vehicle-backend  # 车载助手后端
docker compose up -d --build vehicle-frontend # 车载助手前端
docker compose up -d --build vehicle-runtime  # CopilotKit Runtime
docker compose up -d --build nginx            # Nginx 反向代理

# 强制重新构建（忽略缓存，依赖变更后用）
docker compose build --no-cache web
docker compose up -d web
```

### 重启（不重新构建，只重启容器）

```bash
# 重启某个服务
docker compose restart web
docker compose restart ai-server
docker compose restart vehicle-backend
docker compose restart vehicle-frontend
docker compose restart vehicle-runtime
docker compose restart nginx

# 重启全部服务
docker compose restart
```

### 停止

```bash
# 停止全部服务（不删除数据）
docker compose down

# 停止全部 + 删除数据卷（慎用，会清空知识库数据）
docker compose down -v
```

### 查看日志

```bash
# 查看所有服务日志（实时）
docker compose logs -f

# 查看单个服务日志
docker compose logs -f web
docker compose logs -f ai-server
docker compose logs -f vehicle-backend
docker compose logs -f nginx

# 查看最近 100 行日志
docker compose logs --tail 100 ai-server
```

### 调试

```bash
# 查看所有容器状态
docker compose ps

# 进入容器内部
docker compose exec ai-server bash
docker compose exec vehicle-backend bash
docker compose exec nginx sh

# 启动 Langfuse 可观测性（可选，需 4GB+ 内存）
docker compose --profile langfuse up -d --build
```

---

## 文档

- [使用说明](docs/usage.md)
- [本地开发指南](docs/local-dev.md)
- [Docker 部署（含内网穿透）](docs/deployment.md)
- [故障排除](docs/troubleshooting.md)

## 许可证

[Apache-2.0](LICENSE)
