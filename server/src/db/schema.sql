-- 词库表
CREATE TABLE IF NOT EXISTS words (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  word TEXT NOT NULL UNIQUE,           -- 目标词
  hint TEXT NOT NULL,                   -- 提示线索
  category TEXT NOT NULL DEFAULT 'other', -- 分类: fruit/animal/movie/idiom/tech/other
  difficulty INTEGER NOT NULL DEFAULT 1,  -- 难度 1=简单 2=中等 3=较难
  embedding TEXT,                        -- 预计算的 embedding 向量 (JSON 数组)
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 游戏轮次表
CREATE TABLE IF NOT EXISTS rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  word_id INTEGER NOT NULL,
  hint TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'waiting',  -- waiting / active / finished
  started_at DATETIME,
  ended_at DATETIME,
  duration INTEGER NOT NULL DEFAULT 60,    -- 秒
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (word_id) REFERENCES words(id)
);

-- 猜测记录表
CREATE TABLE IF NOT EXISTS guesses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  round_id INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  username TEXT NOT NULL,
  avatar TEXT DEFAULT '',
  guess_text TEXT NOT NULL,
  similarity REAL NOT NULL DEFAULT 0,      -- 相似度 0-1
  is_correct INTEGER NOT NULL DEFAULT 0,   -- 是否猜对
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (round_id) REFERENCES rounds(id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_words_category ON words(category);
CREATE INDEX IF NOT EXISTS idx_rounds_status ON rounds(status);
CREATE INDEX IF NOT EXISTS idx_guesses_round ON guesses(round_id);
CREATE INDEX IF NOT EXISTS idx_guesses_user_round ON guesses(user_id, round_id);
