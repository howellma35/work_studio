/**
 * 博客数据动态加载器
 *
 * 通过 Vite 插件 virtual:blog-docs（见 vite.config.ts 的 blogDocsPlugin）
 * 在构建时读取 docs/ 和 vehicle-agent/docs/ 下的所有 .md 文件。
 * 用 fs 读取而非 import.meta.glob，是为了同时兼容本地开发与 Docker 构建
 * 两种不同的目录层级（详见 vite.config.ts 注释）。
 *
 * 新增博客：只需在 docs/ 或 vehicle-agent/docs/ 目录下放一个 .md 文件即可。
 * - 标题：取第一个 # 标题
 * - 日期：优先从文件名提取（如 2026-06-16-xxx.md），否则用当天日期
 * - 标签：根据内容关键词自动推断
 * - 正文：完整 Markdown 内容
 */

import rawDocs from 'virtual:blog-docs';

// ===== 元数据提取 =====

/** 从 Markdown 内容中提取 H1 标题，去掉日期前缀 */
function extractTitle(content: string, fallback: string): string {
  const match = content.match(/^#\s+(.+)$/m);
  if (!match) return fallback;
  return match[1].replace(/^\d{4}-\d{2}-\d{2}\s*/, '');
}

/** 从文件名中提取日期 (YYYY-MM-DD) */
function extractDate(filename: string): string {
  const match = filename.match(/(\d{4}-\d{2}-\d{2})/);
  if (match) return match[1];
  return new Date().toISOString().split('T')[0];
}

/** 生成 URL 友好的 slug */
function makeSlug(filepath: string): string {
  const filename = filepath.split('/').pop() || '';
  return filename.replace(/\.md$/, '');
}

/** 根据内容关键词自动推断标签 */
function inferTags(title: string, content: string): string[] {
  const keywords: [string[], string][] = [
    [['RAGFlow', 'ragflow'], 'RAGFlow'],
    [['Docker', 'docker', '容器'], 'Docker'],
    [['Langfuse', '可观测'], 'Langfuse'],
    [['frp', '内网穿透', 'frpc', 'frps'], 'frp'],
    [['CopilotKit', 'AG-UI'], 'CopilotKit'],
    [['LangGraph', 'Agent'], 'LangGraph'],
    [['Nginx', 'SSL', 'HTTPS', '证书'], '部署'],
    [['镜像源', '代理', 'registry'], '运维'],
    [['OBS', '抖音', '直播'], '直播'],
    [['RAG', '知识库', '向量'], 'RAG'],
    [['React', 'Vite', '前端'], '前端'],
    [['FastAPI', 'Python'], '后端'],
    [['踩坑', '排查', '调试', 'troubleshoot'], '踩坑'],
    [['开发日志', '开发历程', '开发记录'], '开发日志'],
  ];

  const tags = new Set<string>();
  const text = `${title} ${content.slice(0, 800)}`;
  for (const [words, tag] of keywords) {
    if (words.some(w => text.includes(w))) tags.add(tag);
  }
  if (tags.size === 0) tags.add('技术');
  return [...tags].slice(0, 4); // 最多 4 个标签
}

// ===== 构建博客数据 =====

interface BlogPost {
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  date: string;
  readTime: string;
  content: string;
}

const posts: BlogPost[] = rawDocs.map(({ name, content: raw }) => {
  const slug = makeSlug(name);

  // 标题 + 日期
  const title = extractTitle(raw, name.replace(/\.md$/, '').replace(/^\d{4}-\d{2}-\d{2}-/, ''));
  const date = extractDate(name);

  // 去掉标题行和紧跟的描述行（> 开头的），正文从实际内容开始
  const body = raw.replace(/^#\s+.+\n+/m, '').replace(/^>\s+.+\n+/gm, '');

  // 摘要（取正文前 120 字，去除 Markdown 标记）
  const plainText = body.replace(/```[\s\S]*?```/g, '').replace(/[#*`|>\-]/g, '').replace(/\n+/g, ' ').trim();
  const summary = plainText.slice(0, 120) + (plainText.length > 120 ? '…' : '');

  return {
    slug,
    title,
    summary,
    tags: inferTags(title, body),
    date,
    readTime: `${Math.max(1, Math.ceil(body.length / 500))} 分钟`,
    content: body,
  };
});

// 按日期降序排列
posts.sort((a, b) => b.date.localeCompare(a.date));

export default posts;
export type { BlogPost };
