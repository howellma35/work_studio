/**
 * SessionPanel — 会话管理侧边栏
 *
 * 支持创建新会话、切换会话、查看会话列表。
 * 会话之间共享 RAGFlow 记忆。
 */
import { useState } from "react";

interface Session {
  session_id: string;
  thread_id: string;
  created_at: string;
}

interface SessionPanelProps {
  currentSessionId: string;
  onNewSession: () => void;
  onSwitchSession: (sessionId: string) => void;
  sessions: Session[];
}

export default function SessionPanel({
  currentSessionId,
  onNewSession,
  onSwitchSession,
  sessions,
}: SessionPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-2 bg-slate-900/60 border-r border-slate-700/40">
        <button
          onClick={() => setCollapsed(false)}
          className="flex items-center justify-center w-8 h-8 rounded-lg border border-slate-700/40 bg-slate-800/60 text-slate-300 hover:text-white hover:bg-slate-700/70 transition-all"
          title="展开会话面板"
        >
          💬
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-48 shrink-0 bg-slate-900/60 border-r border-slate-700/40 overflow-y-auto">
      {/* 标题 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700/40">
        <span className="text-sm font-medium text-slate-200">会话</span>
        <button
          onClick={() => setCollapsed(true)}
          className="text-slate-400 hover:text-white transition-colors"
          title="折叠"
        >
          ◀
        </button>
      </div>

      {/* 新建会话按钮 */}
      <button
        onClick={onNewSession}
        className="flex items-center gap-2 mx-2 my-2 px-3 py-2 rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 transition-all text-sm"
      >
        ✨ 新会话
      </button>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2">
        {sessions.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            暂无会话记录
          </div>
        ) : (
          sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => onSwitchSession(s.session_id)}
              className={`w-full text-left px-3 py-2 rounded-lg mb-1 text-xs transition-all ${
                s.session_id === currentSessionId
                  ? "bg-blue-500/20 border border-blue-400/30 text-blue-200"
                  : "bg-slate-800/40 border border-slate-700/30 text-slate-400 hover:bg-slate-700/50 hover:text-slate-200"
              }`}
            >
              <div className="font-medium truncate">
                {s.session_id === currentSessionId ? "当前会话" : `会话 ${s.session_id.slice(0, 6)}`}
              </div>
              <div className="text-slate-500 mt-0.5">
                {s.created_at || "刚刚"}
              </div>
            </button>
          ))
        )}
      </div>

      {/* 底部：记忆状态 */}
      <div className="px-3 py-2 border-t border-slate-700/40 text-xs text-slate-500">
        🧠 记忆跨会话共享
      </div>
    </div>
  );
}
