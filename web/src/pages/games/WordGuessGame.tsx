import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import GameStatus from '../../components/GameStatus';
import { siteConfig } from '../../config/site';

export default function WordGuessGame() {
  const { connected, gameState, startRound, endRound } = useWebSocket(siteConfig.serverUrl);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Link
        to="/games"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> 返回游戏列表
      </Link>

      {/* Title */}
      <div className="text-center mb-6">
        <h1 className="text-3xl sm:text-4xl font-extrabold bg-gradient-to-r from-orange-400 to-amber-300 bg-clip-text text-transparent">
          猜词大挑战
        </h1>
      </div>

      {/* Game Content */}
      <div className="flex flex-col lg:flex-row gap-5">
        {/* Left: Game Status + Controls */}
        <div className="w-full lg:w-[380px] flex-shrink-0">
          <div className="glass-card p-6">
            {/* Connection Status */}
            <div className={`flex items-center gap-2 text-sm mb-4 ${connected ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
              <span className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-[var(--color-success)] shadow-[0_0_8px_var(--color-success)] animate-pulse' : 'bg-[var(--color-danger)]'}`} />
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
            <div className="glass-card h-full flex items-center justify-center text-[var(--color-text-secondary)] p-8">
              暂无猜测，等待观众参与...
            </div>
          ) : (
            <div className="glass-card p-5 h-full flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">排行榜</h2>
                <span className="text-sm text-[var(--color-text-secondary)]">{gameState.totalParticipants} 人参与</span>
              </div>
              <div className="flex-1 overflow-y-auto flex flex-col gap-2">
                {gameState.leaderboard.map((entry, index) => (
                  <div
                    key={`${entry.userId}-${entry.timestamp}`}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all animate-slide-in
                      ${index === 0 ? 'bg-gradient-to-r from-yellow-500/15 to-yellow-500/5 border border-yellow-500/30' :
                        index === 1 ? 'bg-gradient-to-r from-gray-400/10 to-gray-400/5 border border-gray-400/20' :
                        index === 2 ? 'bg-gradient-to-r from-orange-700/10 to-orange-700/5 border border-orange-700/20' :
                        'bg-white/5'}
                    `}
                  >
                    <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full font-bold text-sm">
                      {index === 0 && <span className="rank-gold w-full h-full flex items-center justify-center rounded-full">1</span>}
                      {index === 1 && <span className="rank-silver w-full h-full flex items-center justify-center rounded-full">2</span>}
                      {index === 2 && <span className="rank-bronze w-full h-full flex items-center justify-center rounded-full">3</span>}
                      {index > 2 && <span className="text-[var(--color-text-secondary)]">{index + 1}</span>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="block font-semibold text-sm truncate">{entry.username}</span>
                      <span className="block text-xs text-[var(--color-text-secondary)] truncate">猜了: {entry.guessText}</span>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <span className="block font-bold text-[var(--color-success)]">{(entry.score * 100).toFixed(1)}%</span>
                      <span className="text-xs text-[var(--color-text-secondary)]">相似度</span>
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
