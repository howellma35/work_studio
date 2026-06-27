export interface AgentToolCardProps {
  icon: string;
  title: string;
  subtitle?: string;
  /** 是否已完成（影响左侧状态点颜色 / 是否转圈） */
  done?: boolean;
}

/**
 * AgentToolCard — 聊天流内的紧凑工具/子Agent调用卡片
 *
 * 用于把后端子Agent 调用、地图更新等以一行小卡片呈现，
 * 既隐藏了大段原始文本，又把每次调用作为历史记录保留在对话中。
 */
export default function AgentToolCard({
  icon,
  title,
  subtitle,
  done = false,
}: AgentToolCardProps) {
  return (
    <div className="my-1.5 flex items-center gap-2.5 rounded-xl border border-slate-600/30 bg-slate-800/50 backdrop-blur-sm px-3 py-2 text-sm">
      <span className="text-base">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-slate-200">{title}</p>
        {subtitle ? (
          <p className="truncate text-xs text-slate-400">{subtitle}</p>
        ) : null}
      </div>
      {done ? (
        <span className="shrink-0 text-xs text-emerald-400">✓</span>
      ) : (
        <span className="shrink-0 animate-spin text-xs text-sky-400">⏳</span>
      )}
    </div>
  );
}
