import { useState, useEffect, useCallback, useRef } from "react";
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
import OriginSelector from "./components/OriginSelector";
import "@copilotkit/react-ui/v2/styles.css";

// AG-UI 代理，直连后端 SSE 端点
const automindAgent = new HttpAgent({ url: "/agent" });

/** 内部布局组件 */
function AppLayout() {
  const [mapState, setMapState] = useState<MapState>(DEFAULT_MAP_STATE);
  const [amapKey, setAmapKey] = useState("");
  const [amapSecret, setAmapSecret] = useState("");

  // 起点选择器状态
  const [originSelectorVisible, setOriginSelectorVisible] = useState(false);
  const [originSelectorOptions, setOriginSelectorOptions] = useState<string[]>(["家", "公司", "火车站", "机场"]);
  const [originSelectorMessage, setOriginSelectorMessage] = useState("请选择您的出发地点：");
  const originResolveRef = useRef<((value: string) => void) | null>(null);

  // 从后端API获取高德地图Key（同步到React state，触发MapPanel重新初始化）
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

  // 注册前端工具：select_origin
  useFrontendTool({
    name: "select_origin",
    description: "让用户选择导航起点位置。弹出选择面板，提供家、公司、火车站、机场等常见起点选项。",
    parameters: z.object({
      options: z.array(z.string()).describe("可选起点列表"),
      message: z.string().describe("询问起点时展示给用户的提示文本"),
    }),
    handler: async (args) => {
      const { options, message } = args;

      return new Promise<string>((resolve) => {
        originResolveRef.current = resolve;
        setOriginSelectorOptions(options || ["家", "公司", "火车站", "机场"]);
        setOriginSelectorMessage(message || "请选择您的出发地点：");
        setOriginSelectorVisible(true);
      });
    },
  });

  // 注册前端工具：update_map
  useFrontendTool({
    name: "update_map",
    description:
      "更新地图显示。当规划导航路线、搜索 POI 或更新位置时调用此工具。",
    parameters: z.object({
      action: z
        .enum(["navigate", "search_poi", "clear"])
        .describe("操作类型：navigate=导航, search_poi=搜索兴趣点, clear=清除路线"),
      destination: z.string().optional().describe("目的地名称"),
      destination_lat: z.number().optional().describe("目的地纬度"),
      destination_lng: z.number().optional().describe("目的地经度"),
      origin: z.string().optional().describe("起点名称"),
      origin_lat: z.number().optional().describe("起点纬度"),
      origin_lng: z.number().optional().describe("起点经度"),
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
        .describe("POI 列表"),
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
          routeCoords = args.route_coords.map(
            (c) => [c[0], c[1]] as [number, number],
          );
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
        return `地图已更新导航路线: ${originName} → ${destName}`;
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
  });

  const handleOriginSelect = useCallback((selected: string) => {
    setOriginSelectorVisible(false);
    if (originResolveRef.current) {
      originResolveRef.current(selected);
      originResolveRef.current = null;
    }
  }, []);

  const handleOriginCancel = useCallback(() => {
    setOriginSelectorVisible(false);
    if (originResolveRef.current) {
      originResolveRef.current("当前位置");
      originResolveRef.current = null;
    }
  }, []);

  return (
    <CopilotSidebar
      defaultOpen
      instructions={`你是 AutoMind 车机助手。你可以帮用户导航、播放音乐、控制车辆、查天气等。

重要规则：
- 当用户没有明确指定起点时，必须先调用 select_origin 前端工具让用户选择起点
- select_origin 的 options 参数设为 ["家", "公司", "火车站", "机场"]
- 调用 plan_route 工具获得导航数据后，必须调用 update_map 前端工具来更新地图显示
- 调用 search_poi 工具获得 POI 数据后，必须调用 update_map(action="search_poi") 来在地图上标记兴趣点
- update_map 的 route_coords 格式为 [[lat, lng], ...], pois 格式为 [{"name":"xx","lat":31.23,"lng":121.47}, ...]
- 回复要简洁，适合车载语音播报场景`}
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
                智能车机助手 · 高德地图 + LangGraph + MCP
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              在线
            </span>
          </div>
        </header>

        {/* 主区域 */}
        <main className="flex-1 overflow-hidden p-4">
          <div className="flex h-full flex-col gap-4">
            <div className="flex-1 min-h-0">
              <MapPanel
                mapState={mapState}
                amapKey={amapKey}
                amapSecret={amapSecret}
              />
            </div>
            <div className="shrink-0">
              <VehicleDashboard />
            </div>
          </div>
        </main>
      </div>

      {/* 起点选择浮层 */}
      {originSelectorVisible && (
        <OriginSelector
          options={originSelectorOptions}
          message={originSelectorMessage}
          onSelect={handleOriginSelect}
          onCancel={handleOriginCancel}
        />
      )}
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
