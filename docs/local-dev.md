# 2026-06-16 本地开发指南

## 前置要求

| 工具 | 最低版本 | 用途 |
|------|---------|------|
| Node.js | 20+ | 前端构建工具链（Vite、TypeScript） |
| Python | 3.11+ | AI 后端 |
| pip | 最新版 | Python 包管理器 |

---

## 项目目录结构总览

```
rag_game/
├── web/                     # ── 前端 ── React + Vite + TypeScript + TailwindCSS v4
│   ├── src/
│   │   ├── components/      #    通用可复用组件
│   │   ├── config/
│   │   │   └── site.ts          #  站点全局配置（标题、组织名、模型列表等）
│   │   ├── data/
│   │   │   └── blogs.json       #  博客文章数据
│   │   ├── hooks/               #  自定义 React Hooks
│   │   ├── layouts/
│   │   │   └── Layout.tsx       #  全局布局（Header + 内容区 + Footer）
│   │   ├── pages/
│   │   │   ├── HomePage.tsx     #  首页（板块入口卡片）
│   │   │   ├── ai/
│   │   │   │   └── AIChat.tsx       #  AI 对话页面
│   │   │   ├── blog/
│   │   │   │   ├── BlogList.tsx     #  博客文章列表
│   │   │   │   └── BlogPost.tsx     #  博客文章详情
│   │   │   └── legal/
│   │   │       ├── OpenSource.tsx   #  开源声明
│   │   │       ├── Privacy.tsx      #  隐私政策
│   │   │       └── Terms.tsx        #  服务条款
│   │   ├── App.tsx              #  React Router 路由配置
│   │   ├── index.css            #  全局样式
│   │   └── main.tsx             #  React 入口
│   ├── vite.config.ts           #  Vite 配置（Tailwind 插件 + API 代理规则）
│   ├── package.json             #  npm 依赖和脚本
│   └── tsconfig.json            #  TypeScript 编译配置
│
├── ai-server/               # ── AI 后端 ── Python FastAPI（对话 + RAG 知识库）
│   ├── app/
│   │   ├── config.py            #  环境变量读取
│   │   ├── main.py              #  应用入口
│   │   ├── routers/             #  API 路由
│   │   ├── services/            #  业务服务
│   │   └── models/              #  数据模型
│   ├── .env.example             #  环境变量模板
│   ├── requirements.txt         #  Python 依赖清单
│   └── Dockerfile               #  Docker 镜像构建文件
│
├── vehicle-agent/           # ── 独立副项目 ── 车载智能助手
│
├── deploy/                  # ── 部署配置 ──
│   ├── docker-compose.yml       #  Docker Compose 多服务编排
│   ├── .env.example             #  统一环境变量模板
│   └── nginx/
│       └── nginx.conf           #  Nginx 反向代理配置
│
├── docs/                    # ── 项目文档 ──
│   ├── usage.md                 #  功能使用说明
│   ├── local-dev.md             #  本地开发指南（本文件）
│   ├── deployment.md            #  Docker 部署方案
│   └── troubleshooting.md       #  调试技巧与问题排查
│
├── .gitignore
└── LICENSE
```

---

## 一、前端（web/）

### 1. 安装依赖

```bash
cd web
npm install
```

### 2. 环境变量（可选）

如需自定义站点信息，在 `web/` 目录下创建 `.env.local`：

```env
VITE_SITE_TITLE=我的平台
VITE_ORG_NAME=我的组织
VITE_ICP_NUMBER=京ICP备XXXXXXXX号
VITE_CONTACT_EMAIL=me@example.com
```

> 不创建也完全可以，会使用 `web/src/config/site.ts` 中的默认值。

### 3. 启动开发服务器

```bash
cd web
npm run dev
```

前端运行在 **http://localhost:5173**。

### 4. Vite 代理规则

`web/vite.config.ts` 已配置以下代理，开发模式下 API 请求自动转发到后端：

| 前端请求路径 | 代理目标 | 说明 |
|-------------|---------|------|
| `/api/ai/*` | `http://localhost:8000` | AI 聊天接口 |
| `/api/knowledge/*` | `http://localhost:8000` | 知识库管理接口 |

### 5. 构建生产版本

```bash
cd web
npm run build
```

构建产物输出到 `web/dist/` 目录。

---

## 二、AI 后端（ai-server/）

> 负责 AI 对话 + RAG 知识库，运行在 **http://localhost:8000**。

### 1. 创建 Python 虚拟环境

```bash
cd ai-server

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（每次打开新终端都需要执行）
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 从模板复制一份配置文件
copy .env.example .env      # Windows
cp .env.example .env        # Linux/Mac
```

编辑 `ai-server/.env`：

```env
# LLM API 配置（OpenAI 兼容接口）
LLM_API_KEY=sk-your-api-key-here
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_DEFAULT_MODEL=deepseek-v4-flash

# Embedding 配置（SiliconFlow）
EMBEDDING_API_KEY=your_siliconflow_key_here
EMBEDDING_API_URL=https://api.siliconflow.cn/v1/embeddings
EMBEDDING_MODEL=BAAI/bge-m3

# Qdrant 向量数据库（本地开发用 localhost）
QDRANT_HOST=localhost
QDRANT_PORT=6333

# 服务配置
AI_PORT=8000
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

**支持的 LLM 提供商：**

| 提供商 | `LLM_API_BASE` 值 |
|--------|-------------------|
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 月之暗面 | `https://api.moonshot.cn/v1` |
| 其他 | 任何 OpenAI 兼容 API 地址 |

### 4. 启动 Qdrant（本地开发）

```bash
# 使用 Docker 启动 Qdrant
docker run -d -p 6333:6333 -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant
```

### 5. 启动 AI 后端

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后访问 **http://localhost:8000/docs** 可查看 Swagger API 文档。

### API 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/ai/models` | 获取可用模型列表 |
| POST | `/api/ai/chat` | AI 对话（支持 RAG 知识库检索） |
| POST | `/api/knowledge/` | 创建知识库 |
| GET | `/api/knowledge/` | 列出所有知识库 |
| GET | `/api/knowledge/{kb_id}` | 获取知识库详情 |
| DELETE | `/api/knowledge/{kb_id}` | 删除知识库 |
| POST | `/api/knowledge/{kb_id}/files` | 上传文件到知识库 |
| DELETE | `/api/knowledge/{kb_id}/files/{file_id}` | 删除知识库中的文件 |

---

## 三、完整启动流程

同时打开 **2 个终端**，按顺序启动：

### 终端 1 — AI 后端

```bash
cd ai-server
.venv\Scripts\Activate.ps1        # 激活虚拟环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 终端 2 — 前端

```bash
cd web
npm run dev
```

全部启动后访问 **http://localhost:5173** 即可使用完整功能。

---

## 端口一览

| 服务 | 端口 | 技术栈 |
|------|------|--------|
| 前端（Vite dev） | 5173 | React 18 + Vite 6 + TypeScript |
| AI 后端 | 8000 | Python FastAPI + Qdrant |
| Qdrant | 6333 | 向量数据库 |

---

## 技术栈说明

**前端**：React 18 + Vite 6 + TypeScript + TailwindCSS v4（`@tailwindcss/vite` 插件）+ React Router v7

**AI 后端**：FastAPI + openai SDK + qdrant-client + pdfplumber + python-docx + uvicorn
