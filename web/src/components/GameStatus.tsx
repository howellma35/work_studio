import { useState } from 'react';
import type { GameState } from '../hooks/useWebSocket';

interface GameStatusProps {
  gameState: GameState;
  connected: boolean;
  onStartRound: (options?: {
    wordId?: number;
    category?: string;
    difficulty?: number;
    duration?: number;
  }) => void;
  onEndRound: () => void;
}

const CATEGORIES = [
  { value: '', label: '随机' },
  { value: 'fruit', label: '水果' },
  { value: 'animal', label: '动物' },
  { value: 'movie', label: '电影' },
  { value: 'idiom', label: '成语' },
  { value: 'tech', label: '科技' },
];

const DIFFICULTIES = [
  { value: 0, label: '随机' },
  { value: 1, label: '简单' },
  { value: 2, label: '中等' },
  { value: 3, label: '较难' },
];

export default function GameStatus({
  gameState,
  connected,
  onStartRound,
  onEndRound,
}: GameStatusProps) {
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState(0);
  const [duration, setDuration] = useState(7200);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div>
      {gameState.status === 'idle' && (
        <div>
          <h2 className="text-lg font-bold mb-1">猜词直播间</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-4">点击下方按钮开始新一轮游戏</p>

          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <label className="w-10 text-xs text-[var(--color-text-secondary)] shrink-0">分类</label>
              <select className="select flex-1 text-sm" value={category} onChange={e => setCategory(e.target.value)}>
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <label className="w-10 text-xs text-[var(--color-text-secondary)] shrink-0">难度</label>
              <select className="select flex-1 text-sm" value={difficulty} onChange={e => setDifficulty(Number(e.target.value))}>
                {DIFFICULTIES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <label className="w-10 text-xs text-[var(--color-text-secondary)] shrink-0">时长</label>
              <select className="select flex-1 text-sm" value={duration} onChange={e => setDuration(Number(e.target.value))}>
                <option value={60}>1分钟</option>
                <option value={180}>3分钟</option>
                <option value={300}>5分钟</option>
                <option value={600}>10分钟</option>
                <option value={900}>15分钟</option>
                <option value={1800}>30分钟</option>
                <option value={3600}>1小时</option>
                <option value={7200}>2小时</option>
              </select>
            </div>
            <button
              className="btn-primary mt-2"
              onClick={() => onStartRound({ category: category || undefined, difficulty: difficulty || undefined, duration })}
              disabled={!connected}
            >
              开始新一轮
            </button>
          </div>
        </div>
      )}

      {gameState.status === 'active' && (
        <div>
          <div className="mb-3">
            <span className="text-xs text-[var(--color-text-muted)]">提示:</span>
            <p className="text-lg font-semibold mt-0.5">{gameState.hint}</p>
          </div>
          <div className={`game-countdown ${gameState.remainingSeconds <= 10 ? 'urgent' : ''}`}>
            {formatTime(gameState.remainingSeconds)}
          </div>
          <button className="btn-secondary w-full mt-3" onClick={onEndRound}>
            提前结束
          </button>
        </div>
      )}

      {gameState.status === 'finished' && (
        <div className="text-center">
          <p className="text-sm text-[var(--color-text-secondary)] mb-2">答案揭晓:</p>
          <p className="text-3xl font-extrabold text-[var(--color-gold)] mb-5">{gameState.lastAnswer}</p>
          <button
            className="btn-primary w-full"
            onClick={() => onStartRound({ category: category || undefined, difficulty: difficulty || undefined, duration })}
            disabled={!connected}
          >
            再来一轮
          </button>
        </div>
      )}
    </div>
  );
}
