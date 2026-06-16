import { Link } from 'react-router-dom';
import { siteConfig } from '../config/site';

export default function Footer() {
  return (
    <footer className="flex-shrink-0 border-t border-white/10 bg-[#0a0a1a]/90 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-5 mb-5 text-sm">
          <div>
            <h4 className="font-semibold text-[var(--color-text-primary)] mb-2 text-xs uppercase tracking-wider">平台</h4>
            <ul className="space-y-1.5 text-[var(--color-text-secondary)]">
              <li><Link to="/blog" className="hover:text-[var(--color-accent-light)] transition-colors">技术博客</Link></li>
              <li><Link to="/ai" className="hover:text-[var(--color-accent-light)] transition-colors">AI前沿探索</Link></li>
              <li><Link to="/tools" className="hover:text-[var(--color-accent-light)] transition-colors">日常小工具</Link></li>
              <li><Link to="/games" className="hover:text-[var(--color-accent-light)] transition-colors">小游戏</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-[var(--color-text-primary)] mb-2 text-xs uppercase tracking-wider">法律</h4>
            <ul className="space-y-1.5 text-[var(--color-text-secondary)]">
              <li><Link to="/privacy" className="hover:text-[var(--color-accent-light)] transition-colors">隐私政策</Link></li>
              <li><Link to="/terms" className="hover:text-[var(--color-accent-light)] transition-colors">服务条款</Link></li>
              <li><Link to="/open-source" className="hover:text-[var(--color-accent-light)] transition-colors">开源声明</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-[var(--color-text-primary)] mb-2 text-xs uppercase tracking-wider">联系</h4>
            <a href={`mailto:${siteConfig.contact_email}`} className="text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] transition-colors break-all text-xs">
              {siteConfig.contact_email}
            </a>
          </div>
          <div>
            <h4 className="font-semibold text-[var(--color-text-primary)] mb-2 text-xs uppercase tracking-wider">运营方</h4>
            <p className="text-[var(--color-text-secondary)] text-xs">{siteConfig.organization_name}</p>
          </div>
        </div>

        <div className="border-t border-white/5 pt-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-[var(--color-text-secondary)]">
            &copy; {new Date().getFullYear()} {siteConfig.organization_name}. All rights reserved.
          </p>
          <a
            href="https://beian.miit.gov.cn/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] transition-colors"
          >
            {siteConfig.icp_number}
          </a>
        </div>
      </div>
    </footer>
  );
}
