# 2026-06-16 Mahongwei Studio - 使用说明

## 平台概览

本平台是一个综合性 Web 应用，集技术博客、AI 智能对话和 RAG 知识库于一体，采用简约现代设计风格，支持多端响应式适配（桌面、平板、手机）。

---

## 核心板块

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

### 2. AI 对话 (`/ai`)

多模型智能对话平台，支持知识库 RAG 问答。

**功能说明：**
- **模型切换**：顶部下拉框可选择不同的大模型
- **智能对话**：输入框发送消息，按 Enter 发送，Shift+Enter 换行
- **知识库问答（RAG）**：可选择关联知识库进行 RAG 问答，AI 将基于知识库中的文档内容进行回答
- **会话管理**：左侧栏可新建、切换、删除对话；对话历史持久化存储在浏览器 localStorage
- **Markdown 渲染**：AI 回复支持 Markdown 格式渲染（代码块、列表、表格等）
- **移动端适配**：小屏幕下侧边栏可收起，底部浮动按钮唤出

**使用前配置：**
需要在 `ai-server/.env` 中配置 LLM API Key，详见 [本地调试文档](./local-dev.md)。

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
