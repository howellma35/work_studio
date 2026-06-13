/**
 * 词库管理 REST API 路由
 */
import { Router, Request, Response } from 'express';
import { listWords, addWord, deleteWord } from '../services/game.service.js';

const router = Router();

// 获取词库列表
router.get('/', (req: Request, res: Response) => {
  const category = req.query.category as string | undefined;
  const difficulty = req.query.difficulty ? parseInt(req.query.difficulty as string) : undefined;

  const words = listWords(category, difficulty);
  res.json({ success: true, data: words });
});

// 添加新词
router.post('/', (req: Request, res: Response) => {
  const { word, hint, category, difficulty } = req.body;

  if (!word || !hint) {
    res.status(400).json({ success: false, message: '词语和提示不能为空' });
    return;
  }

  try {
    const result = addWord(word, hint, category || 'other', difficulty || 1);
    res.json({ success: true, data: { id: result.lastInsertRowid } });
  } catch (err) {
    const message = err instanceof Error ? err.message : '添加词语失败';
    res.status(500).json({ success: false, message });
  }
});

// 删除词
router.delete('/:id', (req: Request, res: Response) => {
  const wordId = parseInt(req.params.id as string);
  if (isNaN(wordId)) {
    res.status(400).json({ success: false, message: '无效的词语ID' });
    return;
  }

  try {
    deleteWord(wordId);
    res.json({ success: true, message: '删除成功' });
  } catch (err) {
    res.status(500).json({ success: false, message: '删除词语失败' });
  }
});

export default router;
