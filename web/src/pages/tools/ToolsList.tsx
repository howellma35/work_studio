import { Link } from 'react-router-dom';
import { FileText, ArrowRight, Wrench } from 'lucide-react';

const tools = [
  {
    path: '/tools/pdf',
    title: 'PDF 解析工具',
    desc: '上传 PDF 文件，提取文本内容，支持导出为 Markdown、TXT、JSON 格式',
    icon: FileText,
    gradient: 'from-emerald-500 to-teal-400',
    features: ['拖拽上传', '文本提取', '多格式导出'],
  },
];

export default function ToolsList() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
          日常小工具
        </h1>
        <p className="text-[var(--color-text-secondary)]">实用工具集合，提升日常工作效率</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map(({ path, title, desc, icon: Icon, gradient, features }) => (
          <Link
            key={path}
            to={path}
            className="glass-card glass-card-hover p-6 flex flex-col group"
          >
            <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
              <Icon className="h-7 w-7 text-white" />
            </div>
            <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-2">{title}</h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4 flex-1">{desc}</p>
            <div className="flex flex-wrap gap-2 mb-4">
              {features.map((f) => (
                <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-[var(--color-text-secondary)] border border-white/10">
                  {f}
                </span>
              ))}
            </div>
            <div className="flex items-center text-sm text-[var(--color-accent-light)]">
              打开工具 <ArrowRight className="h-4 w-4 ml-1" />
            </div>
          </Link>
        ))}

        <div className="glass-card p-6 flex flex-col items-center justify-center border border-dashed border-white/10 min-h-[200px]">
          <Wrench className="h-10 w-10 text-[var(--color-text-secondary)] mb-3 opacity-30" />
          <p className="text-sm text-[var(--color-text-secondary)] opacity-50">更多工具即将上线</p>
        </div>
      </div>
    </div>
  );
}
