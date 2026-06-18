import { useEffect, useState } from "react";
import NavigationCard from "./NavigationCard";
import MediaCard from "./MediaCard";
import VehicleControlCard from "./VehicleControlCard";
import WeatherCard from "./WeatherCard";

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
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* 时钟与状态卡 */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">当前时间</p>
            <p className="text-4xl font-bold text-white tabular-nums">
              {time.toLocaleTimeString("zh-CN", { hour12: false })}
            </p>
            <p className="text-sm text-slate-400 mt-1">
              {time.toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" })}
            </p>
          </div>
          <div className="text-right">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-400/20 glow-blue">
              <span className="text-2xl">🚗</span>
            </div>
          </div>
        </div>
      </div>

      {/* 车辆控制卡 */}
      <VehicleControlCard />

      {/* 天气卡 */}
      <WeatherCard />

      {/* 媒体播放器卡 */}
      <MediaCard />

      {/* 导航卡 */}
      <NavigationCard />

      {/* Agent 架构展示卡 */}
      <div className="glass-card p-6 lg:col-span-2">
        <h3 className="mb-4 text-lg font-bold text-white">Agent 架构</h3>
        {agentInfo ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {agentInfo.sub_agents.map((agent) => (
              <div
                key={agent.name}
                className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-3"
              >
                <p className="text-sm font-semibold text-cyan-400">{agent.desc}</p>
                <p className="mb-2 text-xs text-slate-500">{agent.name}</p>
                <div className="flex flex-wrap gap-1">
                  {agent.tools.map((tool) => (
                    <span
                      key={tool}
                      className="rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">加载中...</p>
        )}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-700/50 pt-4 text-xs text-slate-400">
          <span className="rounded-full bg-blue-500/10 px-3 py-1 text-blue-400">LangGraph 编排</span>
          <span className="rounded-full bg-purple-500/10 px-3 py-1 text-purple-400">MCP 协议</span>
          <span className="rounded-full bg-green-500/10 px-3 py-1 text-green-400">ChromaDB 记忆</span>
          <span className="rounded-full bg-orange-500/10 px-3 py-1 text-orange-400">LangFuse 观测</span>
          <span className="rounded-full bg-pink-500/10 px-3 py-1 text-pink-400">CopilotKit UI</span>
        </div>
      </div>
    </div>
  );
}
