/**
 * 排行榜服务
 * 优先使用 Redis Sorted Set，Redis 不可用时自动回退到内存模式
 */
import Redis from 'ioredis';

// --- 类型 ---
export interface LeaderboardEntry {
  rank: number;
  userId: string;
  username: string;
  avatar: string;
  guessText: string;
  score: number;       // 相似度 0~1
  timestamp: number;   // 猜测时间戳，用于同分时排序
}

// --- Redis 连接 ---
let redis: Redis | null = null;
let useMemory = false;

// --- 内存回退存储 ---
// 排行榜: roundId -> [{ score, member }]
const memoryLeaderboards = new Map<number, Array<{ score: number; member: string }>>();
// 猜测计数: "roundId:userId" -> count
const memoryGuessCounts = new Map<string, number>();

export function getRedis(): Redis | null {
  return redis;
}

export async function connectRedis(): Promise<void> {
  const host = process.env.REDIS_HOST || '127.0.0.1';
  const port = parseInt(process.env.REDIS_PORT || '6379');
  const password = process.env.REDIS_PASSWORD || undefined;

  const r = new Redis({
    host,
    port,
    password: password || undefined,
    lazyConnect: true,
    connectTimeout: 3000,
    maxRetriesPerRequest: 1,
    retryStrategy: () => null, // 不重试，快速失败
  });

  try {
    await r.connect();
    await r.ping();
    redis = r;
    useMemory = false;
    console.log(`[Redis] 连接成功 (${host}:${port})`);
  } catch (err) {
    console.warn('[Redis] 连接失败，使用内存排行榜模式（数据不持久化）');
    console.warn('[Redis] 生产环境请安装 Redis 以获得更好的性能');
    r.disconnect();
    redis = null;
    useMemory = true;
  }
}

export async function disconnectRedis(): Promise<void> {
  if (redis) {
    await redis.quit();
    console.log('[Redis] 已断开');
    redis = null;
  }
}

// ========== 排行榜操作 ==========

/**
 * 提交一次猜测到排行榜
 */
export async function addGuess(entry: LeaderboardEntry): Promise<void> {
  const roundId = entry.rank; // rank 字段实际是 roundId
  const score = entry.score * 1000000 - (entry.timestamp % 1000000) / 1000000;
  const member = JSON.stringify({
    u: entry.userId,
    n: entry.username,
    a: entry.avatar,
    t: entry.guessText,
    s: entry.score,
    ts: entry.timestamp,
  });

  if (redis && !useMemory) {
    const key = `game:${roundId}:leaderboard`;
    await redis.zadd(key, score, member);
    await redis.expire(key, 7200);
  } else {
    // 内存模式
    if (!memoryLeaderboards.has(roundId)) {
      memoryLeaderboards.set(roundId, []);
    }
    const list = memoryLeaderboards.get(roundId)!;
    list.push({ score, member });
    // 按 score 降序排序
    list.sort((a, b) => b.score - a.score);
  }
}

/**
 * 获取排行榜 Top N
 */
export async function getLeaderboard(roundId: number, topN: number = 50): Promise<LeaderboardEntry[]> {
  let results: string[];

  if (redis && !useMemory) {
    const key = `game:${roundId}:leaderboard`;
    results = await redis.zrevrange(key, 0, topN - 1);
  } else {
    const list = memoryLeaderboards.get(roundId) || [];
    results = list.slice(0, topN).map(item => item.member);
  }

  return results.map((member, index) => {
    const data = JSON.parse(member) as {
      u: string; n: string; a: string; t: string; s: number; ts: number;
    };
    return {
      rank: index + 1,
      userId: data.u,
      username: data.n,
      avatar: data.a,
      guessText: data.t,
      score: data.s,
      timestamp: data.ts,
    };
  });
}

/**
 * 获取用户本轮猜测次数
 */
export async function getGuessCount(roundId: number, userId: string): Promise<number> {
  if (redis && !useMemory) {
    const key = `game:${roundId}:guess_count:${userId}`;
    const count = await redis.get(key);
    return count ? parseInt(count) : 0;
  } else {
    return memoryGuessCounts.get(`${roundId}:${userId}`) || 0;
  }
}

/**
 * 增加用户猜测次数
 */
export async function incrementGuessCount(roundId: number, userId: string): Promise<void> {
  if (redis && !useMemory) {
    const key = `game:${roundId}:guess_count:${userId}`;
    await redis.incr(key);
    await redis.expire(key, 7200);
  } else {
    const k = `${roundId}:${userId}`;
    memoryGuessCounts.set(k, (memoryGuessCounts.get(k) || 0) + 1);
  }
}

/**
 * 清除某轮的排行榜数据
 */
export async function clearLeaderboard(roundId: number): Promise<void> {
  if (redis && !useMemory) {
    await redis.del(`game:${roundId}:leaderboard`);
  } else {
    memoryLeaderboards.delete(roundId);
  }
}
