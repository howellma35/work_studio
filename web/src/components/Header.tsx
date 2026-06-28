import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, BookOpen, Bot, Database } from 'lucide-react';
import { siteConfig } from '../config/site';

const navItems = [
  { path: '/blog', label: '博客', icon: BookOpen },
  { path: '/ai', label: 'AI 对话', icon: Bot },
  { path: '/knowledge', label: '知识库', icon: Database },
];

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // 路由变化时关闭菜单
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // 菜单打开时禁止 body 滚动
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-[var(--color-border)] bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-[var(--color-text)] font-semibold text-base hover:opacity-80 transition-opacity">
            {siteConfig.site_title}
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors
                  ${isActive(path)
                    ? 'text-[var(--color-accent)] bg-[var(--color-accent-soft)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-soft)]'
                  }`}
              >
                <Icon size={15} />
                {label}
              </Link>
            ))}
          </nav>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2 -mr-2 text-[var(--color-text-secondary)]"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="菜单"
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMobileOpen(false)}>
          <div className="sidebar-backdrop" />
          <nav
            className="absolute top-0 right-0 w-64 h-full bg-white shadow-xl flex flex-col pt-16 pb-6 px-4 animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 rounded-lg px-4 py-3 text-base font-medium transition-colors
                  ${isActive(path)
                    ? 'text-[var(--color-accent)] bg-[var(--color-accent-soft)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-soft)]'
                  }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </>
  );
}
