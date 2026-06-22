import { useEffect, useRef } from "react";
import AMapLoader from "@amap/amap-jsapi-loader";

/* ==================== 类型 ==================== */
export interface RouteInfo {
  origin: string;
  destination: string;
  distanceKm: number;
  durationMin: number;
  steps: string[];
}

export interface MapState {
  /** 当前位置 [lat, lng] */
  currentPosition: [number, number];
  /** 起点坐标 */
  origin?: [number, number];
  /** 起点名称 */
  originName?: string;
  /** 目的地坐标 */
  destination?: [number, number];
  /** 目的地名称 */
  destinationName?: string;
  /** 路线坐标序列 (lat,lng 格式) */
  routeCoords: [number, number][];
  /** 路线信息 */
  routeInfo: RouteInfo | null;
  /** POI 标记 */
  pois: { name: string; lat: number; lng: number }[];
}

export const DEFAULT_MAP_STATE: MapState = {
  currentPosition: [31.2304, 121.4737], // 上海人民广场
  routeCoords: [],
  routeInfo: null,
  pois: [],
};

/* ============ 目的地 → 坐标映射（预设常用地点） ============ */
const DEST_COORDS: Record<string, [number, number]> = {
  公司: [31.2397, 121.4998],
  陆家嘴: [31.2363, 121.5055],
  外滩: [31.24, 121.49],
  南京路: [31.2352, 121.475],
  虹桥机场: [31.198, 121.3363],
  浦东机场: [31.1434, 121.8081],
  火车站: [31.1944, 121.4557],
  徐家汇: [31.1905, 121.437],
  静安寺: [31.2238, 121.4473],
  世纪公园: [31.215, 121.543],
  家: [31.218, 121.445],
  加油站: [31.225, 121.46],
  停车场: [31.232, 121.48],
  餐厅: [31.228, 121.472],
  医院: [31.22, 121.465],
};

/** 根据地名解析坐标，未知地名在当前位置附近随机偏移 */
export function resolveDestination(
  name: string,
  current: [number, number],
): [number, number] {
  for (const [key, coord] of Object.entries(DEST_COORDS)) {
    if (name.includes(key) || key.includes(name)) return coord;
  }
  return [
    current[0] + (Math.random() - 0.5) * 0.04,
    current[1] + (Math.random() - 0.5) * 0.04,
  ];
}

/** 在两点之间生成折线路径（fallback，当没有真实路线坐标时使用） */
export function generateRouteCoords(
  origin: [number, number],
  dest: [number, number],
): [number, number][] {
  const pts: [number, number][] = [origin];
  const steps = 5 + Math.floor(Math.random() * 4);
  for (let i = 1; i < steps; i++) {
    const t = i / steps;
    pts.push([
      origin[0] + (dest[0] - origin[0]) * t + (Math.random() - 0.5) * 0.006,
      origin[1] + (dest[1] - origin[1]) * t + (Math.random() - 0.5) * 0.006,
    ]);
  }
  pts.push(dest);
  return pts;
}

/* ==================== 主组件 ==================== */
interface MapPanelProps {
  mapState: MapState;
  amapKey: string;
  amapSecret: string;
}

export default function MapPanel({ mapState, amapKey, amapSecret }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const drivingRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polylineRef = useRef<any>(null);
  const poiMarkersRef = useRef<any[]>([]);
  const initAttemptRef = useRef(0); // 追踪初始化尝试次数

  const {
    currentPosition,
    origin,
    originName,
    destination,
    destinationName,
    routeCoords,
    routeInfo,
    pois,
  } = mapState;

  // 初始化高德地图 — 当 amapKey 变化时重新初始化
  useEffect(() => {
    if (!containerRef.current) return;
    if (!amapKey || amapKey === "your-amap-js-key-here" || amapKey === "your-amap-api-key") {
      console.warn("高德地图Key未配置，跳过地图初始化");
      return;
    }

    // 防止重复初始化（同一个Key不重新加载）
    if (mapRef.current && initAttemptRef.current > 0) {
      return;
    }

    // 设置安全密钥（必须在 AMapLoader.load 之前）
    if (amapSecret) {
      (window as any)._AMapSecurityConfig = {
        securityJsCode: amapSecret,
      };
    }

    // 销毁旧地图实例（如果存在）
    if (mapRef.current) {
      mapRef.current.destroy();
      mapRef.current = null;
      markersRef.current = [];
      poiMarkersRef.current = [];
      drivingRef.current = null;
      polylineRef.current = null;
    }

    initAttemptRef.current += 1;

    AMapLoader.load({
      key: amapKey,
      version: "2.0",
      plugins: ["AMap.Driving", "AMap.Geocoder"],
    }).then((AMap: any) => {
      if (!containerRef.current) return; // 组件可能已卸载

      const map = new AMap.Map(containerRef.current, {
        zoom: 14,
        center: currentPosition,
        viewMode: "3D",
      });
      mapRef.current = map;

      // 添加当前位置标记（蓝色脉冲点）
      const currentMarker = new AMap.Marker({
        position: currentPosition,
        content: `<div style="
          width:20px;height:20px;border-radius:50%;
          background:linear-gradient(135deg,#3b82f6,#06b6d4);
          border:3px solid #fff;
          box-shadow:0 0 12px rgba(59,130,246,0.6);
        "></div>`,
        offset: new AMap.Pixel(-10, -10),
      });
      currentMarker.setMap(map);
      markersRef.current.push(currentMarker);

      // 初始化 Driving 插件
      const driving = new AMap.Driving({
        map: map,
        policy: AMap.DrivingPolicy.LEAST_TIME,
        autoFitView: true,
      });
      drivingRef.current = driving;

      console.log("高德地图初始化成功");
    }).catch((e: Error) => {
      console.error("高德地图加载失败:", e);
      initAttemptRef.current = 0; // 重置，允许重试
    });
  }, [amapKey, amapSecret]); // Key变化时重新初始化

  // 清理地图实例
  useEffect(() => {
    return () => {
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, []);

  // 更新地图视图中心和标记（仅当地图已初始化）
  useEffect(() => {
    const map = mapRef.current;
    const AMap = (window as any).AMap;
    if (!map || !AMap) return;

    // 清除旧标记（保留当前位置标记 - index 0）
    while (markersRef.current.length > 1) {
      const m = markersRef.current.pop();
      m.setMap(null);
    }
    // 清除旧的POI标记
    poiMarkersRef.current.forEach(m => m.setMap(null));
    poiMarkersRef.current = [];
    // 清除旧折线
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }
    // 清除 Driving 结果
    if (drivingRef.current) {
      drivingRef.current.clear();
    }

    const centerTarget = destination || origin || currentPosition;
    map.setCenter(centerTarget);

    // 起点标记（绿色）
    if (origin) {
      const originMarker = new AMap.Marker({
        position: origin,
        content: `<div style="
          width:14px;height:14px;border-radius:50%;
          background:#22c55e;border:3px solid #fff;
          box-shadow:0 0 8px rgba(34,197,94,0.5);
        "></div>`,
        offset: new AMap.Pixel(-7, -7),
        label: {
          content: originName || "起点",
          direction: "top",
          offset: new AMap.Pixel(0, -5),
        },
      });
      originMarker.setMap(map);
      markersRef.current.push(originMarker);
    }

    // 目的地标记（红色）
    if (destination) {
      const destMarker = new AMap.Marker({
        position: destination,
        content: `<div style="
          width:14px;height:14px;border-radius:50%;
          background:#ef4444;border:3px solid #fff;
          box-shadow:0 0 8px rgba(239,68,68,0.5);
        "></div>`,
        offset: new AMap.Pixel(-7, -7),
        label: {
          content: destinationName || "目的地",
          direction: "top",
          offset: new AMap.Pixel(0, -5),
        },
      });
      destMarker.setMap(map);
      markersRef.current.push(destMarker);
    }

    // 路线渲染
    if (routeCoords.length > 1) {
      // 如果有起终点，优先用 Driving 插件规划真实路线
      if (origin && destination && drivingRef.current) {
        drivingRef.current.search(
          new AMap.LngLat(origin[1], origin[0]),
          new AMap.LngLat(destination[1], destination[0]),
          (status: string, result: any) => {
            if (status === "complete" && result.routes && result.routes.length > 0) {
              // Driving 已自动在地图上绘制路线
            } else {
              // Driving 失败，用手动折线
              const polyline = new AMap.Polyline({
                path: routeCoords.map((c: [number, number]) => new AMap.LngLat(c[1], c[0])),
                strokeColor: "#3b82f6",
                strokeWeight: 5,
                strokeOpacity: 0.85,
              });
              polyline.setMap(map);
              polylineRef.current = polyline;
            }
          },
        );
      } else {
        // 无起终点或无 Driving，用手动折线
        const polyline = new AMap.Polyline({
          path: routeCoords.map((c: [number, number]) => new AMap.LngLat(c[1], c[0])),
          strokeColor: "#3b82f6",
          strokeWeight: 5,
          strokeOpacity: 0.85,
        });
        polyline.setMap(map);
        polylineRef.current = polyline;
      }
    }

    // POI 标记（橙色）
    pois.forEach((p: { name: string; lat: number; lng: number }) => {
      const poiMarker = new AMap.Marker({
        position: [p.lat, p.lng],
        content: `<div style="
          width:10px;height:10px;border-radius:50%;
          background:#f59e0b;border:2px solid #fff;
          box-shadow:0 0 6px rgba(245,158,11,0.5);
        "></div>`,
        offset: new AMap.Pixel(-5, -5),
        label: {
          content: p.name,
          direction: "top",
          offset: new AMap.Pixel(0, -5),
        },
      });
      poiMarker.setMap(map);
      poiMarkersRef.current.push(poiMarker);
    });

    // 自动调整视野
    if (origin || destination || pois.length > 0) {
      map.setFitView();
    }
  }, [currentPosition, origin, originName, destination, destinationName, routeCoords, pois]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-slate-700/50">
      {/* 高德地图容器 */}
      <div ref={containerRef} className="h-full w-full" />

      {/* Key 未配置时的提示 */}
      {!amapKey || amapKey === "your-amap-js-key-here" ? (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
          <div className="glass-card p-6 text-center">
            <p className="text-sm text-slate-400">地图正在加载...</p>
            <p className="text-xs text-slate-500 mt-2">请确保已配置高德地图 JS API Key</p>
          </div>
        </div>
      ) : null}

      {/* 路线信息卡片 */}
      {routeInfo && (
        <div className="absolute bottom-4 left-4 right-4 z-[1000]">
          <div className="glass-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="flex items-center gap-2 text-sm font-bold text-white">
                <span className="text-blue-400">🧭</span>
                {routeInfo.origin} → {routeInfo.destination}
              </h4>
              <span className="text-xs text-slate-400">
                {routeInfo.distanceKm} km · 约 {routeInfo.durationMin} 分钟
              </span>
            </div>
            <div className="space-y-1">
              {routeInfo.steps.map((s: string, i: number) => (
                <p
                  key={i}
                  className="flex items-start gap-2 text-xs text-slate-400"
                >
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                  {s}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
