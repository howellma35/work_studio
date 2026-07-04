import { Link } from 'react-router-dom';
import { BookOpen, Bot, Database, ArrowRight, Car, Sparkles } from 'lucide-react';

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
    path: '/knowledge',
    title: '知识库',
    desc: '上传文档构建知识库，AI 自动检索相关内容',
    icon: Database,
    color: 'text-emerald-600 bg-emerald-50',
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
          集技术博客、AI 对话与 RAG 知识库于一体的平台
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/ai" className="btn-primary">体验 AI 对话</Link>
          <Link to="/blog" className="btn-secondary">浏览博客</Link>
        </div>
      </section>

      {/* ★ 最新功能：AutoMind 智能车机助手 ★ */}
      <section className="mb-10">
        <a
          href="/vehicle/"
          className="block rounded-2xl overflow-hidden border border-slate-700/40 group transition-all duration-300 hover:shadow-2xl hover:shadow-blue-500/10 hover:border-blue-500/40"
          style={{
            background: 'linear-gradient(135deg, #0c1222 0%, #1a1a3e 50%, #0f172a 100%)',
          }}
        >
          <div className="p-6 sm:p-8 flex flex-col sm:flex-row items-start gap-6">
            {/* 图标 */}
            <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 shadow-lg shadow-blue-500/30 shrink-0">
              <Car className="h-8 w-8 text-white" />
            </div>

            {/* 内容 */}
            <div className="flex-1 min-w-0">
              {/* NEW 徽章 */}
              <div className="inline-flex items-center gap-1.5 mb-3">
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-sm">
                  <Sparkles className="h-3 w-3" />
                  最新功能
                </span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2 tracking-tight">
                AutoMind 智能车机助手
              </h2>
              <p className="text-slate-300 text-sm sm:text-base leading-relaxed mb-4 max-w-xl">
                基于 LangGraph 多 Agent 架构的车载智能助手。集成高德地图实时导航、多媒体控制、
                车辆状态查询、天气提醒等功能，支持自然语言交互与 Human-in-the-Loop 决策。
              </p>

              {/* 功能标签 */}
              <div className="flex flex-wrap gap-2 mb-4">
                {['🧭 实时导航', '🎵 多媒体', '🚗 车控', '🌤 天气', '⏰ 提醒'].map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-white/10 text-slate-200 backdrop-blur-sm border border-white/10"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              {/* CTA */}
              <div className="flex items-center gap-2 text-sm text-blue-400 font-medium group-hover:text-cyan-300 transition-colors">
                <span>立即体验</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        </a>
      </section>

      {/* 常规板块 */}
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
