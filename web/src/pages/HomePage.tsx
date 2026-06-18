import { Link } from 'react-router-dom';
import { BookOpen, Bot, Wrench, Gamepad2, ArrowRight } from 'lucide-react';

const sections = [
  {
    path: '/blog',
    title: '技术博客',
    desc: '深度技术文章，涵盖前端、后端、DevOps 等领域',
    icon: BookOpen,
    color: 'text-blue-600 bg-blue-50',
  },
  {
    path: '/ai',
    title: 'AI 对话',
    desc: '多模型智能对话，支持知识库 RAG 问答',
    icon: Bot,
    color: 'text-violet-600 bg-violet-50',
  },
  {
    path: '/tools',
    title: '日常工具',
    desc: 'PDF 解析、格式转换等实用工具',
    icon: Wrench,
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    path: '/games',
    title: '小游戏',
    desc: '轻松有趣的互动游戏，支持多人对战',
    icon: Gamepad2,
    color: 'text-orange-600 bg-orange-50',
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:py-20">
      {/* Hero */}
      <section className="text-center mb-16">
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[var(--color-text)] mb-4 tracking-tight">
          探索 · 创造 · 连接
        </h1>
        <p className="text-[var(--color-text-secondary)] max-w-md mx-auto text-base sm:text-lg">
          集技术博客、AI 对话、实用工具和互动游戏于一体的平台
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/ai" className="btn-primary">体验 AI 对话</Link>
          <Link to="/blog" className="btn-secondary">浏览博客</Link>
        </div>
      </section>

      {/* 四大板块 */}
      <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sections.map(({ path, title, desc, icon: Icon, color }) => (
          <Link
            key={path}
            to={path}
            className="card card-hover p-5 flex items-start gap-4 group"
          >
            <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center shrink-0`}>
              <Icon size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-[var(--color-text)] mb-0.5">{title}</h3>
              <p className="text-sm text-[var(--color-text-secondary)]">{desc}</p>
            </div>
            <ArrowRight size={16} className="text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-1" />
          </Link>
        ))}
      </section>
    </div>
  );
}
