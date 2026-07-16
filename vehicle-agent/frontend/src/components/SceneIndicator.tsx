/**
 * 驾驶场景指示器组件
 *
 * 显示当前驾驶场景（待机/市区行驶/高速行驶/停车/紧急）
 * 根据场景等级动态切换样式和动画
 */
import { useState, useEffect } from "react";

// 场景类型定义
interface SceneInfo {
  scene: string;
  label: string;
  icon: string;
  safety_level: string;
  max_response_words: number;
}

// 安全等级对应的样式映射
const SAFETY_STYLES: Record<string, { bg: string; border: string; text: string; pulse: boolean }> = {
  low:      { bg: "bg-slate-800/60",  border: "border-slate-600/40", text: "text-slate-300", pulse: false },
  medium:   { bg: "bg-yellow-500/10", border: "border-yellow-500/40", text: "text-yellow-300", pulse: false },
  high:     { bg: "bg-orange-500/15", border: "border-orange-500/40", text: "text-orange-300", pulse: true },
  critical: { bg: "bg-red-500/20",    border: "border-red-500/50",   text: "text-red-300",   pulse: true },
};

export default function SceneIndicator() {
  const [sceneInfo, setSceneInfo] = useState<SceneInfo>({
    scene: "idle",
    label: "待机",
    icon: "🅿️",
    safety_level: "low",
    max_response_words: 100,
  });
  const [allScenes, setAllScenes] = useState<Record<string, SceneInfo>>({});
  const [changing, setChanging] = useState(false);

  // 从后端获取场景信息
  useEffect(() => {
    fetch("/api/vehicle/agent-info")
      .then((res) => res.json())
      .then((data) => {
        if (data.driving_scenes) {
          setAllScenes(data.driving_scenes);
          setSceneInfo(data.driving_scenes.idle || data.driving_scenes[Object.keys(data.driving_scenes)[0]]);
        }
      })
      .catch(() => {});
  }, []);

  // 模拟场景切换（开发演示用，后续替换为 WebSocket 实时推送）
  // 用户可点击切换不同场景来体验场景化行为差异
  const handleSceneSwitch = (sceneKey: string) => {
    if (sceneKey === sceneInfo.scene) return;
    const newScene = allScenes[sceneKey];
    if (!newScene) return;
    setChanging(true);
    setTimeout(() => {
      setSceneInfo(newScene);
      setChanging(false);
    }, 300);
  };

  const style = SAFETY_STYLES[sceneInfo.safety_level] || SAFETY_STYLES.low;

  return (
    <div className="flex flex-col gap-2">
      {/* 当前场景卡片 */}
      <div
        className={`glass-card px-4 py-2.5 flex items-center gap-3 transition-all duration-300 ${style.bg} ${style.border} border ${
          changing ? "scale-95 opacity-60" : "scale-100 opacity-100"
        } ${sceneInfo.safety_level === "critical" ? "animate-pulse-subtle" : ""}`}
      >
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
          sceneInfo.safety_level === "critical"
            ? "bg-red-500/30 glow-red"
            : sceneInfo.safety_level === "high"
              ? "bg-orange-500/20 glow-orange"
              : "bg-blue-500/20 glow-blue"
        }`}>
          <span className="text-sm">{sceneInfo.icon}</span>
        </div>
        <div className="flex-1">
          <p className={`text-sm font-bold ${style.text}`}>
            {sceneInfo.label}
          </p>
          <p className="text-[10px] text-slate-500">
            最大回复 {sceneInfo.max_response_words} 字 · 安全等级 {sceneInfo.safety_level}
          </p>
        </div>
        {style.pulse && (
          <span className={`h-2 w-2 rounded-full ${
            sceneInfo.safety_level === "critical" ? "bg-red-400 animate-pulse" : "bg-orange-400 animate-pulse"
          }`} />
        )}
      </div>

      {/* 场景快速切换（开发演示） */}
      <div className="flex gap-1.5">
        {Object.entries(allScenes).map(([key, info]) => (
          <button
            key={key}
            className={`rounded-lg px-2 py-1 text-[10px] transition-all ${
              key === sceneInfo.scene
                ? `${SAFETY_STYLES[info.safety_level].bg} ${SAFETY_STYLES[info.safety_level].border} border ${SAFETY_STYLES[info.safety_level].text} font-bold`
                : "bg-slate-800/40 text-slate-500 hover:bg-slate-700/60 hover:text-slate-300"
            }`}
            onClick={() => handleSceneSwitch(key)}
            title={`切换到${info.label}场景`}
          >
            {info.icon} {info.label}
          </button>
        ))}
      </div>
    </div>
  );
}
