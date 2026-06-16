import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { siteConfig } from '../../config/site';

export default function Terms() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] mb-8 transition-colors">
        <ArrowLeft className="h-4 w-4" /> 返回首页
      </Link>

      <h1 className="text-3xl font-bold mb-2">服务条款</h1>
      <p className="text-sm text-[var(--color-text-secondary)] mb-8">最后更新: 2026年6月16日</p>

      <div className="glass-card p-6 sm:p-8 space-y-6 text-[var(--color-text-secondary)] text-sm leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">1. 服务说明</h2>
          <p>{siteConfig.site_title}（以下简称"本平台"）由 {siteConfig.organization_name} 运营。本平台提供技术博客、AI 智能对话、工具集和互动游戏等服务。使用本平台即表示您同意遵守以下条款。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">2. 用户行为规范</h2>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>您不得利用本平台从事任何违法活动</li>
            <li>不得上传包含恶意代码、病毒或有害内容的文件</li>
            <li>不得滥用 AI 对话功能生成违法、侵权或不当内容</li>
            <li>不得对本平台进行逆向工程或恶意攻击</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">3. 知识产权</h2>
          <p>本平台的界面设计、代码实现和品牌标识受知识产权法保护。平台中引用的开源软件遵循各自的许可证协议（详见<a href="/open-source" className="text-[var(--color-accent-light)] hover:underline">开源声明</a>）。</p>
          <p className="mt-2">您上传的内容版权归您所有，但您授权本平台在服务提供过程中进行必要的处理。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">4. AI 生成内容</h2>
          <p>AI 对话功能生成的内容仅供参考，可能存在不准确或错误。本平台不对 AI 生成内容的准确性、完整性或适用性做出任何保证。请勿将 AI 输出作为专业建议的唯一依据。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">5. 服务变更与终止</h2>
          <p>我们保留随时修改、暂停或终止部分或全部服务的权利，且无需事先通知。对于服务中断造成的任何损失，本平台不承担责任。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">6. 免责声明</h2>
          <p>本平台按"现状"提供，不做任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和不侵权的保证。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">7. 付费服务（如适用）</h2>
          <p>本平台可能提供付费增值服务。付费服务的具体内容、价格和退款政策将在购买页面单独说明。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">8. 条款修改</h2>
          <p>我们可能定期更新本服务条款。重大变更将通过平台公告或邮件方式通知。继续使用本平台即表示您同意更新后的条款。</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">9. 联系方式</h2>
          <p>如有任何疑问，请联系：<a href={`mailto:${siteConfig.contact_email}`} className="text-[var(--color-accent-light)] hover:underline">{siteConfig.contact_email}</a></p>
        </section>
      </div>
    </div>
  );
}
