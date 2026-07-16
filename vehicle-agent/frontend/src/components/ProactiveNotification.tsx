/**
 * 主动推荐通知组件
 *
 * 监听 SSE 推送端点 /api/vehicle/proactive，
 * 接收主动推荐消息并在界面右上角弹出通知卡片。
 *
 * 推送消息格式:
 * {
 *   type: "proactive_recommendation",
 *   priority: "low" | "medium" | "high" | "critical",
 *   rule_id: string,
 *   message: string,
 *   agent: string,
 *   suggested_actions: string[],
 *   timestamp: string,
 * }
 */
import { useState, useEffect, useCallback } from "react";

interface ProactiveMessage {
  type: string;
  priority: string;
  rule_id: string;
  message: string;
  agent: string;
  suggested_actions: string[];
  timestamp: string;
}

// 优先级对应的样式和自动消失时间
const PRIORITY_CONFIG: Record<string, { bg: string; border: string; text: string; icon: string; autoDismiss: number }> = {
  low:      { bg: "bg-slate-800/80",     border: "border-slate-600/40", text: "text-slate-300",     icon: "💡", autoDismiss: 8000 },
  medium:   { bg: "bg-yellow-500/15",    border: "border-yellow-500/40", text: "text-yellow-300",   icon: "⚡", autoDismiss: 15000 },
  high:     { bg: "bg-orange-500/15",    border: "border-orange-500/40", text: "text-orange-300",   icon: "⚠️", autoDismiss: 30000 },
  critical: { bg: "bg-red-500/20",       border: "border-red-500/50",   text: "text-red-300",      icon: "🚨", autoDismiss: 0 },      // 不自动消失
};

export default function ProactiveNotification() {
  const [notifications, setNotifications] = useState<ProactiveMessage[]>([]);
  const [visible, setVisible] = useState<Set<string>>(new Set());

  // SSE 连接监听
  useEffect(() => {
    const eventSource = new EventSource("/api/vehicle/proactive");

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "proactive_recommendation") {
          setNotifications((prev) => [data, ...prev].slice(0, 5));  // 最多保留5条
          setVisible((prev) => new Set([...prev, data.rule_id]));

          // 自动消失（除非 critical）
          const config = PRIORITY_CONFIG[data.priority] || PRIORITY_CONFIG.low;
          if (config.autoDismiss > 0) {
            setTimeout(() => {
              setVisible((prev) => {
                const next = new Set(prev);
                next.delete(data.rule_id);
                return next;
              });
            }, config.autoDismiss);
          }
        }
        // heartbeat 忽略
      } catch {
        // 解析失败忽略
      }
    };

    eventSource.onerror = () => {
      // SSE 连接失败时静默重连（EventSource 自动重连）
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // 手动关闭通知
  const dismiss = useCallback((ruleId: string) => {
    setVisible((prev) => {
      const next = new Set(prev);
      next.delete(ruleId);
      return next;
    });
  }, []);

  // 通知为空时不渲染
  const visibleNotifications = notifications.filter((n) => visible.has(n.rule_id));
  if (visibleNotifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {visibleNotifications.map((notification) => {
        const config = PRIORITY_CONFIG[notification.priority] || PRIORITY_CONFIG.low;
        return (
          <div
            key={notification.rule_id}
            className={`rounded-xl border ${config.border} ${config.bg} backdrop-blur-md p-3 shadow-lg transition-all duration-300 animate-slide-in`}
          >
            {/* 顶部栏 */}
            <div className="flex items-center justify-between mb-2">
              <span className={`flex items-center gap-1.5 text-xs font-bold ${config.text}`}>
                <span>{config.icon}</span>
                <span>主动推荐 · {notification.priority.toUpperCase()}</span>
              </span>
              <button
                className="text-slate-500 hover:text-white text-xs transition-colors"
                onClick={() => dismiss(notification.rule_id)}
              >
                ✕
              </button>
            </div>

            {/* 推荐内容 */}
            <p className="text-sm text-white/90 leading-relaxed">
              {notification.message}
            </p>

            {/* 建议操作按钮 */}
            {notification.suggested_actions.length > 0 && (
              <div className="flex gap-1.5 mt-2">
                {notification.suggested_actions.map((action, i) => (
                  <span
                    key={i}
                    className="rounded-lg bg-slate-700/60 px-2 py-0.5 text-[10px] text-slate-300"
                  >
                    {action}
                  </span>
                ))}
              </div>
            )}

            {/* 时间戳 */}
            <p className="text-[10px] text-slate-500 mt-1.5">
              {new Date(notification.timestamp).toLocaleTimeString("zh-CN", { hour12: false })}
            </p>
          </div>
        );
      })}
    </div>
  );
}
