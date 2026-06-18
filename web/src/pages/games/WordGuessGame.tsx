import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import GameStatus from '../../components/GameStatus';
import { siteConfig } from '../../config/site';

export default function WordGuessGame() {
  const { connected, gameState, startRound, endRound } = useWebSocket(siteConfig.serverUrl);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:py-10">
      <Link
        to="/games"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] mb-5 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> 返回游戏列表
      </Link>

      <div className="text-center mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text)]">猜词大挑战</h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-5">
        {/* Left: Game Status + Controls */}
        <div className="w-full lg:w-[360px] shrink-0">
          <div className="card p-5">
            <div className={`flex items-center gap-2 text-sm mb-4 ${connected ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-[var(--color-success)]' : 'bg-[var(--color-danger)]'}`} />
              {connected ? '已连接' : '未连接'}
            </div>
            <GameStatus
              gameState={gameState}
              connected={connected}
              onStartRound={startRound}
              onEndRound={endRound}
            />
          </div>
        </div>

        {/* Right: Leaderboard */}
        <div className="flex-1 min-h-0">
          {gameState.leaderboard.length === 0 ? (
            <div className="card h-full flex items-center justify-center text-[var(--color-text-muted)] p-8 text-sm">
              暂无猜测，等待观众参与...
            </div>
          ) : (
            <div className="card p-5 h-full flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold">排行榜</h2>
                <span className="text-sm text-[var(--color-text-secondary)]">{gameState.totalParticipants} 人参与</span>
              </div>
              <div className="flex-1 overflow-y-auto flex flex-col gap-1.5">
                {gameState.leaderboard.map((entry, index) => (
                  <div
                    key={`${entry.userId}-${entry.timestamp}`}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all animate-fade-in
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
          )}
        </div>
      </div>
    </div>
  );
}
