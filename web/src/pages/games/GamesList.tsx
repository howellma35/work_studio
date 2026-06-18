import { Link } from 'react-router-dom';
import { Gamepad2, ArrowRight, Users } from 'lucide-react';

const games = [
  {
    path: '/games/word-guess',
    title: '猜词大挑战',
    desc: '多人实时猜词游戏，支持排行榜、计时器和 OBS 直播大屏模式',
    icon: Gamepad2,
    color: 'text-orange-600 bg-orange-50',
    features: ['实时对战', '排行榜', 'OBS 直播'],
  },
];

export default function GamesList() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:py-14">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-2">小游戏</h1>
        <p className="text-[var(--color-text-secondary)] text-sm">轻松有趣的互动游戏，支持多人实时对战</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {games.map(({ path, title, desc, icon: Icon, color, features }) => (
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
              开始游戏 <ArrowRight className="h-4 w-4 ml-1" />
            </div>
          </Link>
        ))}

        <div className="card p-5 flex flex-col items-center justify-center border-dashed min-h-[200px]">
          <Users className="h-8 w-8 text-[var(--color-text-muted)] mb-2 opacity-40" />
          <p className="text-sm text-[var(--color-text-muted)]">更多游戏即将上线</p>
        </div>
      </div>
    </div>
  );
}
