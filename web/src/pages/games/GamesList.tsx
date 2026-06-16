import { Link } from 'react-router-dom';
import { Gamepad2, ArrowRight, Users } from 'lucide-react';

const games = [
  {
    path: '/games/word-guess',
    title: '猜词大挑战',
    desc: '多人实时猜词游戏，支持排行榜、计时器和 OBS 直播大屏模式',
    icon: Gamepad2,
    gradient: 'from-orange-500 to-amber-400',
    features: ['实时对战', '排行榜', 'OBS 直播'],
  },
];

export default function GamesList() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 bg-gradient-to-r from-orange-400 to-amber-300 bg-clip-text text-transparent">
          小游戏
        </h1>
        <p className="text-[var(--color-text-secondary)]">轻松有趣的互动游戏，支持多人实时对战</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {games.map(({ path, title, desc, icon: Icon, gradient, features }) => (
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
              开始游戏 <ArrowRight className="h-4 w-4 ml-1" />
            </div>
          </Link>
        ))}

        {/* 预留更多游戏位 */}
        <div className="glass-card p-6 flex flex-col items-center justify-center border border-dashed border-white/10 min-h-[200px]">
          <Users className="h-10 w-10 text-[var(--color-text-secondary)] mb-3 opacity-30" />
          <p className="text-sm text-[var(--color-text-secondary)] opacity-50">更多游戏即将上线</p>
        </div>
      </div>
    </div>
  );
}
