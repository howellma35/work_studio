import { useState } from "react";

export default function NavigationCard() {
  const [destination, setDestination] = useState("");

  return (
    <div className="glass-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-xl">🧭</span>
        <h3 className="text-lg font-bold text-white">导航</h3>
      </div>

      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="输入目的地..."
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
          <p className="mb-2 text-xs text-slate-400">快速目的地</p>
          <div className="flex flex-wrap gap-2">
            {["🏠 家", "🏢 公司", "🚉 火车站", "✈️ 机场", "⛽ 加油站", "🏥 医院"].map((item) => (
              <button
                key={item}
                className="rounded-full bg-slate-700/50 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-blue-500/30 hover:text-white"
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <p className="text-xs text-blue-400">
            💡 提示：直接通过右下角聊天框对助手说"导航去公司"即可规划路线。
            系统会询问您的出发地点（家/公司/火车站/机场），并使用高德地图进行真实路线规划。
          </p>
        </div>
      </div>
    </div>
  );
}
