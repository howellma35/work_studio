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
    <div className="fixed bottom-0 inset-x-0 z-50 p-4">
      <div className="mx-auto max-w-5xl">
        <div className="card flex items-center justify-between gap-4 px-4 py-3 shadow-lg">
          <p className="text-sm text-[var(--color-text-secondary)] flex-1">
            我们使用 Cookie 来提升体验。
            <Link to="/privacy" className="text-[var(--color-accent)] hover:underline ml-1">隐私政策</Link>
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={accept} className="btn-primary text-sm !py-1.5 !px-4">
              知道了
            </button>
            <button
              onClick={() => setVisible(false)}
              className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
