import { useState, useEffect } from "react";
import { CopilotKit } from "@copilotkit/react-core/v2";
import {
  useFrontendTool,
  useHumanInTheLoop,
  useDefaultRenderTool,
} from "@copilotkit/react-core/v2";
import { CopilotChat, AssistantMessage as DefaultAssistantMessage } from "@copilotkit/react-ui";
import { z } from "zod";
import MapPanel, {
  type MapState,
  DEFAULT_MAP_STATE,
  resolveDestination,
  generateRouteCoords,
} from "./components/MapPanel";
import VehicleDashboard from "./components/VehicleDashboard";
import OriginChoiceCard from "./components/OriginChoiceCard";
import AgentToolCard from "./components/AgentToolCard";
import "@copilotkit/react-ui/v2/styles.css";

// ===== 每日对话次数管理 =====
const VEHICLE_DAILY_LIMIT = 5;

function getVehicleTodayKey() {
  return `vehicle_chat_count_${new Date().toISOString().slice(0, 10)}`;
}
function getVehicleTodayCount(): number {
  return parseInt(localStorage.getItem(getVehicleTodayKey()) || "0", 10);
}
function incrementVehicleCount(): number {
  const count = getVehicleTodayCount() + 1;
  localStorage.setItem(getVehicleTodayKey(), String(count));
  return count;
}

// CopilotKit Runtime 模式：前端通过 runtimeUrl 连接 Runtime 服务器
// Runtime 服务器（Express:4000）代理请求到 Python 后端（FastAPI:8001）
// 不再使用 selfManagedAgents 直连模式

// 折叠/展开按钮图标
function CollapseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}
function ExpandIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

/**
 * 自定义 AssistantMessage：
 * 1. 把 ROUTE_DATA/POI_DATA 数据行折叠进 <details>（默认收起）
 * 2. 如果消息中包含 update_map 等工具调用且正在执行，隐藏文字内容，
 *    显示“正在查询路况”加载提示，等工具完成后再显示文字
 */
function FoldableAssistantMessage(props: any) {
  const rawContent: string = props.message?.content || "";
  const hasToolCalls = !!props.message?.generativeUI;
  const isGenerating = !!props.isGenerating;

  // 如果当前消息仍在生成中且有工具调用（如 update_map 正在传输数据），
  // 隐藏文字内容，显示加载提示
  if (hasToolCalls && isGenerating && rawContent) {
    return (
      <div className="copilotKitMessage copilotKitAssistantMessage">
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
          <span>正在查询路况，请稍候...</span>
        </div>
      </div>
    );
  }

  // 检测以 ROUTE_DATA: 或 POI_DATA: 开头的行（navigation_agent 返回的结构化数据）
  if (!/^(ROUTE_DATA|POI_DATA):/m.test(rawContent)) {
    return <DefaultAssistantMessage {...props} />;
  }

  // 把数据行替换为 <details> 折叠框
  const processedContent = rawContent.replace(
    /^(ROUTE_DATA|POI_DATA):.*$/gm,
    (line) => {
      const prefix = line.startsWith("ROUTE_DATA") ? "ROUTE_DATA" : "POI_DATA";
      const label = prefix === "ROUTE_DATA" ? "路线数据" : "POI数据";
      // 转义 HTML 特殊字符，避免破坏 <pre> 渲染
      const escaped = line
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return `<details class="route-data-fold"><summary>📊 ${label}（点击展开）</summary><pre>${escaped}</pre></details>`;
    },
  );

  return (
    <DefaultAssistantMessage
      {...props}
      message={{ ...props.message, content: processedContent }}
    />
  );
}

/** 内部布局组件 */
function AppLayout() {
  const [mapState, setMapState] = useState<MapState>(DEFAULT_MAP_STATE);
  const [amapKey, setAmapKey] = useState("");
  const [amapSecret, setAmapSecret] = useState("");
  const [chatOpen, setChatOpen] = useState(true);
  const [dailyCount, setDailyCount] = useState(getVehicleTodayCount);

  // 从后端获取真实计数（防止 localStorage 被清绕过）
  useEffect(() => {
    fetch("/api/vehicle/chat-count")
      .then((res) => res.json())
      .then((data) => {
        if (typeof data.used === "number") {
          setDailyCount(data.used);
        }
      })
      .catch(() => {});
  }, []);

  // 导航完成后自动计数（前端 + 后端都会计数）
  const recordUsage = () => {
    const newCount = incrementVehicleCount();
    setDailyCount(newCount);
  };

  const isLimitReached = dailyCount >= VEHICLE_DAILY_LIMIT;

  // 从后端API获取高德地图Key
  useEffect(() => {
    fetch("/api/vehicle/agent-info")
      .then((res) => res.json())
      .then((data) => {
        if (data.amap_js_key) {
          setAmapKey(data.amap_js_key);
          if (data.amap_js_secret) {
            setAmapSecret(data.amap_js_secret);
          }
        }
      })
      .catch(() => {
        console.warn("无法从后端获取高德地图Key");
      });
  }, []);

  // ===== useHumanInTheLoop: select_origin — 官方标准 Human-in-the-Loop =====
  //
  // Agent 调用 select_origin 时，CopilotKit 暂停执行并触发 render 函数。
  // render 直接在聊天流中渲染内联小卡片 OriginChoiceCard（不再用全屏模态），
  // 用户选择/输入后 respond() 把结果返回给大模型继续执行。
  // 各状态卡片都保留在消息流中，形成可回看的历史调用记录。
  useHumanInTheLoop({
    name: "select_origin",
    description:
      "让用户选择导航起点位置。在聊天中展示一个内联选择卡片，提供家、公司、火车站、机场等常见起点选项，也可输入自定义地点。",
    parameters: z.object({
      options: z.array(z.string()).describe("可选起点列表"),
      message: z.string().describe("询问起点时展示给用户的提示文本"),
    }),
    render: ({ args, status, respond }) => {
      if (status === "inProgress") {
        return (
          <div className="my-1.5 flex items-center gap-2 rounded-xl border border-slate-600/30 bg-slate-800/50 backdrop-blur-sm p-2.5 text-xs text-slate-300">
            <span className="animate-spin">⏳</span> 正在准备起点选择...
          </div>
        );
      }

      if (status === "executing" && respond) {
        const options = (args as any)?.options || ["家", "公司", "火车站", "机场"];
        const message = (args as any)?.message || "请选择您的出发地点：";
        return (
          <OriginChoiceCard
            options={options}
            message={message}
            onSelect={(value: string) => respond(value)}
          />
        );
      }

      // complete — 保留一条紧凑的历史记录
      const picked = (args as any)?.__picked;
      return (
        <div className="my-1.5 inline-flex items-center gap-1.5 rounded-lg border border-slate-600/30 bg-slate-800/50 backdrop-blur-sm px-2.5 py-1 text-xs text-slate-300">
          ✓ 已选择起点{picked ? `：${picked}` : ""}
        </div>
      );
    },
  });

  // useFrontendTool: update_map — 前端执行handler，更新地图显示
  useFrontendTool({
    name: "update_map",
    description: "更新地图显示。当规划导航路线、搜索 POI 或更新位置时调用此工具。",
    parameters: z.object({
      action: z.enum(["navigate", "search_poi", "clear"]).describe("操作类型"),
      destination: z.string().optional().describe("目的地名称"),
      destination_lat: z.number().optional().describe("目的地纬度"),
      destination_lng: z.number().optional().describe("目的地经度"),
      origin: z.string().optional().describe("起点名称"),
      origin_lat: z.number().optional().describe("起点纬度"),
      origin_lng: z.number().optional().describe("起点经度"),
      distance_km: z.number().optional().describe("距离（公里）"),
      duration_min: z.number().optional().describe("预计时长（分钟）"),
      steps: z.array(z.string()).optional().describe("路线步骤描述列表"),
      route_coords: z.array(z.array(z.number())).optional().describe("路线坐标序列 [[lat, lng], ...]"),
      pois: z.array(z.object({ name: z.string(), lat: z.number(), lng: z.number() })).optional().describe("POI 列表"),
    }),
    handler: async (args) => {
      const { action } = args;

      if (action === "navigate") {
        const destName = args.destination || "目的地";
        const originName = args.origin || "当前位置";

        let destCoord: [number, number];
        if (args.destination_lat && args.destination_lng) {
          destCoord = [args.destination_lat, args.destination_lng];
        } else {
          destCoord = resolveDestination(destName, mapState.currentPosition);
        }

        let originCoord: [number, number] | undefined;
        if (args.origin_lat && args.origin_lng) {
          originCoord = [args.origin_lat, args.origin_lng];
        } else if (originName !== "当前位置") {
          originCoord = resolveDestination(originName, mapState.currentPosition);
        }

        let routeCoords: [number, number][];
        if (args.route_coords) {
          routeCoords = args.route_coords.map((c) => [c[0], c[1]] as [number, number]);
        } else if (originCoord) {
          routeCoords = generateRouteCoords(originCoord, destCoord);
        } else {
          routeCoords = generateRouteCoords(mapState.currentPosition, destCoord);
        }

        setMapState((prev) => ({
          ...prev,
          origin: originCoord,
          originName: originName !== "当前位置" ? originName : undefined,
          destination: destCoord,
          destinationName: destName,
          routeCoords,
          routeInfo: {
            origin: originName,
            destination: destName,
            distanceKm: args.distance_km || 0,
            durationMin: args.duration_min || 0,
            steps: args.steps || [],
          },
        }));
        recordUsage();
        return `地图已更新导航路线: ${originName} → ${destName}`;
      }

      if (action === "search_poi") {
        const pois = (args.pois || []).map((p) => ({ name: p.name, lat: p.lat, lng: p.lng }));
        setMapState((prev) => ({ ...prev, pois }));
        return `地图已显示 ${pois.length} 个兴趣点`;
      }

      if (action === "clear") {
        setMapState((prev) => ({
          ...prev,
          origin: undefined,
          originName: undefined,
          destination: undefined,
          destinationName: undefined,
          routeCoords: [],
          routeInfo: null,
          pois: [],
        }));
        return "地图已清除导航数据";
      }

      return "未知操作";
    },
    // render：聊天流内渲染紧凑导航卡片（不显示逐条 steps 长文本），保留为历史记录
    render: ({ args, status }) => {
      const a = (args as any) || {};
      if (a.action === "search_poi") {
        const n = (a.pois || []).length;
        return (
          <AgentToolCard
            icon="📍"
            title="地图标记兴趣点"
            subtitle={status === "complete" ? `已标记 ${n} 个地点` : "更新地图中..."}
            done={status === "complete"}
          />
        );
      }
      if (a.action === "clear") {
        return (
          <AgentToolCard icon="🗺️" title="清除地图" subtitle="" done={status === "complete"} />
        );
      }
      // navigate
      const origin = a.origin || "当前位置";
      const dest = a.destination || "目的地";
      const meta =
        a.distance_km || a.duration_min
          ? `${a.distance_km ?? "?"} km · 约 ${a.duration_min ?? "?"} 分钟`
          : status === "complete"
            ? "路线已显示在地图"
            : "正在传输路线数据...";
      return (
        <AgentToolCard
          icon="🧭"
          title={`${origin} → ${dest}`}
          subtitle={meta}
          done={status === "complete"}
        />
      );
    },
  });

  // 后端子Agent 工具调用（navigation_agent / media_agent / ...）的通用渲染：
  // 用紧凑卡片代替大段原始文本，避免长文本刷屏；历史调用自然保留在 thread 中。
  useDefaultRenderTool({
    render: ({ name, status }) => {
      const labelMap: Record<string, string> = {
        navigation_agent: "导航助手",
        media_agent: "多媒体助手",
        vehicle_agent: "车辆控制",
        weather_agent: "天气助手",
        reminder_agent: "提醒助手",
      };
      const title = labelMap[name] || name;
      return (
        <AgentToolCard
          icon="🤖"
          title={title}
          subtitle={status === "complete" ? "已完成" : "处理中..."}
          done={status === "complete"}
        />
      );
    },
  });

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950">
      {/* ====== 左侧：地图 + 仪表盘 ====== */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${chatOpen ? "" : "flex-1"}`}>
        {/* 顶部导航栏 */}
        <header className="mx-4 mt-4 flex items-center justify-between px-5 py-3 rounded-xl border border-slate-700/40 bg-slate-900/60 backdrop-blur shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-sm font-bold shadow-lg shadow-blue-500/20">
              A
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">AutoMind</h1>
              <p className="text-[10px] text-slate-400">智能车机助手 · 高德地图 + LangGraph</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-sm text-slate-300">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              在线
            </span>
            {/* 每日限制计数器 */}
            <span className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border ${
              isLimitReached
                ? "border-red-500/40 bg-red-500/10 text-red-300"
                : "border-slate-600/40 bg-slate-800/60 text-slate-300"
            }`}>
              💬 {VEHICLE_DAILY_LIMIT - dailyCount}/{VEHICLE_DAILY_LIMIT}
            </span>
            {/* 折叠/展开聊天按钮 */}
            <button
              className="flex items-center gap-1 rounded-lg border border-slate-700/40 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700/70 hover:text-white transition-all"
              onClick={() => setChatOpen(!chatOpen)}
            >
              {chatOpen ? <CollapseIcon /> : <ExpandIcon />}
              {chatOpen ? "收起" : "展开"}对话
            </button>
          </div>
        </header>

        {/* 主区域 */}
        <main className="flex-1 overflow-hidden p-4">
          <div className="flex h-full flex-col gap-4">
            <div className="flex-1 min-h-0">
              <MapPanel mapState={mapState} amapKey={amapKey} amapSecret={amapSecret} />
            </div>
            <div className="shrink-0">
              <VehicleDashboard />
            </div>
          </div>
        </main>
      </div>

      {/* ====== 右侧：可折叠聊天面板 ====== */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 flex flex-col border-l border-slate-700/40 bg-slate-950/80 backdrop-blur transition-all duration-300 relative">
          <CopilotChat
            AssistantMessage={FoldableAssistantMessage}
            instructions={`你是 AutoMind 车机助手。目前只支持导航功能，其他功能（音乐、车辆控制、天气、提醒）正在开发中。

重要规则：
- 当用户询问非导航功能时，礼貌地告知该功能正在开发中，建议用户先体验导航功能
- 当用户没有明确指定起点时，必须先调用 select_origin 前端工具让用户选择起点
- select_origin 的 options 参数设为 ["家", "公司", "火车站", "机场"]
- 调用 plan_route 工具获得导航数据后，必须调用 update_map 前端工具来更新地图显示
- 调用 search_poi 工具获得 POI 数据后，必须调用 update_map(action="search_poi") 来在地图上标记兴趣点
- update_map 的 route_coords 格式为 [[lat, lng], ...], pois 格式为 [{"name":"xx","lat":31.23,"lng":121.47}, ...]
- 回复要简洁，适合车载语音播报场景`}
            labels={{
              title: "AutoMind 助手",
              initial: "你好，我是你的车载智能助手。\n\n📢 **目前只支持导航功能**，其他功能（音乐、车辆控制、天气等）正在开发中。\n\n你可以试试说：\n- 导航到张江科技园\n- 带我去虹桥机场\n- 去最近的加油站\n- 导航回家",
              placeholder: isLimitReached
                ? "今日对话次数已用完，明天再来吧"
                : "输入指令，如：导航到张江科技园...",
            }}
            className="h-full flex-1"
          />
          {/* 每日限制遮罩 */}
          {isLimitReached && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/90 backdrop-blur-sm z-10">
              <div className="flex flex-col items-center gap-3 px-6 text-center">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center border border-red-500/30">
                  <span className="text-2xl">📝</span>
                </div>
                <h3 className="text-base font-semibold text-white">今日对话次数已用完</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  每位用户每天最多 <span className="text-red-400 font-semibold">{VEHICLE_DAILY_LIMIT}</span> 次对话
                  <br />
                  请明天再来吧 🙏
                </p>
                <div className="mt-2 text-xs text-slate-500">
                  剩余 {VEHICLE_DAILY_LIMIT - dailyCount}/{VEHICLE_DAILY_LIMIT}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}

export default function App() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" useSingleEndpoint={false}>
      <AppLayout />
    </CopilotKit>
  );
}
