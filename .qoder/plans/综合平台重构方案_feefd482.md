# 综合 Web 平台重构方案

## 架构概览

```
项目根目录/
├── web/                    # 前端 (React + Vite + TailwindCSS + React Router)
│   ├── src/
│   │   ├── pages/          # 各板块页面
│   │   ├── components/     # 通用组件 (Header, Footer, CookieBanner 等)
│   │   ├── layouts/        # 布局组件
│   │   ├── hooks/          # 自定义 hooks
│   │   ├── config/         # 可配置变量
│   │   └── ...
├── server/                 # 现有 Node.js 后端 (猜词游戏)
├── ai-server/              # 新增 Python FastAPI 后端 (AI 聊天 + PDF 解析)
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── models/
│   ├── requirements.txt
│   └── Dockerfile
├── deploy/                 # 部署配置
│   ├── docker-compose.yml  # 更新加入 ai-server
│   └── nginx.conf          # 更新路由
└── docs/                   # 说明文档 (用户要求)
```

## Task 1: 前端基础架构搭建

**目标**: 引入 React Router + TailwindCSS，建立多页面路由框架

- 在 `web/` 中安装依赖:
  - `react-router-dom` (路由)
  - `tailwindcss @tailwindcss/vite` (CSS 框架)
  - `lucide-react` (图标库, MIT 协议)
  - `react-markdown` (Markdown 渲染, MIT)
  - `react-dropzone` (拖拽上传, MIT)
- 配置 TailwindCSS (v4, 使用 Vite 插件)
- 在 `web/src/config/site.ts` 中定义所有可配置变量 (`site_title`, `model_options`, `icp_number`, `organization_name`, `contact_email`)
- 配置 React Router，路由结构:
  - `/` — 首页 (推荐内容展示)
  - `/blog` — 技术博客列表
  - `/blog/:slug` — 博客详情
  - `/ai` — AI 前沿探索 (聊天页)
  - `/tools` — 日常小工具列表
  - `/tools/pdf` — PDF 解析工具
  - `/games` — 小游戏列表
  - `/games/word-guess` — 猜词游戏 (原功能)
  - `/open-source` — 开源声明页
  - `/privacy` — 隐私政策
  - `/terms` — 服务条款

## Task 2: 通用布局与 UI 组件

**目标**: 创建 Header/Footer/Cookie Banner/布局框架

设计风格: **暗色玻璃拟态 (Dark Glassmorphism)** — 深色背景 + 毛玻璃卡片 + 渐变点缀色

- `Layout.tsx` — 带 Header + Footer 的主布局，内容区域自适应
- `Header.tsx` — 顶部导航栏，四个板块链接 + 移动端汉堡菜单
- `Footer.tsx` — 底部固定区域: ICP 备案号、开源声明链接、隐私政策链接、服务条款链接
- `CookieBanner.tsx` — Cookie 使用提示横幅 (底部弹出，可关闭)
- `HomePage.tsx` — 首页: 四个板块的卡片式入口 + 推荐内容展示
- 响应式设计: 移动端汉堡菜单、平板双列、桌面端四列卡片

## Task 3: 小游戏板块 — 迁移猜词游戏

**目标**: 将现有猜词游戏嵌入为子页面

- 将现有 `App.tsx` 中的猜词排行榜逻辑迁移到 `pages/games/WordGuessGame.tsx`
- `pages/games/GamesList.tsx` — 小游戏列表页 (目前仅猜词游戏，预留扩展位)
- 保持原有 WebSocket 连接和 API 不变

## Task 4: 技术博客板块

**目标**: 实现静态博客展示

- `pages/blog/BlogList.tsx` — 博客列表页，卡片式布局
- `pages/blog/BlogPost.tsx` — 博客详情页，支持 Markdown 渲染
- 博客数据暂用静态 JSON 文件 (`web/src/data/blogs.json`) 存储，后续可扩展为 CMS
- 预置 2-3 篇示例博客文章

## Task 5: Python AI 后端服务 (ai-server)

**目标**: 新建 FastAPI 服务，处理 AI 聊天和 PDF 解析

技术选型 (全部 MIT/Apache-2.0 商业友好):
- `fastapi` (Web 框架, MIT)
- `uvicorn` (ASGI 服务器, BSD)
- `python-multipart` (文件上传)
- `openai` (Python SDK, Apache-2.0, 兼容各大模型 API)
- `pymupdf (fitz)` (PDF 解析, AGPL -> 改用 `pdfplumber` MIT 协议)
- `pdfplumber` (PDF 文本提取, MIT)
- `python-dotenv` (环境变量, BSD)
- `pydantic` (数据校验, MIT)

目录结构:
```
ai-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口 + CORS
│   ├── config.py            # 环境变量配置
│   ├── routers/
│   │   ├── chat.py          # AI 聊天 API
│   │   └── pdf.py           # PDF 解析 API
│   └── services/
│       ├── llm_service.py   # 大模型调用 (OpenAI 兼容接口)
│       └── pdf_service.py   # PDF 解析逻辑
├── requirements.txt
├── .env.example
└── Dockerfile
```

API 设计:
- `POST /api/ai/chat` — 发送聊天消息 (支持 model 参数切换)
- `POST /api/ai/chat/stream` — SSE 流式聊天响应
- `GET /api/ai/models` — 获取可用模型列表
- `POST /api/pdf/parse` — 上传并解析 PDF
- `GET /api/pdf/export` — 导出解析结果 (md/txt/json)
- `POST /api/pdf/upload-knowledge` — 上传知识库文件用于 RAG

## Task 6: AI 前沿探索前端页面

**目标**: 实现 AI 聊天界面

- `pages/ai/AIChat.tsx`:
  - 左侧: 会话历史列表 + 新建/清空/删除会话
  - 右侧: 聊天主区域
    - 顶部: 模型选择下拉框 (从 `model_options` 读取)
    - 中间: 消息列表 (支持 Markdown 渲染、代码高亮)
    - 底部: 输入框 + 文件上传按钮 (知识库) + 发送按钮
  - SSE 流式响应展示
  - 会话历史存储在 localStorage
  - RAG: 上传文件后，后端将文件内容作为上下文注入

## Task 7: PDF 解析工具前端页面

**目标**: 实现在线 PDF 解析器

- `pages/tools/PdfParser.tsx`:
  - 拖拽上传区域 (react-dropzone)
  - 上传后显示: 左侧 PDF 预览 (iframe)、右侧解析结果
  - 解析结果支持切换格式: 纯文本 / Markdown / JSON
  - 导出按钮 (下载对应格式文件)
  - 进度条 + 错误提示
- `pages/tools/ToolsList.tsx` — 工具列表页

## Task 8: 合规页面

**目标**: 实现法律合规相关页面

- `pages/legal/OpenSource.tsx` — 开源声明页，列出所有第三方包及许可证
- `pages/legal/Privacy.tsx` — 隐私政策
- `pages/legal/Terms.tsx` — 服务条款
- Footer 中固定展示 ICP 备案号 (可配置)

## Task 9: 后端集成与 Nginx 路由更新

**目标**: 更新 docker-compose 和 nginx 配置

- `deploy/docker-compose.yml`: 新增 `ai-server` 服务
- `deploy/nginx.conf`: 新增 `/api/ai/` 和 `/api/pdf/` 路由代理到 ai-server:8000
- `ai-server/Dockerfile`: Python 3.11-slim 多阶段构建

## Task 10: 日志模块

**目标**: 后端分级日志

- Node.js 后端: 使用 `pino` (MIT) 替代 console.log，支持 INFO/WARN/ERROR
- Python 后端: 使用标准库 `logging`，配置分级输出 + 文件日志
- 日志路径: 容器内 `/app/logs/`，docker-compose 挂载 volume

## Task 11: 说明文档

**目标**: 编写项目文档

- 创建 `docs/` 目录:
  - `docs/usage.md` — 使用说明
  - `docs/local-dev.md` — 本地调试步骤
  - `docs/deployment.md` — Docker 集群部署方案
  - `docs/troubleshooting.md` — 调试技巧与常见问题

## Task 12: 响应式适配与最终测试

**目标**: 确保多端兼容

- 测试各页面在手机 (375px)、平板 (768px)、桌面 (1440px) 下的表现
- 修复布局溢出、交互异常
- 确保所有路由跳转正常

## 技术选型汇总 (全部商业友好协议)

| 库 | 协议 | 用途 |
|---|---|---|
| React 18 | MIT | 前端框架 |
| Vite 6 | MIT | 构建工具 |
| TailwindCSS v4 | MIT | CSS 框架 |
| React Router v7 | MIT | 路由 |
| lucide-react | ISC (类MIT) | 图标 |
| react-markdown | MIT | Markdown 渲染 |
| react-dropzone | MIT | 拖拽上传 |
| FastAPI | MIT | Python Web |
| pdfplumber | MIT | PDF 解析 |
| openai SDK | Apache-2.0 | 大模型调用 |
| pino | MIT | Node.js 日志 |
| uvicorn | BSD | ASGI 服务器 |
