/**
 * 排行榜组件
 * 显示 Top N 猜测排名，带动画效果
 */
import type { LeaderboardEntry } from '../hooks/useWebSocket';

interface LeaderboardProps {
  entries: LeaderboardEntry[];
  totalParticipants: number;
}

export default function Leaderboard({ entries, totalParticipants }: LeaderboardProps) {
  if (entries.length === 0) {
    return (
      <div className="leaderboard-empty">
        <p>暂无猜测，等待观众参与...</p>
      </div>
    );
  }

  return (
    <div className="leaderboard">
      <div className="leaderboard-header">
        <h2>排行榜</h2>
        <span className="participant-count">{totalParticipants} 人参与</span>
      </div>
      <div className="leaderboard-list">
        {entries.map((entry, index) => (
          <div
            key={`${entry.userId}-${entry.timestamp}`}
            className={`leaderboard-item rank-${Math.min(index + 1, 4)}`}
          >
            <div className="rank-badge">
              {index === 0 && <span className="rank-gold">1</span>}
              {index === 1 && <span className="rank-silver">2</span>}
              {index === 2 && <span className="rank-bronze">3</span>}
              {index > 2 && <span className="rank-normal">{index + 1}</span>}
            </div>
            <div className="user-info">
              <span className="username">{entry.username}</span>
              <span className="guess-text">猜了: {entry.guessText}</span>
            </div>
            <div className="score">
              <span className="score-value">{(entry.score * 100).toFixed(1)}%</span>
              <span className="score-label">相似度</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
