import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

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
  /** 目的地坐标 */
  destination?: [number, number];
  /** 目的地名称 */
  destinationName?: string;
  /** 路线坐标序列 */
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

/* ============ 目的地 → 坐标映射（模拟） ============ */
const DEST_COORDS: Record<string, [number, number]> = {
  公司: [31.2397, 121.4998],
  陆家嘴: [31.2363, 121.5055],
  外滩: [31.24, 121.49],
  南京路: [31.2352, 121.475],
  虹桥机场: [31.198, 121.3363],
  浦东机场: [31.1434, 121.8081],
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
  // 模糊匹配
  for (const [key, coord] of Object.entries(DEST_COORDS)) {
    if (name.includes(key) || key.includes(name)) return coord;
  }
  return [
    current[0] + (Math.random() - 0.5) * 0.04,
    current[1] + (Math.random() - 0.5) * 0.04,
  ];
}

/** 在两点之间生成逼真的折线路径 */
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

/* ==================== 图标 ==================== */
const currentIcon = new L.DivIcon({
  html: `<div style="
    width:20px;height:20px;border-radius:50%;
    background:linear-gradient(135deg,#3b82f6,#06b6d4);
    border:3px solid #fff;
    box-shadow:0 0 12px rgba(59,130,246,0.6);
  "></div>`,
  className: "",
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

const destIcon = new L.DivIcon({
  html: `<div style="
    width:14px;height:14px;border-radius:50%;
    background:#ef4444;border:3px solid #fff;
    box-shadow:0 0 8px rgba(239,68,68,0.5);
  "></div>`,
  className: "",
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const poiIcon = new L.DivIcon({
  html: `<div style="
    width:10px;height:10px;border-radius:50%;
    background:#f59e0b;border:2px solid #fff;
    box-shadow:0 0 6px rgba(245,158,11,0.5);
  "></div>`,
  className: "",
  iconSize: [10, 10],
  iconAnchor: [5, 5],
});

/* ==================== 视角跟随 ==================== */
function MapFollower({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 14, { duration: 1.2 });
  }, [center, map]);
  return null;
}

/* ==================== 主组件 ==================== */
export default function MapPanel({ mapState }: { mapState: MapState }) {
  const {
    currentPosition,
    destination,
    destinationName,
    routeCoords,
    routeInfo,
    pois,
  } = mapState;

  const mapCenter: [number, number] = destination || currentPosition;

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-slate-700/50">
      <MapContainer
        center={currentPosition}
        zoom={14}
        className="h-full w-full"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapFollower center={mapCenter} />

        {/* 当前位置 */}
        <Marker position={currentPosition} icon={currentIcon}>
          <Popup>📍 当前位置</Popup>
        </Marker>

        {/* 目的地 */}
        {destination && (
          <Marker position={destination} icon={destIcon}>
            <Popup>🏁 {destinationName || "目的地"}</Popup>
          </Marker>
        )}

        {/* 路线折线 */}
        {routeCoords.length > 1 && (
          <Polyline
            positions={routeCoords}
            pathOptions={{ color: "#3b82f6", weight: 5, opacity: 0.85 }}
          />
        )}

        {/* POI */}
        {pois.map((p, i) => (
          <Marker key={i} position={[p.lat, p.lng]} icon={poiIcon}>
            <Popup>{p.name}</Popup>
          </Marker>
        ))}
      </MapContainer>

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
              {routeInfo.steps.map((s, i) => (
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
