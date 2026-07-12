import { Link } from 'react-router-dom';
import { siteConfig } from '../config/site';

export default function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg-soft)] mt-auto">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6">
          {/* 左侧：品牌 */}
          <div className="shrink-0">
            <p className="font-semibold text-sm text-[var(--color-text)]">{siteConfig.organization_name}</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">{siteConfig.contact_email}</p>
          </div>

          {/* 中间：链接 */}
          <div className="flex gap-8 text-xs text-[var(--color-text-secondary)]">
            <div className="flex flex-col gap-1.5">
              <Link to="/blog" className="hover:text-[var(--color-accent)]">博客</Link>
              <Link to="/ai" className="hover:text-[var(--color-accent)]">AI 对话</Link>
              <Link to="/tools" className="hover:text-[var(--color-accent)]">工具</Link>
              <Link to="/games" className="hover:text-[var(--color-accent)]">游戏</Link>
            </div>
            <div className="flex flex-col gap-1.5">
              <Link to="/privacy" className="hover:text-[var(--color-accent)]">隐私政策</Link>
              <Link to="/terms" className="hover:text-[var(--color-accent)]">服务条款</Link>
              <Link to="/open-source" className="hover:text-[var(--color-accent)]">开源声明</Link>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-4 border-t border-[var(--color-border)] flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[var(--color-text-muted)]">
          <p>&copy; {new Date().getFullYear()} {siteConfig.organization_name}. All rights reserved.</p>
          <div className="flex items-center gap-3">
            <a
              href="https://beian.miit.gov.cn/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[var(--color-accent)] transition-colors"
            >
              {siteConfig.icp_number}
            </a>
            <span className="text-[var(--color-border)]">|</span>
            <a
              href="http://www.beian.gov.cn/portal/registerSystemInfo?recordcode=31011402022120"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[var(--color-accent)] transition-colors inline-flex items-center gap-1"
            >
              <img
                src="/police.png"
                alt="公安备案"
                className="w-4 h-4 inline-block"
              />
              {siteConfig.police_record_number}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
