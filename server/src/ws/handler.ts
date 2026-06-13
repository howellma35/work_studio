/**
 * WebSocket 消息处理器
 * 管理客户端连接、消息路由、定时广播排行榜
 */
import { Server as SocketServer, Socket } from 'socket.io';
import { getActiveRound, processGuess, getRound, startRound, endRound, createRound } from '../services/game.service.js';
import { getLeaderboard, getGuessCount } from '../services/rank.service.js';

// --- 类型 ---
interface ClientMessage {
  type: string;
  data?: Record<string, unknown>;
}

interface ConnectedClient {
  socket: Socket;
  userId: string;
  username: string;
  avatar: string;
  role: 'viewer' | 'host';
}

// --- 状态 ---
const clients = new Map<string, ConnectedClient>();
let leaderboardTimer: ReturnType<typeof setInterval> | null = null;
let roundTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * 初始化 WebSocket 服务
 */
export function setupWebSocket(io: SocketServer): void {
  io.on('connection', (socket: Socket) => {
    console.log(`[WS] 新连接: ${socket.id}`);

    // 客户端注册（带用户信息）
    socket.on('register', (data: { userId: string; username: string; avatar: string; role: string }) => {
      clients.set(socket.id, {
        socket,
        userId: data.userId,
        username: data.username,
        avatar: data.avatar || '',
        role: (data.role as 'viewer' | 'host') || 'viewer',
      });
      console.log(`[WS] 用户注册: ${data.username} (${data.role})`);

      // 如果有活跃轮次，发送当前状态
      const activeRound = getActiveRound();
      if (activeRound) {
        socket.emit('message', {
          type: 'new_round',
          data: {
            roundId: activeRound.id,
            hint: activeRound.hint,
            duration: activeRound.duration,
            startedAt: activeRound.startedAt,
          },
        });
      }
    });

    // 处理消息
    socket.on('message', async (msg: ClientMessage) => {
      const client = clients.get(socket.id);
      if (!client) return;

      try {
        switch (msg.type) {
          case 'guess':
            await handleGuess(io, client, msg.data || {});
            break;
          case 'start_round':
            await handleStartRound(io, client, msg.data || {});
            break;
          case 'end_round':
            await handleEndRound(io, client, msg.data || {});
            break;
          default:
            socket.emit('message', { type: 'error', data: { message: `未知消息类型: ${msg.type}` } });
        }
      } catch (err) {
        console.error('[WS] 处理消息错误:', err);
        socket.emit('message', { type: 'error', data: { message: '服务器内部错误' } });
      }
    });

    // 断开连接
    socket.on('disconnect', () => {
      const client = clients.get(socket.id);
      if (client) {
        console.log(`[WS] 断开: ${client.username}`);
        clients.delete(socket.id);
      }
    });
  });
}

/**
 * 处理猜测消息
 */
async function handleGuess(io: SocketServer, client: ConnectedClient, data: Record<string, unknown>): Promise<void> {
  const roundId = data.roundId as number;
  const text = (data.text as string || '').trim();

  if (!text) {
    client.socket.emit('message', { type: 'error', data: { message: '请输入猜测内容' } });
    return;
  }

  if (text.length > 50) {
    client.socket.emit('message', { type: 'error', data: { message: '输入过长，最多50字' } });
    return;
  }

  const round = getRound(roundId);
  if (!round || round.status !== 'active') {
    client.socket.emit('message', { type: 'error', data: { message: '当前没有进行中的游戏' } });
    return;
  }

  const result = await processGuess(
    roundId,
    client.userId,
    client.username,
    client.avatar,
    text
  );

  // 发送猜测结果给该用户
  client.socket.emit('message', {
    type: 'guess_result',
    data: {
      roundId,
      text,
      similarity: result.similarity,
      isCorrect: result.isCorrect,
      rank: result.rank,
      message: result.message,
    },
  });

  // 广播排行榜更新给所有人
  await broadcastLeaderboard(io, roundId);
}

/**
 * 主播: 开始新一轮
 */
async function handleStartRound(io: SocketServer, client: ConnectedClient, data: Record<string, unknown>): Promise<void> {
  if (client.role !== 'host') {
    client.socket.emit('message', { type: 'error', data: { message: '只有主播可以开始游戏' } });
    return;
  }

  // 检查是否有活跃轮次
  const active = getActiveRound();
  if (active) {
    client.socket.emit('message', { type: 'error', data: { message: '当前已有进行中的游戏，请先结束' } });
    return;
  }

  const round = await createRound({
    wordId: data.wordId as number | undefined,
    category: data.category as string | undefined,
    difficulty: data.difficulty as number | undefined,
    duration: data.duration as number | undefined,
  });

  const startedRound = startRound(round.id);

  // 广播新一轮开始
  broadcast(io, {
    type: 'new_round',
    data: {
      roundId: startedRound.id,
      hint: startedRound.hint,
      duration: startedRound.duration,
      startedAt: startedRound.startedAt,
    },
  });

  // 启动排行榜定时广播（每3秒）
  startLeaderboardBroadcast(io, startedRound.id);

  // 启动倒计时
  roundTimer = setTimeout(async () => {
    await handleAutoEndRound(io, startedRound.id);
  }, startedRound.duration * 1000);

  console.log(`[Game] 轮次 ${startedRound.id} 开始，答案: ${startedRound.word}`);
}

/**
 * 主播: 手动结束轮次
 */
async function handleEndRound(io: SocketServer, client: ConnectedClient, data: Record<string, unknown>): Promise<void> {
  if (client.role !== 'host') {
    client.socket.emit('message', { type: 'error', data: { message: '只有主播可以结束游戏' } });
    return;
  }

  const roundId = data.roundId as number;
  await finishRound(io, roundId);
}

/**
 * 自动结束轮次（倒计时到）
 */
async function handleAutoEndRound(io: SocketServer, roundId: number): Promise<void> {
  const round = getRound(roundId);
  if (!round || round.status !== 'active') return;

  await finishRound(io, roundId);
}

/**
 * 结束轮次并广播结果
 */
async function finishRound(io: SocketServer, roundId: number): Promise<void> {
  // 清除定时器
  stopLeaderboardBroadcast();
  if (roundTimer) {
    clearTimeout(roundTimer);
    roundTimer = null;
  }

  const endedRound = endRound(roundId);
  const leaderboard = await getLeaderboard(roundId);

  // 广播轮次结束
  broadcast(io, {
    type: 'round_end',
    data: {
      roundId: endedRound.id,
      answer: endedRound.word,
      hint: endedRound.hint,
      leaderboard: leaderboard.slice(0, 10), // Top 10
      totalParticipants: leaderboard.length,
    },
  });

  console.log(`[Game] 轮次 ${roundId} 结束，答案: ${endedRound.word}，参与人数: ${leaderboard.length}`);
}

/**
 * 广播排行榜
 */
async function broadcastLeaderboard(io: SocketServer, roundId: number): Promise<void> {
  const leaderboard = await getLeaderboard(roundId);
  broadcast(io, {
    type: 'leaderboard',
    data: {
      roundId,
      entries: leaderboard.slice(0, 50),
      totalParticipants: leaderboard.length,
    },
  });
}

/**
 * 启动排行榜定时广播
 */
function startLeaderboardBroadcast(io: SocketServer, roundId: number): void {
  stopLeaderboardBroadcast();
  leaderboardTimer = setInterval(async () => {
    await broadcastLeaderboard(io, roundId);
  }, 3000); // 每3秒
}

/**
 * 停止排行榜定时广播
 */
function stopLeaderboardBroadcast(): void {
  if (leaderboardTimer) {
    clearInterval(leaderboardTimer);
    leaderboardTimer = null;
  }
}

/**
 * 广播消息给所有已注册客户端
 */
function broadcast(io: SocketServer, message: ClientMessage): void {
  io.emit('message', message);
}
