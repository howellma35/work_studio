/**
 * 游戏轮次 REST API 路由
 */
import { Router, Request, Response } from 'express';
import { createRound, startRound, endRound, getRound, getActiveRound } from '../services/game.service.js';
import { getLeaderboard } from '../services/rank.service.js';

const router = Router();

// 获取当前活跃轮次
router.get('/active', (_req: Request, res: Response) => {
  const round = getActiveRound();
  res.json({ success: true, data: round });
});

// 获取指定轮次信息
router.get('/rounds/:id', (req: Request, res: Response) => {
  const roundId = parseInt(req.params.id as string);
  if (isNaN(roundId)) {
    res.status(400).json({ success: false, message: '无效的轮次ID' });
    return;
  }
  const round = getRound(roundId);
  if (!round) {
    res.status(404).json({ success: false, message: '轮次不存在' });
    return;
  }
  res.json({ success: true, data: round });
});

// 获取指定轮次排行榜
router.get('/rounds/:id/leaderboard', async (req: Request, res: Response) => {
  const roundId = parseInt(req.params.id as string);
  if (isNaN(roundId)) {
    res.status(400).json({ success: false, message: '无效的轮次ID' });
    return;
  }

  try {
    const leaderboard = await getLeaderboard(roundId);
    res.json({ success: true, data: leaderboard });
  } catch (err) {
    res.status(500).json({ success: false, message: '获取排行榜失败' });
  }
});

// 创建新一轮（REST 方式，备用）
router.post('/rounds', async (req: Request, res: Response) => {
  try {
    const round = await createRound(req.body);
    res.json({ success: true, data: round });
  } catch (err) {
    const message = err instanceof Error ? err.message : '创建轮次失败';
    res.status(500).json({ success: false, message });
  }
});

// 开始轮次（REST 方式，备用）
router.post('/rounds/:id/start', (req: Request, res: Response) => {
  const roundId = parseInt(req.params.id as string);
  if (isNaN(roundId)) {
    res.status(400).json({ success: false, message: '无效的轮次ID' });
    return;
  }
  try {
    const round = startRound(roundId);
    res.json({ success: true, data: round });
  } catch (err) {
    const message = err instanceof Error ? err.message : '开始轮次失败';
    res.status(500).json({ success: false, message });
  }
});

// 结束轮次（REST 方式，备用）
router.post('/rounds/:id/end', (req: Request, res: Response) => {
  const roundId = parseInt(req.params.id as string);
  if (isNaN(roundId)) {
    res.status(400).json({ success: false, message: '无效的轮次ID' });
    return;
  }
  try {
    const round = endRound(roundId);
    res.json({ success: true, data: round });
  } catch (err) {
    const message = err instanceof Error ? err.message : '结束轮次失败';
    res.status(500).json({ success: false, message });
  }
});

export default router;
