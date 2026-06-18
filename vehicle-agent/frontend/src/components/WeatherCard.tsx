export default function WeatherCard() {
  return (
    <div className="glass-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-xl">🌤️</span>
        <h3 className="text-lg font-bold text-white">天气</h3>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">上海</p>
          <p className="text-4xl font-bold text-white">26°C</p>
          <p className="text-sm text-slate-400">多云</p>
        </div>
        <div className="text-5xl">⛅</div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-2">
          <p className="text-xs text-slate-500">湿度</p>
          <p className="text-sm font-medium text-slate-200">65%</p>
        </div>
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-2">
          <p className="text-xs text-slate-500">风力</p>
          <p className="text-sm font-medium text-slate-200">3级</p>
        </div>
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-2">
          <p className="text-xs text-slate-500">AQI</p>
          <p className="text-sm font-medium text-green-400">45</p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
        <p className="text-xs text-blue-300">
          💡 对助手说"明天天气怎么样"获取预报
        </p>
      </div>
    </div>
  );
}
