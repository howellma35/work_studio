import { useState } from "react";
import { CopilotKit } from "@copilotkit/react-core/v2";
import { useFrontendTool } from "@copilotkit/react-core/v2";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { HttpAgent } from "@ag-ui/client";
import { z } from "zod";
import MapPanel, {
  type MapState,
  DEFAULT_MAP_STATE,
  resolveDestination,
  generateRouteCoords,
} from "./components/MapPanel";
import VehicleDashboard from "./components/VehicleDashboard";
import "@copilotkit/react-ui/v2/styles.css";

// AG-UI 代理，直连后端 SSE 端点（通过 Vite 代理转发到 localhost:8001）
const automindAgent = new HttpAgent({ url: "/agent" });

/** 内部布局组件 — 可使用 CopilotKit hooks */
function AppLayout() {
  const [mapState, setMapState] = useState<MapState>(DEFAULT_MAP_STATE);

  // 注册前端工具：Agent 调用 update_map 时自动更新地图
  useFrontendTool({
    name: "update_map",
    description:
      "更新地图显示。当规划导航路线、搜索 POI 或更新位置时调用此工具。",
    parameters: z.object({
      action: z
        .enum(["navigate", "search_poi", "clear"])
        .describe("操作类型：navigate=导航, search_poi=搜索兴趣点, clear=清除路线"),
      destination: z.string().optional().describe("目的地名称（navigate 时必填）"),
      destination_lat: z.number().optional().describe("目的地纬度（如有精确坐标）"),
      destination_lng: z.number().optional().describe("目的地经度（如有精确坐标）"),
      distance_km: z.number().optional().describe("距离（公里）"),
      duration_min: z.number().optional().describe("预计时长（分钟）"),
      steps: z.array(z.string()).optional().describe("路线步骤描述列表"),
      route_coords: z
        .array(z.array(z.number()))
        .optional()
        .describe("路线坐标序列 [[lat, lng], ...]"),
      pois: z
        .array(z.object({ name: z.string(), lat: z.number(), lng: z.number() }))
        .optional()
        .describe('POI 列表 [{"name": "xxx", "lat": 31.23, "lng": 121.47}, ...]'),
    }),
    handler: async (args) => {
      const { action } = args;

      if (action === "navigate") {
        const destName = args.destination || "目的地";
        let destCoord: [number, number];
        if (args.destination_lat && args.destination_lng) {
          destCoord = [args.destination_lat, args.destination_lng];
        } else {
          destCoord = resolveDestination(destName, mapState.currentPosition);
        }

        let routeCoords: [number, number][];
        if (args.route_coords) {
          routeCoords = args.route_coords.map(
            (c) => [c[0], c[1]] as [number, number],
          );
        } else {
          routeCoords = generateRouteCoords(mapState.currentPosition, destCoord);
        }

        setMapState((prev) => ({
          ...prev,
          destination: destCoord,
          destinationName: destName,
          routeCoords,
          routeInfo: {
            origin: "当前位置",
            destination: destName,
            distanceKm: args.distance_km || 0,
            durationMin: args.duration_min || 0,
            steps: args.steps || [],
          },
        }));
        return "地图已更新导航路线";
      }

      if (action === "search_poi") {
        const pois = (args.pois || []).map((p) => ({
          name: p.name,
          lat: p.lat,
          lng: p.lng,
        }));
        setMapState((prev) => ({ ...prev, pois }));
        return `地图已显示 ${pois.length} 个兴趣点`;
      }

      if (action === "clear") {
        setMapState((prev) => ({
          ...prev,
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
  });

  return (
    <CopilotSidebar
      defaultOpen
      instructions={`你是 AutoMind 车机助手。你可以帮用户导航、播放音乐、控制车辆、查天气等。

重要规则：
- 当调用 plan_route 工具获得导航数据后，必须调用 update_map 前端工具来更新地图显示
- 当调用 search_poi 工具获得 POI 数据后，必须调用 update_map(action="search_poi") 来在地图上标记兴趣点
- update_map 的 route_coords 格式为 [[lat, lng], ...], pois 格式为 [{"name":"xx","lat":31.23,"lng":121.47}, ...]
- 回复要简洁，适合车载语音播报场景`
      }
      labels={{
        title: "AutoMind 助手",
        initial: "你好，我是你的车载智能助手。有什么可以帮你的吗？",
        placeholder: "输入指令，如：导航去公司、播放音乐、打开车窗...",
      }}
    >
      <div className="flex h-screen flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950">
        {/* 顶部导航栏 */}
        <header className="glass-card mx-4 mt-4 flex items-center justify-between px-6 py-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-sm font-bold glow-blue">
              A
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">AutoMind</h1>
              <p className="text-[10px] text-slate-400">
                智能车机助手 · LangGraph + MCP + AG-UI
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
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

        {/* 主区域：左地图 + 下方信息卡 */}
        <main className="flex-1 overflow-hidden p-4">
          <div className="flex h-full flex-col gap-4">
            {/* 地图（占满主要区域） */}
            <div className="flex-1 min-h-0">
              <MapPanel mapState={mapState} />
            </div>
            {/* 底部紧凑信息卡 */}
            <div className="shrink-0">
              <VehicleDashboard />
            </div>
          </div>
        </main>
      </div>
    </CopilotSidebar>
  );
}

export default function App() {
  return (
    <CopilotKit agents__unsafe_dev_only={{ default: automindAgent }}>
      <AppLayout />
    </CopilotKit>
  );
}
