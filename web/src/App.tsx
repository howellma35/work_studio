/**
 * 猜词直播排行榜 - 主播端 H5 大屏
 * 用于 OBS 浏览器源捕获
 */
import { useWebSocket } from './hooks/useWebSocket';
import Leaderboard from './components/Leaderboard';
import GameStatus from './components/GameStatus';

// 后端地址，开发时默认 localhost:3000
const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:3000';

export default function App() {
  const { connected, gameState, startRound, endRound } = useWebSocket(SERVER_URL);

  return (
    <div className="app">
      <div className="app-header">
        <h1 className="app-title">猜词大挑战</h1>
      </div>

      <div className="app-content">
        {/* 左侧: 游戏状态 + 控制面板 */}
        <div className="app-left">
          <GameStatus
            gameState={gameState}
            connected={connected}
            onStartRound={startRound}
            onEndRound={endRound}
          />
        </div>

        {/* 右侧: 排行榜 */}
        <div className="app-right">
          <Leaderboard
            entries={gameState.leaderboard}
            totalParticipants={gameState.totalParticipants}
          />
        </div>
      </div>
    </div>
  );
}
