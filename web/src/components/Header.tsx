import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Cpu, FileText, Wrench, Gamepad2, Sparkles } from 'lucide-react';
import { siteConfig } from '../config/site';

const navItems = [
  { path: '/blog', label: '技术博客', icon: FileText },
  { path: '/ai', label: 'AI前沿探索', icon: Cpu },
  { path: '/tools', label: '日常小工具', icon: Wrench },
  { path: '/games', label: '小游戏', icon: Gamepad2 },
];

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0a0a1a]/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <Sparkles className="h-6 w-6 text-[var(--color-accent-light)] group-hover:scale-110 transition-transform" />
          <span className="text-lg font-bold bg-gradient-to-r from-[var(--color-accent-light)] to-[var(--color-success)] bg-clip-text text-transparent">
            {siteConfig.site_title}
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map(({ path, label, icon: Icon }) => {
            const active = location.pathname.startsWith(path);
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all
                  ${active
                    ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent-light)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5'
                  }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-white/10 bg-[#0a0a1a]/95 backdrop-blur-xl animate-slide-in">
          <div className="flex flex-col p-4 gap-1">
            {navItems.map(({ path, label, icon: Icon }) => {
              const active = location.pathname.startsWith(path);
              return (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 rounded-lg px-4 py-3 text-base font-medium transition-all
                    ${active
                      ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent-light)]'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5'
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  {label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
