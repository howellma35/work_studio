# 本地调试指南

## 前置要求

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| Node.js | 20+ | 前端构建工具链 |
| Python | 3.11+ | AI 后端和游戏后端 |
| pip | 最新版 | Python 包管理器 |

> **注意**：本项目后端全部使用 Python，不再需要 Redis 或 Node.js 后端。

---

## 项目目录结构总览

```
rag_game/
├── web/                    # React 前端（Vite + TypeScript + TailwindCSS）
│   ├── src/
│   │   ├── components/     # 通用组件（Header, Footer, CookieBanner, GameStatus）
│   │   ├── config/         # 站点配置（site.ts — 可配置变量集中管理）
│   │   ├── data/           # 静态数据（blogs.json 博客文章数据）
│   │   ├── hooks/          # 自定义 Hook（useWebSocket.ts）
│   │   ├── layouts/        # 布局组件（Layout.tsx — Header+Footer+内容区）
│   │   ├── pages/          # 页面组件
│   │   │   ├── ai/         #   AI 聊天页面（AIChat.tsx）
│   │   │   ├── blog/       #   博客列表和详情（BlogList, BlogPost）
│   │   │   ├── games/      #   游戏列表和猜词游戏（GamesList, WordGuessGame）
│   │   │   ├── legal/      #   法律页面（OpenSource, Privacy, Terms）
│   │   │   ├── tools/      #   工具列表和 PDF 解析（ToolsList, PdfParser）
│   │   │   └── HomePage.tsx #  首页
│   │   ├── App.tsx         # 路由配置入口
│   │   ├── index.css       # 全局样式（TailwindCSS v4 设计系统）
│   │   └── main.tsx        # React 入口
│   ├── vite.config.ts      # Vite 配置（Tailwind 插件 + API 代理）
│   ├── package.json
│   └── tsconfig.json
│
├── ai-server/              # Python AI 后端（FastAPI）
│   ├── app/
│   │   ├── config.py       # 环境变量配置
│   │   ├── main.py         # 入口：CORS、路由注册、日志配置
│   │   ├── routers/
│   │   │   ├── chat.py     # AI 聊天 API（POST /api/ai/chat）
│   │   │   └── pdf.py      # PDF 解析 API（POST /api/pdf/parse）
│   │   └── services/
│   │       ├── llm_service.py  # OpenAI 兼容接口调用
│   │       └── pdf_service.py  # pdfplumber 文本提取
│   ├── .env.example        # 环境变量模板
│   ├── requirements.txt    # Python 依赖
│   └── Dockerfile
│
├── game-server/            # Python 游戏后端（FastAPI + Socket.IO）
│   ├── app/
│   │   ├── config.py       # 环境变量配置
│   │   ├── main.py         # 入口：FastAPI + Socket.IO 组合应用
│   │   ├── services/
│   │   │   ├── game_service.py      # 游戏轮次管理、词库管理
│   │   │   ├── embedding_service.py # Embedding 语义匹配
│   │   │   └── rank_service.py      # 排行榜（内存实现）
│   │   └── ws/
│   │       └── handler.py  # Socket.IO 事件处理器
│   ├── data/
│   │   └── words.json      # 词库数据（词语、提示、分类、难度）
│   ├── .env.example        # 环境变量模板
│   ├── requirements.txt    # Python 依赖
│   └── Dockerfile
│
├── server/                 # [旧] Node.js 后端（已弃用，保留供参考）
├── miniprogram/            # [旧] 抖音小程序（已弃用，保留供参考）
│
├── deploy/                 # Docker 部署配置
│   ├── docker-compose.yml  # 多服务编排
│   └── nginx.conf          # Nginx 反向代理（含 SSL）
│
├── docs/                   # 项目文档
│   ├── usage.md            # 使用说明
│   ├── local-dev.md        # 本地调试指南（本文件）
│   ├── deployment.md       # Docker 部署方案
│   └── troubleshooting.md  # 调试技巧与问题排查
│
├── .gitignore
└── LICENSE                 # Apache-2.0 开源协议
```

---

## 一、前端开发

### 启动

```bash
cd web
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`。

### Vite 代理配置

`web/vite.config.ts` 已配置以下代理，开发模式下自动转发：

| 前端请求路径 | 代理目标 | 说明 |
|-------------|---------|------|
| `/api/ai/*` | `http://localhost:8000` | AI 聊天后端 |
| `/api/pdf/*` | `http://localhost:8000` | PDF 解析后端 |
| `/api/game/*` | `http://localhost:3001` | 游戏 REST API |
| `/socket.io/*` | `http://localhost:3001` | 游戏 WebSocket (Socket.IO) |

### 环境变量（可选）

在 `web/` 目录创建 `.env.local`：

```env
VITE_SITE_TITLE=我的平台
VITE_ORG_NAME=我的组织
VITE_ICP_NUMBER=京ICP备XXXXXXXX号
VITE_CONTACT_EMAIL=me@example.com
```

### 构建

```bash
cd web
npm run build
```

构建产物输出到 `web/dist/` 目录。

---

## 二、Python AI 后端（AI 聊天 + PDF 解析）

### 创建虚拟环境

```bash
cd ai-server

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `ai-server/.env`：

```env
# LLM API 配置（OpenAI 兼容接口）
LLM_API_KEY=sk-your-api-key-here
LLM_API_BASE=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o-mini

# 服务配置
PORT=8000
LOG_LEVEL=INFO
```

**支持的 LLM API 提供商：**

| 提供商 | `LLM_API_BASE` | 说明 |
|--------|----------------|------|
| OpenAI | `https://api.openai.com/v1` | GPT-4o / GPT-4o-mini |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-plus 等 |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |
| 其他 | 任何 OpenAI 兼容 API 地址 | 确保支持 `/chat/completions` |

### 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

AI 后端运行在 `http://localhost:8000`，API 文档可访问 `http://localhost:8000/docs`。

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/ai/models` | 获取可用模型列表 |
| POST | `/api/ai/chat` | AI 对话（FormData: message, model, history, knowledge_file） |
| POST | `/api/pdf/parse` | PDF 解析（FormData: file） |

---

## 三、Python 游戏后端（猜词游戏 WebSocket）

### 创建虚拟环境

```bash
cd game-server

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `game-server/.env`：

```env
# Embedding API 配置（硅基流动 SiliconFlow）
EMBEDDING_API_KEY=your-api-key-here
EMBEDDING_API_URL=https://api.siliconflow.cn/v1/embeddings
EMBEDDING_MODEL=BAAI/bge-m3

# 游戏配置
SIMILARITY_THRESHOLD=0.75    # 相似度判定阈值（0~1）
ROUND_DURATION=60            # 默认每轮时长（秒）
MAX_GUESSES_PER_ROUND=3      # 每人每轮最大猜测次数

# 服务配置
GAME_PORT=3001
LOG_LEVEL=INFO
```

> **提示**：如果不配置 `EMBEDDING_API_KEY`，系统将自动回退到编辑距离字符串匹配模式。

### 启动

```bash
uvicorn app.main:combined_app --reload --host 0.0.0.0 --port 3001
```

游戏后端运行在 `http://localhost:3001`，Socket.IO 端点也在此端口。

### 词库管理

词库文件：`game-server/data/words.json`

```json
{
  "words": [
    {
      "id": 1,
      "word": "苹果",
      "hint": "一种常见的红色水果，也是一家科技公司的名字",
      "category": "fruit",
      "difficulty": 1
    }
  ],
  "nextId": 45
}
```

**可用分类**：`fruit`（水果）、`animal`（动物）、`movie`（电影）、`idiom`（成语）、`tech`（科技）

**难度等级**：1（简单）、2（中等）、3（较难）

---

## 四、完整启动流程（本地开发）

按以下顺序启动三个服务：

```bash
# 终端 1 — AI 后端
cd ai-server
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 游戏后端
cd game-server
.venv\Scripts\Activate.ps1
uvicorn app.main:combined_app --reload --host 0.0.0.0 --port 3001

# 终端 3 — 前端
cd web
npm run dev
```

全部启动后访问 `http://localhost:5173` 即可使用完整功能。
