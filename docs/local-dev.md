# 本地开发指南

## 前置要求

| 工具 | 最低版本 | 用途 |
|------|---------|------|
| Node.js | 20+ | 前端构建工具链（Vite、TypeScript） |
| Python | 3.11+ | AI 后端 + 游戏后端 |
| pip | 最新版 | Python 包管理器 |

> 本项目后端全部使用 Python，**不需要** Redis 或 Node.js 后端。

---

## 项目目录结构总览

```
rag_game/
├── web/                     # ── 前端 ── React + Vite + TypeScript + TailwindCSS v4
│   ├── public/              #    静态资源（不经 Vite 处理的文件）
│   │   └── viewer.html      #    PDF 在线预览页面
│   ├── src/
│   │   ├── components/      #    通用可复用组件
│   │   │   ├── Header.tsx       #  顶部导航栏（桌面端标签 + 移动端抽屉菜单）
│   │   │   ├── Footer.tsx       #  底部页脚（链接、版权、备案号）
│   │   │   ├── CookieBanner.tsx  #  Cookie 同意横幅（首次访问弹出）
│   │   │   ├── GameStatus.tsx    #  猜词游戏控制面板（分类/难度/时长选择、倒计时）
│   │   │   └── Leaderboard.tsx   #  猜词游戏排行榜组件
│   │   ├── config/
│   │   │   └── site.ts          #  站点全局配置（标题、组织名、模型列表等）
│   │   ├── data/
│   │   │   └── blogs.json       #  博客文章数据（标题、摘要、Markdown 正文）
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts  #  Socket.IO 连接 Hook（管理游戏状态和消息）
│   │   ├── layouts/
│   │   │   └── Layout.tsx       #  全局布局（Header + 内容区 + Footer）
│   │   ├── pages/
│   │   │   ├── HomePage.tsx     #  首页（四大板块入口卡片）
│   │   │   ├── ai/
│   │   │   │   └── AIChat.tsx       #  AI 对话页面（侧边栏+聊天+知识库上传）
│   │   │   ├── blog/
│   │   │   │   ├── BlogList.tsx     #  博客文章列表
│   │   │   │   └── BlogPost.tsx     #  博客文章详情（Markdown 渲染）
│   │   │   ├── games/
│   │   │   │   ├── GamesList.tsx    #  游戏列表
│   │   │   │   └── WordGuessGame.tsx # 猜词游戏主页面
│   │   │   ├── legal/
│   │   │   │   ├── OpenSource.tsx   #  开源声明（依赖清单表格）
│   │   │   │   ├── Privacy.tsx      #  隐私政策
│   │   │   │   └── Terms.tsx        #  服务条款
│   │   │   └── tools/
│   │   │       ├── ToolsList.tsx    #  工具列表
│   │   │       └── PdfParser.tsx    #  PDF 解析工具（上传+预览+导出）
│   │   ├── App.tsx              #  React Router 路由配置
│   │   ├── index.css            #  全局样式（TailwindCSS v4 设计系统变量）
│   │   ├── main.tsx             #  React 入口（挂载到 #root）
│   │   └── vite-env.d.ts        #  Vite 类型声明
│   ├── index.html               #  HTML 模板入口
│   ├── vite.config.ts           #  Vite 配置（Tailwind 插件 + API 代理规则）
│   ├── package.json             #  npm 依赖和脚本
│   └── tsconfig.json            #  TypeScript 编译配置
│
├── ai-server/               # ── AI 后端 ── Python FastAPI（对话 + PDF 解析）
│   ├── app/
│   │   ├── __init__.py          #  Python 包标识
│   │   ├── config.py            #  环境变量读取（LLM_API_KEY 等）
│   │   ├── main.py              #  应用入口（FastAPI 实例、CORS、路由注册、日志）
│   │   ├── routers/
│   │   │   ├── chat.py              #  POST /api/ai/chat — AI 对话接口
│   │   │   └── pdf.py               #  POST /api/pdf/parse — PDF 解析接口
│   │   └── services/
│   │       ├── llm_service.py       #  OpenAI 兼容 API 调用封装
│   │       └── pdf_service.py       #  pdfplumber 文本提取封装
│   ├── .env.example             #  环境变量模板（复制为 .env 后编辑）
│   ├── .env                     #  实际环境变量（不提交到 Git）
│   ├── requirements.txt         #  Python 依赖清单
│   ├── Dockerfile               #  Docker 镜像构建文件
│   └── logs/                    #  运行时日志目录（自动创建）
│
├── game-server/             # ── 游戏后端 ── Python FastAPI + Socket.IO
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py            #  环境变量读取（EMBEDDING_API_KEY 等）
│   │   ├── main.py              #  应用入口（FastAPI + Socket.IO 组合 ASGI 应用）
│   │   ├── services/
│   │   │   ├── game_service.py      #  游戏核心逻辑（轮次管理、词库、猜词处理）
│   │   │   ├── embedding_service.py #  Embedding 向量语义匹配（含编辑距离回退）
│   │   │   └── rank_service.py      #  排行榜（内存实现，无需 Redis）
│   │   └── ws/
│   │       └── handler.py           #  Socket.IO 事件处理（连接/猜测/开始/结束轮次）
│   ├── data/
│   │   └── words.json             #  词库数据（词语、提示、分类、难度）
│   ├── .env.example
│   ├── .env
│   ├── requirements.txt
│   ├── Dockerfile
│   └── logs/
│
├── server/                  # ── [已弃用] ── 旧 Node.js 后端，保留供参考
├── miniprogram/             # ── [已弃用] ── 旧抖音小程序，保留供参考
│
├── deploy/                  # ── 部署配置 ──
│   ├── docker-compose.yml       #  Docker Compose 多服务编排
│   └── nginx.conf               #  Nginx 反向代理配置（含 SSL + WebSocket）
│
├── docs/                    # ── 项目文档 ──
│   ├── usage.md                 #  功能使用说明
│   ├── local-dev.md             #  本地开发指南（本文件）
│   ├── deployment.md            #  Docker 部署方案
│   └── troubleshooting.md       #  调试技巧与问题排查
│
├── .gitignore               #  Git 忽略规则
└── LICENSE                  #  Apache-2.0 开源协议
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

`web/vite.config.ts` 已配置以下代理，开发模式下 API 请求自动转发到对应后端：

| 前端请求路径 | 代理目标 | 说明 |
|-------------|---------|------|
| `/api/ai/*` | `http://localhost:8000` | AI 聊天接口 |
| `/api/pdf/*` | `http://localhost:8000` | PDF 解析接口 |
| `/api/game/*` | `http://localhost:3001` | 游戏 REST 接口 |
| `/socket.io/*` | `http://localhost:3001` | 游戏 WebSocket（Socket.IO） |

### 5. 构建生产版本

```bash
cd web
npm run build
```

构建产物输出到 `web/dist/` 目录。

---

## 二、AI 后端（ai-server/）

> 负责 AI 对话 + PDF 解析，运行在 **http://localhost:8000**。

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

激活成功后，终端提示符前会出现 `(.venv)` 标识。

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

编辑 `ai-server/.env`，**必须填入 LLM API Key**：

```env
# LLM API 配置（OpenAI 兼容接口）
LLM_API_KEY=sk-your-api-key-here
LLM_API_BASE=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o-mini

# 服务配置
AI_PORT=8000
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

**支持的 LLM 提供商：**

| 提供商 | `LLM_API_BASE` 值 |
|--------|-------------------|
| OpenAI | `https://api.openai.com/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 月之暗面 | `https://api.moonshot.cn/v1` |
| 其他 | 任何 OpenAI 兼容 API 地址 |

### 4. 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后访问 **http://localhost:8000/docs** 可查看 Swagger API 文档。

### API 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/ai/models` | 获取可用模型列表 |
| POST | `/api/ai/chat` | AI 对话（FormData: message, model, history, knowledge_file） |
| POST | `/api/pdf/parse` | PDF 解析（FormData: file） |

---

## 三、游戏后端（game-server/）

> 负责猜词游戏 WebSocket 通信，运行在 **http://localhost:3001**。

### 1. 创建 Python 虚拟环境

```bash
cd game-server

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
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
copy .env.example .env      # Windows
cp .env.example .env        # Linux/Mac
```

编辑 `game-server/.env`：

```env
# Embedding API 配置（硅基流动 SiliconFlow）
EMBEDDING_API_KEY=your_api_key_here
EMBEDDING_API_URL=https://api.siliconflow.cn/v1/embeddings
EMBEDDING_MODEL=BAAI/bge-m3

# 游戏配置
SIMILARITY_THRESHOLD=0.75
ROUND_DURATION=60
MAX_GUESSES_PER_ROUND=3

# 服务配置
GAME_PORT=3001
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

> 不配置 `EMBEDDING_API_KEY` 也能运行，系统自动回退到编辑距离字符串匹配（精度较低）。

### 4. 启动

```bash
uvicorn app.main:combined_app --reload --host 0.0.0.0 --port 3001
```

> 注意入口是 `combined_app`（Socket.IO 包装的 ASGI 应用），不是 `app`。

### 词库管理

词库文件位于 `game-server/data/words.json`，结构如下：

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

- **分类**：`fruit`（水果）、`animal`（动物）、`movie`（电影）、`idiom`（成语）、`tech`（科技）
- **难度**：1（简单）、2（中等）、3（较难）

---

## 四、完整启动流程

同时打开 **3 个终端**，按顺序启动：

### 终端 1 — AI 后端

```bash
cd ai-server
.venv\Scripts\Activate.ps1        # 激活虚拟环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 终端 2 — 游戏后端

```bash
cd game-server
.venv\Scripts\Activate.ps1        # 激活虚拟环境
uvicorn app.main:combined_app --reload --host 0.0.0.0 --port 3001
```

### 终端 3 — 前端

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
| AI 后端 | 8000 | Python FastAPI |
| 游戏后端 | 3001 | Python FastAPI + python-socketio |

---

## 技术栈说明

**前端**：React 18 + Vite 6 + TypeScript + TailwindCSS v4（`@tailwindcss/vite` 插件）+ React Router v7

**AI 后端**：FastAPI + openai（Python SDK）+ pdfplumber + uvicorn

**游戏后端**：FastAPI + python-socketio + httpx + uvicorn（Socket.IO 与前端 `socket.io-client` 兼容）
