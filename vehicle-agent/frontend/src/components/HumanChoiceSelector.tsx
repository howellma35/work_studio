import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

export interface HumanChoiceSelectorProps {
  options: string[];
  message: string;
  onSelect: (value: string) => void;
  onCancel?: () => void;
}

const OPTION_ICONS: Record<string, string> = {
  "家": "🏠",
  "公司": "🏢",
  "火车站": "🚉",
  "机场": "✈️",
  "加油站": "⛽",
  "停车场": "🅿️",
  "医院": "🏥",
  "餐厅": "🍽️",
  "当前位置": "📍",
  "确认": "✅",
  "取消": "❌",
  "是": "✅",
  "否": "❌",
};

const OPTION_COLORS: Record<string, string> = {
  "家": "from-green-500 to-emerald-400",
  "公司": "from-blue-500 to-cyan-400",
  "火车站": "from-amber-500 to-yellow-400",
  "机场": "from-purple-500 to-violet-400",
  "加油站": "from-orange-500 to-amber-400",
  "停车场": "from-sky-500 to-blue-400",
  "医院": "from-red-500 to-rose-400",
  "餐厅": "from-pink-500 to-fuchsia-400",
  "确认": "from-green-500 to-emerald-400",
  "是": "from-green-500 to-emerald-400",
  "取消": "from-slate-500 to-slate-400",
  "否": "from-red-500 to-rose-400",
};

/**
 * HumanChoiceSelector — Portal 渲染的选择卡片组件
 *
 * 脱离 CopilotKit 聊天 DOM，避免 pointer-events 被 CSS 限制。
 * 提供可点击的选项卡片 + 自由文本输入框，选择/输入后回调 onSelect。
 */
export default function HumanChoiceSelector({
  options,
  message,
  onSelect,
  onCancel,
}: HumanChoiceSelectorProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // 打开时自动聚焦输入框
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 200);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = () => {
    const val = inputValue.trim();
    if (val) {
      onSelect(val);
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const portalContent = (
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget && onCancel) onCancel();
      }}
    >
      {/* 动画卡片 */}
      <div
        className="glass-card w-[400px] max-w-[90vw] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ animation: "hitl-fade-in 0.25s ease-out" }}
      >
        {/* 标题 */}
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 text-lg shadow-lg">
            💬
          </div>
          <h3 className="text-base font-bold text-white leading-snug">
            {message || "请选择一个选项："}
          </h3>
        </div>

        {/* 选项卡片网格 */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          {options.map((opt) => (
            <button
              key={opt}
              className={`group flex items-center gap-3 rounded-xl border p-4 text-left transition-all duration-200 cursor-pointer ${
                hovered === opt
                  ? "scale-[1.03] border-blue-500/60 bg-slate-700/80 shadow-lg shadow-blue-500/10"
                  : "border-slate-700/50 bg-slate-800/50 hover:bg-slate-700/60"
              }`}
              onMouseEnter={() => setHovered(opt)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect(opt)}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${
                  OPTION_COLORS[opt] || "from-slate-500 to-slate-400"
                } text-lg font-bold shadow-md transition-transform group-hover:scale-110`}
              >
                {OPTION_ICONS[opt] || "📌"}
              </div>
              <span className="text-sm font-semibold text-white">{opt}</span>
            </button>
          ))}
        </div>

        {/* 分隔线 */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-slate-700/50" />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
            或输入自定义内容
          </span>
          <div className="flex-1 h-px bg-slate-700/50" />
        </div>

        {/* 自由文本输入框 */}
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入自定义回复..."
            className="flex-1 rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
          />
          <button
            className={`shrink-0 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
              inputValue.trim()
                ? "bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-md hover:shadow-lg hover:shadow-blue-500/20 cursor-pointer"
                : "bg-slate-800/40 text-slate-600 cursor-not-allowed"
            }`}
            onClick={handleSubmit}
            disabled={!inputValue.trim()}
          >
            发送
          </button>
        </div>

        {/* 底部取消按钮 */}
        {onCancel && (
          <button
            className="mt-4 w-full rounded-lg border border-slate-700/40 bg-slate-900/30 px-4 py-2 text-xs text-slate-400 hover:bg-slate-800/50 hover:text-slate-300 transition-colors cursor-pointer"
            onClick={onCancel}
          >
            取消
          </button>
        )}
      </div>
    </div>
  );

  return createPortal(portalContent, document.body);
}
