/**
 * 游戏状态组件
 * 显示当前游戏状态、提示、倒计时、主播控制面板
 */
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
  const [duration, setDuration] = useState(60);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="game-status">
      {/* 连接状态 */}
      <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
        <span className="dot" />
        {connected ? '已连接' : '未连接'}
      </div>

      {/* 游戏状态 */}
      {gameState.status === 'idle' && (
        <div className="idle-panel">
          <h1>猜词直播间</h1>
          <p>点击下方按钮开始新一轮游戏</p>

          <div className="control-panel">
            <div className="control-row">
              <label>分类:</label>
              <select value={category} onChange={e => setCategory(e.target.value)}>
                {CATEGORIES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div className="control-row">
              <label>难度:</label>
              <select value={difficulty} onChange={e => setDifficulty(Number(e.target.value))}>
                {DIFFICULTIES.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div className="control-row">
              <label>时长:</label>
              <select value={duration} onChange={e => setDuration(Number(e.target.value))}>
                <option value={30}>30秒</option>
                <option value={60}>60秒</option>
                <option value={90}>90秒</option>
                <option value={120}>120秒</option>
              </select>
            </div>
            <button
              className="btn-start"
              onClick={() => onStartRound({
                category: category || undefined,
                difficulty: difficulty || undefined,
                duration,
              })}
              disabled={!connected}
            >
              开始新一轮
            </button>
          </div>
        </div>
      )}

      {gameState.status === 'active' && (
        <div className="active-panel">
          <div className="hint-display">
            <span className="hint-label">提示:</span>
            <span className="hint-text">{gameState.hint}</span>
          </div>
          <div className={`countdown ${gameState.remainingSeconds <= 10 ? 'urgent' : ''}`}>
            {formatTime(gameState.remainingSeconds)}
          </div>
          <button className="btn-end" onClick={onEndRound}>
            提前结束
          </button>
        </div>
      )}

      {gameState.status === 'finished' && (
        <div className="finished-panel">
          <div className="answer-reveal">
            <span className="answer-label">答案揭晓:</span>
            <span className="answer-text">{gameState.lastAnswer}</span>
          </div>
          <button
            className="btn-start"
            onClick={() => onStartRound({
              category: category || undefined,
              difficulty: difficulty || undefined,
              duration,
            })}
            disabled={!connected}
          >
            再来一轮
          </button>
        </div>
      )}
    </div>
  );
}
