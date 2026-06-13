/**
 * Embedding 语义匹配服务
 * 使用硅基流动 SiliconFlow API 获取文本向量，计算余弦相似度
 */

// --- 类型定义 ---
interface EmbeddingResponse {
  data: Array<{ embedding: number[] }>;
  model: string;
  usage: { prompt_tokens: number; total_tokens: number };
}

// --- 缓存 ---
const embeddingCache = new Map<string, number[]>();

/**
 * 获取文本的 Embedding 向量
 * 优先从缓存读取，否则调用 API
 */
export async function getEmbedding(text: string): Promise<number[]> {
  const cached = embeddingCache.get(text);
  if (cached) return cached;

  const apiKey = process.env.EMBEDDING_API_KEY || '';
  const apiUrl = process.env.EMBEDDING_API_URL || 'https://api.siliconflow.cn/v1/embeddings';
  const model = process.env.EMBEDDING_MODEL || 'BAAI/bge-m3';

  const resp = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input: [text],
    }),
  });

  if (!resp.ok) {
    const errBody = await resp.text();
    console.error(`[Embedding] API error ${resp.status}: ${errBody}`);
    throw new Error(`Embedding API 调用失败: ${resp.status}`);
  }

  const data = (await resp.json()) as EmbeddingResponse;
  const embedding = data.data[0].embedding;

  // 缓存结果
  embeddingCache.set(text, embedding);
  return embedding;
}

/**
 * 计算两个向量的余弦相似度
 * 返回值范围 [-1, 1]，越接近 1 越相似
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error(`向量维度不匹配: ${a.length} vs ${b.length}`);
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const magnitude = Math.sqrt(normA) * Math.sqrt(normB);
  if (magnitude === 0) return 0;

  return dotProduct / magnitude;
}

/**
 * 简单的字符串相似度（当没有 Embedding API Key 时使用）
 * 基于编辑距离的归一化相似度
 */
function simpleStringSimilarity(a: string, b: string): number {
  const la = a.toLowerCase().trim();
  const lb = b.toLowerCase().trim();
  if (la === lb) return 1;
  if (la.length === 0 || lb.length === 0) return 0;

  // 简单编辑距离
  const matrix: number[][] = [];
  for (let i = 0; i <= la.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= lb.length; j++) {
    matrix[0][j] = j;
  }
  for (let i = 1; i <= la.length; i++) {
    for (let j = 1; j <= lb.length; j++) {
      const cost = la[i - 1] === lb[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }
  const maxLen = Math.max(la.length, lb.length);
  return 1 - matrix[la.length][lb.length] / maxLen;
}

/**
 * 计算猜测文本与答案的语义相似度
 * 当 API Key 未配置时，回退到简单字符串相似度
 */
export async function calculateSimilarity(
  guessText: string,
  answerText: string,
  answerEmbedding?: number[]
): Promise<number> {
  const apiKey = process.env.EMBEDDING_API_KEY || '';

  // 没有 API Key 时使用简单字符串相似度
  if (!apiKey || apiKey === 'your_dashscope_api_key_here') {
    return simpleStringSimilarity(guessText, answerText);
  }

  // 获取答案向量（优先用预计算的）
  const ansVec = answerEmbedding || await getEmbedding(answerText);
  // 获取猜测向量
  const guessVec = await getEmbedding(guessText);

  return cosineSimilarity(guessVec, ansVec);
}

/**
 * 判断是否猜对（相似度超过阈值）
 */
export function isCorrect(similarity: number): boolean {
  const threshold = parseFloat(process.env.SIMILARITY_THRESHOLD || '0.75');
  return similarity >= threshold;
}

/**
 * 预计算词库中所有词的 embedding 并缓存
 */
export async function precomputeEmbeddings(words: Array<{ word: string }>): Promise<void> {
  console.log(`[Embedding] 开始预计算 ${words.length} 个词的 embedding...`);

  for (const { word } of words) {
    try {
      await getEmbedding(word);
      // 简单限速：每次间隔 100ms
      await new Promise(resolve => setTimeout(resolve, 100));
    } catch (err) {
      console.error(`[Embedding] 预计算 "${word}" 失败:`, err);
    }
  }

  console.log(`[Embedding] 预计算完成，缓存中已有 ${embeddingCache.size} 个向量`);
}

/**
 * 从数据库加载已有 embedding 到缓存
 */
export function loadCachedEmbeddings(
  rows: Array<{ word: string; embedding: string | null }>
): void {
  for (const row of rows) {
    if (row.embedding) {
      try {
        embeddingCache.set(row.word, JSON.parse(row.embedding));
      } catch {
        // 忽略解析失败的记录
      }
    }
  }
  console.log(`[Embedding] 从数据库加载了 ${embeddingCache.size} 个缓存向量`);
}

/**
 * 获取缓存中的 embedding（用于保存到数据库）
 */
export function getCachedEmbedding(text: string): number[] | undefined {
  return embeddingCache.get(text);
}
