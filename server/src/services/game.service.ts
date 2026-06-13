/**
 * 游戏轮次管理服务
 * 使用内存 + JSON 文件持久化（轻量方案，无需 SQLite）
 * 负责游戏状态机: 创建轮次 -> 开始 -> 接收猜测 -> 结束
 */
import fs from 'node:fs';
import path from 'node:path';
import { calculateSimilarity, isCorrect, getEmbedding, loadCachedEmbeddings } from './embedding.service.js';
import { addGuess, getLeaderboard, getGuessCount, incrementGuessCount } from './rank.service.js';
import type { LeaderboardEntry } from './rank.service.js';

// --- 类型 ---
export type RoundStatus = 'waiting' | 'active' | 'finished';

export interface Word {
  id: number;
  word: string;
  hint: string;
  category: string;
  difficulty: number;
  embedding?: number[];
}

export interface Round {
  id: number;
  wordId: number;
  word: string;
  hint: string;
  status: RoundStatus;
  startedAt: string | null;
  endedAt: string | null;
  duration: number;
}

export interface GuessRecord {
  roundId: number;
  userId: string;
  username: string;
  avatar: string;
  guessText: string;
  similarity: number;
  isCorrect: boolean;
  createdAt: string;
}

export interface GuessResult {
  similarity: number;
  isCorrect: boolean;
  rank: number;
  message: string;
}

// --- 数据存储 ---
const DATA_DIR = path.resolve(__dirname, '../../data');
const WORDS_FILE = path.join(DATA_DIR, 'words.json');
const GUESSES_FILE = path.join(DATA_DIR, 'guesses.json');

let words: Word[] = [];
let rounds: Round[] = [];
let guesses: GuessRecord[] = [];
let nextWordId = 1;
let nextRoundId = 1;

function ensureDataDir(): void {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

function loadWords(): void {
  ensureDataDir();
  if (fs.existsSync(WORDS_FILE)) {
    try {
      const data = JSON.parse(fs.readFileSync(WORDS_FILE, 'utf-8'));
      words = data.words || [];
      nextWordId = data.nextId || (words.length > 0 ? Math.max(...words.map(w => w.id)) + 1 : 1);
    } catch {
      words = [];
    }
  }
}

function saveWords(): void {
  ensureDataDir();
  fs.writeFileSync(WORDS_FILE, JSON.stringify({ words, nextId: nextWordId }, null, 2));
}

function loadGuesses(): void {
  ensureDataDir();
  if (fs.existsSync(GUESSES_FILE)) {
    try {
      guesses = JSON.parse(fs.readFileSync(GUESSES_FILE, 'utf-8'));
    } catch {
      guesses = [];
    }
  }
}

function saveGuesses(): void {
  ensureDataDir();
  fs.writeFileSync(GUESSES_FILE, JSON.stringify(guesses));
}

/**
 * 初始化: 加载词库 + embedding 缓存
 */
export function initGame(): void {
  loadWords();
  loadGuesses();

  // 加载已有 embedding 缓存
  const cachedRows = words
    .filter(w => w.embedding)
    .map(w => ({ word: w.word, embedding: JSON.stringify(w.embedding) }));
  loadCachedEmbeddings(cachedRows);

  console.log(`[Game] 初始化完成，词库 ${words.length} 个词`);
}

/**
 * 创建新一轮游戏
 */
export async function createRound(options?: {
  wordId?: number;
  category?: string;
  difficulty?: number;
  duration?: number;
}): Promise<Round> {
  const duration = options?.duration || parseInt(process.env.ROUND_DURATION || '60');

  let word: Word;

  if (options?.wordId) {
    word = words.find(w => w.id === options.wordId)!;
    if (!word) throw new Error(`词 ID ${options.wordId} 不存在`);
  } else {
    // 按条件筛选后随机
    let candidates = words;
    if (options?.category) candidates = candidates.filter(w => w.category === options.category);
    if (options?.difficulty) candidates = candidates.filter(w => w.difficulty === options.difficulty);
    if (candidates.length === 0) throw new Error('词库中没有符合条件的词');
    word = candidates[Math.floor(Math.random() * candidates.length)];
  }

  // 预计算 embedding（如果没有缓存）
  if (!word.embedding) {
    try {
      word.embedding = await getEmbedding(word.word);
      saveWords();
    } catch (err) {
      console.error(`[Game] 预计算 embedding 失败:`, err);
    }
  }

  const round: Round = {
    id: nextRoundId++,
    wordId: word.id,
    word: word.word,
    hint: word.hint,
    status: 'waiting',
    startedAt: null,
    endedAt: null,
    duration,
  };
  rounds.push(round);
  return { ...round };
}

/**
 * 开始一轮游戏
 */
export function startRound(roundId: number): Round {
  const round = rounds.find(r => r.id === roundId);
  if (!round) throw new Error('轮次不存在');
  round.status = 'active';
  round.startedAt = new Date().toISOString();
  return { ...round };
}

/**
 * 结束一轮游戏
 */
export function endRound(roundId: number): Round {
  const round = rounds.find(r => r.id === roundId);
  if (!round) throw new Error('轮次不存在');
  round.status = 'finished';
  round.endedAt = new Date().toISOString();
  return { ...round };
}

/**
 * 获取当前轮次信息
 */
export function getRound(roundId: number): Round | null {
  const round = rounds.find(r => r.id === roundId);
  return round ? { ...round } : null;
}

/**
 * 获取当前活跃的轮次
 */
export function getActiveRound(): Round | null {
  const round = [...rounds].reverse().find(r => r.status === 'active');
  return round ? { ...round } : null;
}

/**
 * 处理一次猜测
 */
export async function processGuess(
  roundId: number,
  userId: string,
  username: string,
  avatar: string,
  guessText: string
): Promise<GuessResult> {
  const maxGuesses = parseInt(process.env.MAX_GUESSES_PER_ROUND || '3');

  // 检查猜测次数
  const count = await getGuessCount(roundId, userId);
  if (count >= maxGuesses) {
    return {
      similarity: 0,
      isCorrect: false,
      rank: -1,
      message: `本轮已用完 ${maxGuesses} 次猜测机会`,
    };
  }

  // 获取当前轮次的答案
  const round = getRound(roundId);
  if (!round || round.status !== 'active') {
    return { similarity: 0, isCorrect: false, rank: -1, message: '当前没有进行中的游戏' };
  }

  // 找到答案词的 embedding
  const answerWord = words.find(w => w.id === round.wordId);
  const answerEmbedding = answerWord?.embedding;

  // 计算相似度
  const similarity = await calculateSimilarity(guessText, round.word, answerEmbedding);
  const correct = isCorrect(similarity);

  // 写入 Redis 排行榜
  await incrementGuessCount(roundId, userId);
  const entry: LeaderboardEntry = {
    rank: roundId, // addGuess 内部用 rank 字段作为 roundId
    userId,
    username,
    avatar,
    guessText,
    score: similarity,
    timestamp: Date.now(),
  };
  await addGuess(entry);

  // 记录到内存
  const record: GuessRecord = {
    roundId,
    userId,
    username,
    avatar,
    guessText,
    similarity,
    isCorrect: correct,
    createdAt: new Date().toISOString(),
  };
  guesses.push(record);
  saveGuesses();

  // 获取排名
  const leaderboard = await getLeaderboard(roundId);
  const userRank = leaderboard.findIndex(e => e.userId === userId) + 1;

  return {
    similarity: Math.round(similarity * 1000) / 1000,
    isCorrect: correct,
    rank: userRank > 0 ? userRank : leaderboard.length,
    message: correct
      ? `猜对了！相似度 ${(similarity * 100).toFixed(1)}%`
      : `相似度 ${(similarity * 100).toFixed(1)}%，继续加油！`,
  };
}

/**
 * 获取词库列表
 */
export function listWords(category?: string, difficulty?: number): Word[] {
  let result = words;
  if (category) result = result.filter(w => w.category === category);
  if (difficulty) result = result.filter(w => w.difficulty === difficulty);
  return result.map(({ embedding: _, ...rest }) => rest as Word);
}

/**
 * 添加新词到词库
 */
export function addWord(word: string, hint: string, category: string, difficulty: number): { lastInsertRowid: number } {
  const existing = words.find(w => w.word === word);
  if (existing) throw new Error(`词语 "${word}" 已存在`);
  const id = nextWordId++;
  words.push({ id, word, hint, category, difficulty });
  saveWords();
  return { lastInsertRowid: id };
}

/**
 * 删除词
 */
export function deleteWord(wordId: number): void {
  words = words.filter(w => w.id !== wordId);
  saveWords();
}
