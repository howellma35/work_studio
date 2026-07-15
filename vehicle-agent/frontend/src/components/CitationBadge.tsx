/**
 * CitationBadge — 知识来源标注徽章
 *
 * 解析 `[来源: xxx | 相关度: 0.xx]` 格式的标注，渲染为可点击的徽章。
 * 点击可展开查看完整来源信息。
 */
import { useState } from "react";

interface CitationBadgeProps {
  source: string;       // 文档名
  similarity?: number;  // 相关度分数
  excerpt?: string;     // 内容摘要
}

export default function CitationBadge({ source, similarity, excerpt }: CitationBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <span
      className="inline-flex items-center gap-1 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <span className="inline-flex items-center rounded-md bg-blue-500/20 border border-blue-400/30 px-1.5 py-0.5 text-xs text-blue-300 hover:bg-blue-500/30 transition-colors">
        📚 {source}
        {similarity !== undefined && (
          <span className="text-blue-400/70 ml-1">{similarity.toFixed(2)}</span>
        )}
      </span>
      {expanded && excerpt && (
        <span className="ml-1 text-xs text-slate-400 italic max-w-xs inline-block truncate">
          {excerpt}
        </span>
      )}
    </span>
  );
}

/**
 * parseCitations — 从文本中提取所有来源标注
 *
 * 输入: "1. [来源: vehicle_manual.md | 相关度: 0.85] 胎压标准..."
 * 输出: [{ source: "vehicle_manual.md", similarity: 0.85, fullMatch: "[来源: ...]" }]
 */
export function parseCitations(text: string): Array<{
  source: string;
  similarity: number;
  fullMatch: string;
}> {
  const regex = /\[来源:\s*(.*?)\s*\|\s*相关度:\s*([\d.]+)\s*\]/g;
  const citations = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
    citations.push({
      source: match[1].trim(),
      similarity: parseFloat(match[2]),
      fullMatch: match[0],
    });
  }
  return citations;
}
