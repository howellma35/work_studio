import type { LeaderboardEntry } from '../hooks/useWebSocket';

interface LeaderboardProps {
  entries: LeaderboardEntry[];
  totalParticipants: number;
}

export default function Leaderboard({ entries, totalParticipants }: LeaderboardProps) {
  if (entries.length === 0) {
    return (
      <div className="card p-8 text-center text-[var(--color-text-muted)] text-sm">
        暂无猜测，等待观众参与...
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">排行榜</h2>
        <span className="text-sm text-[var(--color-text-secondary)]">{totalParticipants} 人参与</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {entries.map((entry, index) => (
          <div
            key={`${entry.userId}-${entry.timestamp}`}
            className={`flex items-center gap-3 p-3 rounded-lg
              ${index === 0 ? 'bg-yellow-50 border border-yellow-200' :
                index === 1 ? 'bg-gray-50 border border-gray-200' :
                index === 2 ? 'bg-orange-50 border border-orange-200' :
                'bg-[var(--color-bg-soft)]'}
            `}
          >
            <div className="w-7 h-7 shrink-0 flex items-center justify-center rounded-full font-bold text-xs">
              {index === 0 && <span className="rank-gold w-full h-full flex items-center justify-center rounded-full">1</span>}
              {index === 1 && <span className="rank-silver w-full h-full flex items-center justify-center rounded-full">2</span>}
              {index === 2 && <span className="rank-bronze w-full h-full flex items-center justify-center rounded-full">3</span>}
              {index > 2 && <span className="text-[var(--color-text-secondary)]">{index + 1}</span>}
            </div>
            <div className="flex-1 min-w-0">
              <span className="block font-medium text-sm truncate">{entry.username}</span>
              <span className="block text-xs text-[var(--color-text-muted)] truncate">猜了: {entry.guessText}</span>
            </div>
            <div className="text-right shrink-0">
              <span className="block font-bold text-sm text-[var(--color-success)]">{(entry.score * 100).toFixed(1)}%</span>
              <span className="text-xs text-[var(--color-text-muted)]">相似度</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
