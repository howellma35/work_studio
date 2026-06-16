import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';

const COOKIE_KEY = 'cookie_consent_accepted';

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(COOKIE_KEY) !== 'true') {
      setVisible(true);
    }
  }, []);

  const accept = () => {
    localStorage.setItem(COOKIE_KEY, 'true');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] animate-slide-in">
      <div className="mx-auto max-w-7xl px-4 pb-4 sm:px-6 lg:px-8">
        <div className="glass-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 sm:p-5 shadow-2xl">
          <div className="flex-1 text-sm text-[var(--color-text-secondary)]">
            本网站使用 Cookie 来提升用户体验和分析网站流量。继续使用即表示您同意我们的
            {' '}
            <Link to="/privacy" className="text-[var(--color-accent-light)] hover:underline">隐私政策</Link>
            {' '}和{' '}
            <Link to="/terms" className="text-[var(--color-accent-light)] hover:underline">服务条款</Link>。
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <button onClick={accept} className="btn-primary text-sm px-5 py-2">
              我知道了
            </button>
            <button
              onClick={() => setVisible(false)}
              className="p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              aria-label="关闭"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
