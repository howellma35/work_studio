/**
 * 猜词直播小游戏 - 后端入口
 * Express + Socket.IO + SQLite + Redis
 */
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import http from 'node:http';
import { Server as SocketServer } from 'socket.io';
import { connectRedis, disconnectRedis } from './services/rank.service.js';
import { initGame } from './services/game.service.js';
import { setupWebSocket } from './ws/handler.js';
import gameRouter from './routes/game.js';
import wordsRouter from './routes/words.js';

const app = express();
const server = http.createServer(app);
const port = parseInt(process.env.PORT || '3000');

// --- 中间件 ---
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'DELETE'],
}));
app.use(express.json());

// --- REST API ---
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api/game', gameRouter);
app.use('/api/words', wordsRouter);

// --- WebSocket ---
const io = new SocketServer(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
});

setupWebSocket(io);

// --- 启动 ---
async function start(): Promise<void> {
  try {
    // 连接 Redis
    await connectRedis();

    // 初始化游戏（加载词库缓存）
    initGame();

    // 启动 HTTP + WS 服务
    server.listen(port, () => {
      console.log(`[Server] 服务已启动: http://localhost:${port}`);
      console.log(`[Server] WebSocket: ws://localhost:${port}`);
      console.log(`[Server] 健康检查: http://localhost:${port}/api/health`);
    });
  } catch (err) {
    console.error('[Server] 启动失败:', err);
    process.exit(1);
  }
}

// 优雅退出
process.on('SIGINT', async () => {
  console.log('\n[Server] 正在关闭...');
  await disconnectRedis();
  server.close();
  process.exit(0);
});

start();
