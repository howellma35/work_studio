import { useState } from "react";

export interface OriginChoiceCardProps {
  options: string[];
  message: string;
  onSelect: (value: string) => void;
}

const OPTION_ICONS: Record<string, string> = {
  家: "🏠",
  公司: "🏢",
  火车站: "🚉",
  机场: "✈️",
  加油站: "⛽",
  停车场: "🅿️",
  医院: "🏥",
  餐厅: "🍽️",
  当前位置: "📍",
};

/**
 * OriginChoiceCard — 内联（聊天流内）起点选择小卡片
 *
 * 与旧版 HumanChoiceSelector 不同：不使用 createPortal、不全屏遮罩，
 * 直接作为聊天气泡中的一个紧凑卡片渲染。用户点选项或输入后回调 onSelect。
 */
export default function OriginChoiceCard({
  options,
  message,
  onSelect,
}: OriginChoiceCardProps) {
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = () => {
    const val = inputValue.trim();
    if (val) onSelect(val);
  };

  return (
    <div className="my-1.5 rounded-xl border border-slate-600/30 bg-slate-800/60 backdrop-blur-sm p-3 text-sm">
      <p className="mb-2.5 flex items-center gap-1.5 font-medium text-slate-200">
        <span>📍</span>
        {message || "请选择您的出发地点："}
      </p>

      {/* 选项 chips（横向紧凑） */}
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => onSelect(opt)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-500/40 bg-slate-700/50 px-3 py-1.5 text-xs font-medium text-slate-200 transition-all hover:border-sky-400/60 hover:bg-sky-500/15 hover:text-sky-300"
          >
            <span>{OPTION_ICONS[opt] || "📌"}</span>
            {opt}
          </button>
        ))}
      </div>

      {/* 自定义输入 */}
      <div className="mt-2.5 flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="或输入其他起点..."
          className="flex-1 rounded-lg border border-slate-600/40 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-sky-400/60 focus:outline-none"
        />
        <button
          onClick={handleSubmit}
          disabled={!inputValue.trim()}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
            inputValue.trim()
              ? "bg-blue-500 text-white hover:bg-blue-400"
              : "cursor-not-allowed bg-slate-700/40 text-slate-500"
          }`}
        >
          确定
        </button>
      </div>
    </div>
  );
}
