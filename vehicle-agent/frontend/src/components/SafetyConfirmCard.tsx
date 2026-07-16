/**
 * 安全操作确认卡片
 *
 * 当车辆操作被评估为 HIGH 风险等级时，supervisor 会调用
 * confirm_dangerous_operation 前端工具，此卡片渲染二次确认 UI。
 *
 * 用户点击"确认执行"或"取消"后，结果返回给 LLM 继续执行或取消。
 */
interface SafetyConfirmCardProps {
  operation: string;
  riskLevel: string;
  safetyNotice: string;
  onSelect: (approved: boolean) => void;
}

// 风险等级对应的样式
const RISK_DISPLAY: Record<string, { icon: string; label: string; color: string; bgColor: string }> = {
  medium: {
    icon: "⚡",
    label: "中等风险",
    color: "text-yellow-300",
    bgColor: "bg-yellow-500/15",
  },
  high: {
    icon: "🔒",
    label: "高风险",
    color: "text-orange-300",
    bgColor: "bg-orange-500/20",
  },
  critical: {
    icon: "⛔",
    label: "极高风险",
    color: "text-red-300",
    bgColor: "bg-red-500/25",
  },
};

export default function SafetyConfirmCard({
  operation,
  riskLevel,
  safetyNotice,
  onSelect,
}: SafetyConfirmCardProps) {
  const display = RISK_DISPLAY[riskLevel] || RISK_DISPLAY.high;

  return (
    <div className={`my-2 rounded-xl border border-slate-600/30 ${display.bgColor} backdrop-blur-sm p-4`}>
      {/* 风险指示器 */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{display.icon}</span>
        <span className={`text-sm font-bold ${display.color}`}>
          {display.label} · 安全确认
        </span>
      </div>

      {/* 操作描述 */}
      <div className="mb-3">
        <p className="text-xs text-slate-400 mb-1">即将执行的操作：</p>
        <p className="text-sm text-white font-medium">{operation}</p>
      </div>

      {/* 安全提示 */}
      <div className="mb-4 rounded-lg bg-slate-800/50 px-3 py-2">
        <p className="text-xs text-slate-300">{safetyNotice}</p>
      </div>

      {/* 确认按钮 */}
      <div className="flex gap-2">
        <button
          className="flex-1 rounded-lg bg-orange-500/20 border border-orange-500/40 px-4 py-2 text-sm font-medium text-orange-300 hover:bg-orange-500/30 transition-all"
          onClick={() => onSelect(true)}
        >
          ✅ 确认执行
        </button>
        <button
          className="flex-1 rounded-lg bg-slate-700/60 border border-slate-600/40 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-600/70 transition-all"
          onClick={() => onSelect(false)}
        >
          ❌ 取消
        </button>
      </div>
    </div>
  );
}
