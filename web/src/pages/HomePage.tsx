import { Link } from 'react-router-dom';
import { FileText, Cpu, Wrench, Gamepad2, ArrowRight, Sparkles, Zap, Shield, Globe } from 'lucide-react';

const sections = [
  {
    path: '/blog',
    title: '技术博客',
    desc: '深度技术文章，涵盖前端、后端、DevOps 等领域实践与思考',
    icon: FileText,
    gradient: 'from-blue-500 to-cyan-400',
    tag: '精选文章',
  },
  {
    path: '/ai',
    title: 'AI 前沿探索',
    desc: '与多种大模型智能对话，上传知识库进行 RAG 问答，探索 AI 能力边界',
    icon: Cpu,
    gradient: 'from-violet-500 to-purple-400',
    tag: '热门推荐',
  },
  {
    path: '/tools',
    title: '日常小工具',
    desc: 'PDF 解析、格式转换等实用工具，提升日常工作效率',
    icon: Wrench,
    gradient: 'from-emerald-500 to-teal-400',
    tag: '实用工具',
  },
  {
    path: '/games',
    title: '小游戏',
    desc: '轻松有趣的互动小游戏，支持多人实时对战排行榜',
    icon: Gamepad2,
    gradient: 'from-orange-500 to-amber-400',
    tag: '互动娱乐',
  },
];

const features = [
  { icon: Sparkles, text: '现代设计', desc: '暗色玻璃拟态主题' },
  { icon: Zap, text: '高性能', desc: 'Vite 极速构建' },
  { icon: Shield, text: '商业友好', desc: '全栈 MIT 协议' },
  { icon: Globe, text: '多端适配', desc: '手机平板桌面' },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero */}
      <section className="text-center mb-20">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-[var(--color-text-secondary)] mb-6">
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-accent-light)]" />
          技术博客 · AI 对话 · 工具集 · 互动游戏
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold mb-5 leading-tight">
          <span className="bg-gradient-to-r from-[var(--color-accent-light)] via-white to-[var(--color-success)] bg-clip-text text-transparent">
            探索 · 创造 · 连接
          </span>
        </h1>
        <p className="text-base sm:text-lg text-[var(--color-text-secondary)] max-w-xl mx-auto leading-relaxed">
          一个集技术博客、AI 智能对话、实用工具和互动游戏于一体的现代 Web 平台
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/ai" className="btn-primary text-sm px-6 py-2.5 gap-2">
            <Cpu className="h-4 w-4" />
            体验 AI 对话
          </Link>
          <Link to="/blog" className="btn-ghost text-sm px-6 py-2.5 gap-2">
            <FileText className="h-4 w-4" />
            浏览博客
          </Link>
        </div>
      </section>

      {/* 四大板块 */}
      <section className="mb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {sections.map(({ path, title, desc, icon: Icon, gradient, tag }) => (
            <Link
              key={path}
              to={path}
              className="glass-card glass-card-hover p-6 sm:p-7 flex flex-col group relative overflow-hidden"
            >
              <span className={`absolute top-5 right-5 text-[10px] font-semibold px-2.5 py-1 rounded-full bg-gradient-to-r ${gradient} text-white uppercase tracking-wide`}>
                {tag}
              </span>
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <Icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-1.5">{title}</h3>
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{desc}</p>
              <div className="mt-4 flex items-center text-sm font-medium text-[var(--color-accent-light)] opacity-0 group-hover:opacity-100 transition-opacity">
                进入板块 <ArrowRight className="h-4 w-4 ml-1" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 特性 */}
      <section className="mb-8">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {features.map(({ icon: Icon, text, desc }) => (
            <div key={text} className="text-center p-4 glass-card">
              <Icon className="h-7 w-7 text-[var(--color-accent-light)] mx-auto mb-2" />
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">{text}</h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
