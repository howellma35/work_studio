import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { siteConfig } from '../../config/site';

export default function Privacy() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:py-14">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] mb-6 transition-colors">
        <ArrowLeft className="h-4 w-4" /> 返回首页
      </Link>

      <h1 className="text-2xl font-bold mb-1">隐私政策</h1>
      <p className="text-xs text-[var(--color-text-muted)] mb-6">最后更新: 2026年6月16日</p>

      <div className="card p-5 sm:p-7 space-y-5 text-[var(--color-text-secondary)] text-sm leading-relaxed">
        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">1. 信息收集</h2>
          <p>我们可能收集以下类型的信息：</p>
          <ul className="list-disc pl-5 mt-1.5 space-y-1">
            <li><strong className="text-[var(--color-text)]">账户信息</strong>：当您注册账户时，我们可能收集您的用户名、邮箱等基本信息。</li>
            <li><strong className="text-[var(--color-text)]">使用数据</strong>：包括访问日志、页面浏览记录、功能使用情况等，用于改善服务质量。</li>
            <li><strong className="text-[var(--color-text)]">上传内容</strong>：您上传的文件（如 PDF）仅用于即时处理，处理完成后不会长期存储。</li>
            <li><strong className="text-[var(--color-text)]">对话记录</strong>：AI 对话内容存储在您的浏览器本地存储中，服务端不会持久化保存。</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">2. Cookie 使用</h2>
          <p>我们使用 Cookie 和类似技术来：</p>
          <ul className="list-disc pl-5 mt-1.5 space-y-1">
            <li>记住您的偏好设置（如 Cookie 同意状态）</li>
            <li>分析网站流量和使用模式</li>
            <li>维护和改善服务性能</li>
          </ul>
          <p className="mt-1.5">您可以通过浏览器设置管理或禁用 Cookie，但这可能影响部分功能的正常使用。</p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">3. 数据共享</h2>
          <p>我们不会将您的个人信息出售给第三方。在以下情况下，我们可能共享信息：</p>
          <ul className="list-disc pl-5 mt-1.5 space-y-1">
            <li>经您明确同意</li>
            <li>法律法规要求</li>
            <li>保护 {siteConfig.organization_name} 的合法权益</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">4. 第三方服务</h2>
          <p>本平台可能调用第三方 AI 模型 API（如 OpenAI、Anthropic 等）。您发送的对话内容会传输至这些服务提供商进行处理。请参阅各提供商的隐私政策了解详细信息。</p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">5. 数据安全</h2>
          <p>我们采取合理的技术措施保护您的信息安全，但无法保证绝对的互联网安全。建议您妥善保管账户凭据。</p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-[var(--color-text)] mb-2">6. 联系我们</h2>
          <p>如对本隐私政策有疑问，请联系：<a href={`mailto:${siteConfig.contact_email}`} className="text-[var(--color-accent)] hover:underline">{siteConfig.contact_email}</a></p>
        </section>
      </div>
    </div>
  );
}
