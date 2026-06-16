/**
 * 分级日志模块
 * 基于 pino，支持 INFO/WARN/ERROR 分级输出
 * 生产环境输出 JSON，开发环境 pretty print
 */
import pino from 'pino';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const logDir = process.env.LOG_DIR || join(process.cwd(), 'logs');
const logLevel = process.env.LOG_LEVEL || 'info';

// 确保日志目录存在
try {
  mkdirSync(logDir, { recursive: true });
} catch {
  // ignore
}

const isProduction = process.env.NODE_ENV === 'production';

const logger = pino({
  level: logLevel,
  timestamp: pino.stdTimeFunctions.isoTime,
  transport: isProduction
    ? {
        targets: [
          // 控制台输出
          { target: 'pino/file', options: { destination: 1 } },
          // 文件输出
          {
            target: 'pino/file',
            options: { destination: join(logDir, 'app.log') },
          },
        ],
      }
    : {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:yyyy-mm-dd HH:MM:ss',
        },
      },
});

export default logger;
