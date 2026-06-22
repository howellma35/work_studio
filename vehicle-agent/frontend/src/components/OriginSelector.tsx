import { useState } from "react";
import { createPortal } from "react-dom";

export interface OriginSelectorProps {
  options: string[];
  message: string;
  onSelect: (selected: string) => void;
  onCancel: () => void;
}

const OPTION_ICONS: Record<string, string> = {
  "家": "🏠",
  "公司": "🏢",
  "火车站": "🚉",
  "机场": "✈️",
};

const OPTION_COLORS: Record<string, string> = {
  "家": "from-green-500 to-emerald-400",
  "公司": "from-blue-500 to-cyan-400",
  "火车站": "from-amber-500 to-yellow-400",
  "机场": "from-purple-500 to-violet-400",
};

export default function OriginSelector({ options, message, onSelect, onCancel }: OriginSelectorProps) {
  const [hovered, setHovered] = useState<string | null>(null);

  // 用 Portal 渲染到 body，避免 CopilotSidebar 内部 DOM 结构干扰
  const portalContent = (
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => {
        // 点击背景区域（非卡片内容）触发取消
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="glass-card w-[360px] p-6" onClick={(e) => e.stopPropagation()}>
        {/* 标题 */}
        <div className="mb-4 flex items-center gap-2">
          <span className="text-xl">🧭</span>
          <h3 className="text-lg font-bold text-white">{message || "请选择您的出发地点："}</h3>
        </div>

        {/* 选项按钮 */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {options.map((opt) => (
            <button
              key={opt}
              className={`flex items-center gap-3 rounded-xl p-4 text-left transition-all duration-200 cursor-pointer ${
                hovered === opt
                  ? "scale-105 border-slate-500 bg-slate-700/70 shadow-lg"
                  : "border-slate-700/50 bg-slate-800/50 hover:bg-slate-700/70"
              } border`}
              onMouseEnter={() => setHovered(opt)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect(opt)}
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br ${
                OPTION_COLORS[opt] || "from-slate-500 to-slate-400"
              } text-lg font-bold shadow-md`}>
                {OPTION_ICONS[opt] || "📍"}
              </div>
              <span className="text-sm font-medium text-white">{opt}</span>
            </button>
          ))}
        </div>

        {/* 取消按钮 */}
        <button
          className="w-full rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-2 text-xs text-slate-400 hover:bg-slate-700/50 hover:text-slate-300 transition-colors cursor-pointer"
          onClick={onCancel}
        >
          取消选择（使用当前位置）
        </button>
      </div>
    </div>
  );

  return createPortal(portalContent, document.body);
}
