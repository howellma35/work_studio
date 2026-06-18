export default function MediaCard() {
  return (
    <div className="glass-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎵</span>
          <h3 className="text-lg font-bold text-white">多媒体</h3>
        </div>
        <span className="rounded-full bg-slate-700/50 px-2 py-0.5 text-xs text-slate-400">空闲</span>
      </div>

      <div className="space-y-4">
        {/* 当前播放状态 */}
        <div className="flex items-center gap-4 rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500/30 to-pink-500/30">
            <span className="text-2xl">🎶</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-white">未在播放</p>
            <p className="text-xs text-slate-500">对助手说"放点音乐"</p>
          </div>
        </div>

        {/* 音量条 */}
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>音量</span>
            <span>30%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-700/50">
            <div className="h-full w-[30%] rounded-full bg-gradient-to-r from-purple-500 to-pink-500"></div>
          </div>
        </div>

        {/* 播放控制 */}
        <div className="flex items-center justify-center gap-4">
          <button className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-700/50 text-slate-300 hover:bg-slate-700">
            ⏮
          </button>
          <button className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-pink-500 text-white glow-blue">
            ▶
          </button>
          <button className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-700/50 text-slate-300 hover:bg-slate-700">
            ⏭
          </button>
        </div>
      </div>
    </div>
  );
}
