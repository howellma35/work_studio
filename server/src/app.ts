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
import logger from './utils/logger.js';

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
    logger.info('Redis 连接成功');

    // 初始化游戏（加载词库缓存）
    initGame();
    logger.info('游戏初始化完成');

    // 启动 HTTP + WS 服务
    server.listen(port, () => {
      logger.info({ port }, `服务已启动: http://localhost:${port}`);
      logger.info(`WebSocket: ws://localhost:${port}`);
      logger.info(`健康检查: http://localhost:${port}/api/health`);
    });
  } catch (err) {
    logger.error({ err }, '启动失败');
    process.exit(1);
  }
}

// 优雅退出
process.on('SIGINT', async () => {
  logger.info('正在关闭服务...');
  await disconnectRedis();
  server.close();
  process.exit(0);
});

start();
