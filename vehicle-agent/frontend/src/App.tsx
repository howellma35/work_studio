import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import VehicleDashboard from "./components/VehicleDashboard";
import "@copilotkit/react-ui/styles.css";

export default function App() {
  return (
    <CopilotKit runtimeUrl="/copilotkit" agent="automind">
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950">
        {/* 顶部导航 */}
        <header className="glass-card mx-4 mt-4 flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-lg font-bold glow-blue">
              A
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AutoMind</h1>
              <p className="text-xs text-slate-400">智能车机助手 · LangGraph + MCP + CopilotKit</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse"></span>
              在线
            </span>
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-slate-700/50 px-3 py-1.5 text-xs hover:bg-slate-700 transition-colors"
            >
              LangFuse 观测台
            </a>
          </div>
        </header>

        {/* 主区域 */}
        <main className="flex gap-4 p-4">
          <div className="flex-1">
            <VehicleDashboard />
          </div>
        </main>

        {/* CopilotKit 浮动聊天窗口 */}
        <CopilotPopup
          instructions="我是 AutoMind 车机助手。你可以问我导航、播放音乐、控制车辆、查天气等。"
          labels={{
            title: "AutoMind 助手",
            initial: "你好，我是你的车载智能助手。有什么可以帮你的吗？",
            placeholder: "输入指令，如：导航去公司、播放音乐、打开车窗...",
          }}
          className="co-themed--dark"
        />
      </div>
    </CopilotKit>
  );
}
