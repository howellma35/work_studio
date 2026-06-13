/**
 * WebSocket 连接 Hook
 * 管理与后端的 Socket.IO 连接，处理消息收发
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

// --- 类型 ---
export interface LeaderboardEntry {
  rank: number;
  userId: string;
  username: string;
  avatar: string;
  guessText: string;
  score: number;
  timestamp: number;
}

export interface GameMessage {
  type: 'new_round' | 'leaderboard' | 'round_end' | 'guess_result' | 'error';
  data: Record<string, unknown>;
}

export interface GameState {
  status: 'idle' | 'active' | 'finished';
  roundId: number | null;
  hint: string;
  duration: number;
  remainingSeconds: number;
  leaderboard: LeaderboardEntry[];
  lastAnswer: string | null;
  totalParticipants: number;
}

const initialState: GameState = {
  status: 'idle',
  roundId: null,
  hint: '',
  duration: 60,
  remainingSeconds: 0,
  leaderboard: [],
  lastAnswer: null,
  totalParticipants: 0,
};

export function useWebSocket(serverUrl: string) {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState<GameState>(initialState);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 注册连接
  useEffect(() => {
    const socket = io(serverUrl, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      // 以主播身份注册
      socket.emit('register', {
        userId: 'host',
        username: '主播',
        avatar: '',
        role: 'host',
      });
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socket.on('message', (msg: GameMessage) => {
      handleMessage(msg);
    });

    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
      socket.disconnect();
    };
  }, [serverUrl]);

  // 处理消息
  const handleMessage = useCallback((msg: GameMessage) => {
    switch (msg.type) {
      case 'new_round': {
        const data = msg.data as { roundId: number; hint: string; duration: number; startedAt: string };
        const elapsed = Math.floor((Date.now() - new Date(data.startedAt).getTime()) / 1000);
        const remaining = Math.max(0, data.duration - elapsed);

        setGameState(prev => ({
          ...prev,
          status: 'active',
          roundId: data.roundId,
          hint: data.hint,
          duration: data.duration,
          remainingSeconds: remaining,
          leaderboard: [],
          lastAnswer: null,
          totalParticipants: 0,
        }));

        // 启动倒计时
        if (countdownRef.current) clearInterval(countdownRef.current);
        countdownRef.current = setInterval(() => {
          setGameState(prev => {
            if (prev.remainingSeconds <= 1) {
              if (countdownRef.current) clearInterval(countdownRef.current);
              return prev;
            }
            return { ...prev, remainingSeconds: prev.remainingSeconds - 1 };
          });
        }, 1000);
        break;
      }

      case 'leaderboard': {
        const data = msg.data as { entries: LeaderboardEntry[]; totalParticipants: number };
        setGameState(prev => ({
          ...prev,
          leaderboard: data.entries,
          totalParticipants: data.totalParticipants,
        }));
        break;
      }

      case 'round_end': {
        const data = msg.data as { answer: string; leaderboard: LeaderboardEntry[]; totalParticipants: number };
        if (countdownRef.current) clearInterval(countdownRef.current);
        setGameState(prev => ({
          ...prev,
          status: 'finished',
          lastAnswer: data.answer,
          leaderboard: data.leaderboard,
          totalParticipants: data.totalParticipants,
          remainingSeconds: 0,
        }));
        break;
      }
    }
  }, []);

  // 主播操作: 开始新一轮
  const startRound = useCallback((options?: {
    wordId?: number;
    category?: string;
    difficulty?: number;
    duration?: number;
  }) => {
    socketRef.current?.emit('message', {
      type: 'start_round',
      data: options || {},
    });
  }, []);

  // 主播操作: 结束当前轮
  const endRound = useCallback(() => {
    socketRef.current?.emit('message', {
      type: 'end_round',
      data: { roundId: gameState.roundId },
    });
  }, [gameState.roundId]);

  return {
    connected,
    gameState,
    startRound,
    endRound,
  };
}
