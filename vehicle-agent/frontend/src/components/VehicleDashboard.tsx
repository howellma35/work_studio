import { useEffect, useState } from "react";

interface AgentInfo {
  agent_name: string;
  sub_agents: Array<{ name: string; desc: string; tools: string[] }>;
}

export default function VehicleDashboard() {
  const [agentInfo, setAgentInfo] = useState<AgentInfo | null>(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetch("/api/vehicle/agent-info")
      .then((res) => res.json())
      .then(setAgentInfo)
      .catch(() => {});
  }, []);

  return (
    <div className="flex gap-3 overflow-x-auto pb-1">
      {/* 时钟 */}
      <div className="glass-card shrink-0 px-4 py-2.5 flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-400/20 glow-blue">
          <span className="text-sm">🚗</span>
        </div>
        <div>
          <p className="text-sm font-bold text-white tabular-nums">
            {time.toLocaleTimeString("zh-CN", { hour12: false })}
          </p>
          <p className="text-[10px] text-slate-400">
            {time.toLocaleDateString("zh-CN", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
      </div>

      {/* 车辆状态 */}
      <div className="glass-card shrink-0 px-4 py-2.5 flex items-center gap-3">
        <span className="text-sm">⚙️</span>
        <div className="flex gap-2 text-[10px]">
          <span className="rounded bg-green-500/10 px-1.5 py-0.5 text-green-400">
            电量 78%
          </span>
          <span className="rounded bg-slate-700/50 px-1.5 py-0.5 text-slate-400">
            ❄️ 22°C
          </span>
          <span className="rounded bg-slate-700/50 px-1.5 py-0.5 text-slate-400">
            🔒 已锁
          </span>
        </div>
      </div>

      {/* 天气 */}
      <div className="glass-card shrink-0 px-4 py-2.5 flex items-center gap-2">
        <span className="text-sm">🌤️</span>
        <span className="text-xs text-slate-300">上海 26°C</span>
        <span className="text-[10px] text-slate-500">晴</span>
      </div>

      {/* Agent 架构标签 */}
      {agentInfo && (
        <div className="glass-card shrink-0 px-4 py-2.5 flex items-center gap-2">
          <span className="text-sm">🤖</span>
          <div className="flex gap-1">
            {agentInfo.sub_agents.map((a) => (
              <span
                key={a.name}
                className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] text-cyan-400"
              >
                {a.desc}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 技术栈标签 */}
      <div className="glass-card shrink-0 px-4 py-2.5 flex items-center gap-1.5">
        <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-400">
          LangGraph
        </span>
        <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-[10px] text-purple-400">
          MCP
        </span>
        <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] text-green-400">
          ChromaDB
        </span>
        <span className="rounded-full bg-orange-500/10 px-2 py-0.5 text-[10px] text-orange-400">
          LangFuse
        </span>
      </div>
    </div>
  );
}
