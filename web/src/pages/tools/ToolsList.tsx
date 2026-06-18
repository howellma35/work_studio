import { Link } from 'react-router-dom';
import { FileText, ArrowRight, Wrench } from 'lucide-react';

const tools = [
  {
    path: '/tools/pdf',
    title: 'PDF 解析工具',
    desc: '上传 PDF 文件，提取文本内容，支持导出为 Markdown、TXT、JSON 格式',
    icon: FileText,
    color: 'text-emerald-600 bg-emerald-50',
    features: ['拖拽上传', '文本提取', '多格式导出'],
  },
];

export default function ToolsList() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:py-14">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-2">日常工具</h1>
        <p className="text-[var(--color-text-secondary)] text-sm">实用工具集合，提升日常工作效率</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map(({ path, title, desc, icon: Icon, color, features }) => (
          <Link
            key={path}
            to={path}
            className="card card-hover p-5 flex flex-col group"
          >
            <div className={`w-11 h-11 rounded-lg ${color} flex items-center justify-center mb-3`}>
              <Icon className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-[var(--color-text)] mb-1.5">{title}</h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-3 flex-1">{desc}</p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {features.map((f) => (
                <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-muted)] text-[var(--color-text-secondary)]">
                  {f}
                </span>
              ))}
            </div>
            <div className="flex items-center text-sm text-[var(--color-accent)] font-medium">
              打开工具 <ArrowRight className="h-4 w-4 ml-1" />
            </div>
          </Link>
        ))}

        <div className="card p-5 flex flex-col items-center justify-center border-dashed min-h-[200px]">
          <Wrench className="h-8 w-8 text-[var(--color-text-muted)] mb-2 opacity-40" />
          <p className="text-sm text-[var(--color-text-muted)]">更多工具即将上线</p>
        </div>
      </div>
    </div>
  );
}
