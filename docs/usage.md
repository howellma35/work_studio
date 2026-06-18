# Mahongwei Studio - 使用说明

## 平台概览

本平台是一个综合性 Web 应用，集技术博客、AI 智能对话、实用工具和互动游戏于一体，采用简约现代设计风格，支持多端响应式适配（桌面、平板、手机）。

---

## 四大核心板块

### 1. 技术博客 (`/blog`)

技术文章展示平台，支持 Markdown 富文本渲染。

**功能说明：**
- 文章列表页展示标题、摘要、发布日期、预计阅读时间和标签
- 点击文章卡片进入详情页面，支持 Markdown 渲染（代码高亮、表格、列表等）
- 使用 `@tailwindcss/typography` 插件提供优雅的 prose 排版

**如何添加新文章：**
在 `web/src/data/blogs.json` 中按以下格式添加条目，并在 `content` 字段编写 Markdown 内容：

```json
{
  "slug": "my-new-post",
  "title": "文章标题",
  "summary": "文章摘要",
  "tags": ["前端", "React"],
  "date": "2025-01-01",
  "readTime": "5 min",
  "content": "# 标题\n\n正文内容..."
}
```

---

### 2. AI 前沿探索 (`/ai`)

多模型智能对话平台，支持知识库 RAG 问答。

**功能说明：**
- **模型切换**：顶部下拉框可选择不同的大模型（GPT-4o、Claude 3.5 Sonnet、通义千问 Plus、DeepSeek Chat 等）
- **智能对话**：输入框发送消息，按 Enter 发送，Shift+Enter 换行
- **知识库问答（RAG）**：点击上传按钮上传 PDF / TXT / MD 文件（最大 50MB），AI 将基于文件内容进行回答
- **会话管理**：左侧栏可新建、切换、删除对话；对话历史持久化存储在浏览器 localStorage
- **Markdown 渲染**：AI 回复支持 Markdown 格式渲染（代码块、列表、表格等）
- **移动端适配**：小屏幕下侧边栏可收起，底部浮动按钮唤出

**使用前配置：**
需要在 `ai-server/.env` 中配置 LLM API Key，详见 [本地调试文档](./local-dev.md)。

---

### 3. 日常小工具 (`/tools`)

实用工具集合。

#### PDF 解析工具 (`/tools/pdf`)

- **上传方式**：拖拽 PDF 文件到上传区域，或点击选择文件（最大 50MB）
- **文本提取**：自动提取 PDF 中的文本内容和表格数据
- **PDF 预览**：上传后可在页面左侧直接预览 PDF 原文
- **多格式导出**：支持导出为 TXT / Markdown / JSON 三种格式
- **元数据展示**：显示文件名、页数等基本信息

**注意事项：**
- 仅支持文字型 PDF，扫描件（图片型）无法提取文本
- 后端使用 pdfplumber（MIT 协议）进行解析

---

### 4. 小游戏 (`/games`)

互动游戏集合，目前包含猜词大挑战。

#### 猜词大挑战 (`/games/word-guess`)

多人实时猜词游戏，适用于直播互动场景。

**主播控制面板（左侧）：**
- 选择词语分类：水果、动物、电影、成语、科技（或随机）
- 选择难度等级：简单 / 中等 / 较难（或随机）
- 选择游戏时长：1分钟 ~ 2小时
- 点击「开始新一轮」启动游戏
- 游戏进行中显示倒计时和提示词
- 可提前结束当前轮次

**排行榜面板（右侧）：**
- 实时显示所有参与者的猜测和相似度得分
- 前三名使用金银铜牌样式高亮
- 每 3 秒自动刷新排行

**游戏机制：**
- 系统随机从词库中选词，展示提示给观众
- 观众输入猜测，系统通过 Embedding 语义向量计算相似度（0~100%）
- 相似度超过阈值（默认 75%）即判定猜对
- 每人每轮最多猜测 3 次

**词库管理：**
词库文件位于 `game-server/data/words.json`，包含词语、提示、分类和难度信息，可自行编辑扩充。

---

## 法律与合规页面

| 页面路径 | 说明 |
|---------|------|
| `/privacy` | 隐私政策 — 说明数据收集、使用和保护方式 |
| `/terms` | 服务条款 — 平台使用规范和免责条款 |
| `/open-source` | 开源声明 — 列出所有使用的开源组件及其协议 |

---

## 可配置变量

以下变量可在 `web/src/config/site.ts` 中直接修改，也可通过环境变量设置（在 `web/.env.local` 中）：

| 变量 | 环境变量名 | 默认值 | 说明 |
|------|-----------|--------|------|
| `site_title` | `VITE_SITE_TITLE` | Mahongwei Studio | 网站标题（Header Logo 旁显示） |
| `organization_name` | `VITE_ORG_NAME` | Mahongwei Studio | 运营组织名称（Footer 显示） |
| `icp_number` | `VITE_ICP_NUMBER` | 京ICP备XXXXXXXX号-X | ICP 备案编号（Footer 显示） |
| `contact_email` | `VITE_CONTACT_EMAIL` | contact@mahongwei.com.cn | 联系邮箱（Footer 显示） |
| `model_options` | — | 代码中配置 | AI 聊天可用模型列表 |

---

## Cookie 提示

首次访问时底部会弹出 Cookie 同意横幅，用户点击「我知道了」后状态存入 localStorage，不再重复弹出。
