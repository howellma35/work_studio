export default function VehicleControlCard() {
  const controls = [
    { icon: "🪟", label: "车窗", status: "关闭", color: "text-slate-400" },
    { icon: "❄️", label: "空调", status: "22°C", color: "text-blue-400" },
    { icon: "🔒", label: "门锁", status: "已锁", color: "text-green-400" },
    { icon: "💺", label: "座椅", status: "标准", color: "text-slate-400" },
  ];

  return (
    <div className="glass-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚙️</span>
          <h3 className="text-lg font-bold text-white">车辆控制</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">电量</span>
          <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-400">78%</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {controls.map((item) => (
          <div
            key={item.label}
            className="flex items-center justify-between rounded-lg border border-slate-700/50 bg-slate-800/30 p-3"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">{item.icon}</span>
              <span className="text-sm text-slate-300">{item.label}</span>
            </div>
            <span className={`text-sm font-medium ${item.color}`}>{item.status}</span>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">里程</span>
          <span className="text-sm text-slate-300">15,234 km</span>
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        💡 通过助手语音控制："把空调调到24度"
      </p>
    </div>
  );
}
