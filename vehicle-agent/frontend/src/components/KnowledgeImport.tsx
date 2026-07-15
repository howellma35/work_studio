/**
 * KnowledgeImport — 知识库导入面板
 *
 * 支持拖拽上传文件和内联文本导入到知识库。
 */
import { useState } from "react";

interface KnowledgeImportProps {
  onClose: () => void;
}

export default function KnowledgeImport({ onClose }: KnowledgeImportProps) {
  const [mode, setMode] = useState<"file" | "text">("text");
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleImport = async () => {
    if (!name.trim() || (mode === "text" && !content.trim())) {
      setMessage("请填写名称和内容");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      if (mode === "text") {
        const res = await fetch("/api/vehicle/knowledge/datasets/automind_user_imports/content", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ name, content }),
        });
        const data = await res.json();
        if (data.status === "ok") {
          setMessage("✅ 导入成功！后续可以通过对话检索到这些内容。");
        } else {
          setMessage(`❌ 导入失败: ${data.detail || "未知错误"}`);
        }
      }
    } catch (e) {
      setMessage(`❌ 网络错误: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm z-50">
      <div className="w-[480px] max-h-[80vh] bg-slate-900 border border-slate-700/50 rounded-xl shadow-xl overflow-y-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/40">
          <h3 className="text-base font-semibold text-white">📚 知识库导入</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">✕</button>
        </div>

        {/* 模式切换 */}
        <div className="flex gap-2 px-4 pt-3">
          <button
            onClick={() => setMode("text")}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
              mode === "text" ? "bg-blue-500/20 border border-blue-400/30 text-blue-200" : "bg-slate-800/40 text-slate-400 border border-slate-700/30"
            }`}
          >
            📝 文本导入
          </button>
          <button
            onClick={() => setMode("file")}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
              mode === "file" ? "bg-blue-500/20 border border-blue-400/30 text-blue-200" : "bg-slate-800/40 text-slate-400 border border-slate-700/30"
            }`}
          >
            📁 文件上传
          </button>
        </div>

        {/* 内容区 */}
        <div className="px-4 py-3 space-y-3">
          {mode === "text" ? (
            <>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">文档名称</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="如：我的驾驶技巧"
                  className="w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/40 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-400/50"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">文档内容</label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="输入要导入到知识库的文本内容..."
                  rows={8}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/40 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-400/50 resize-none"
                />
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 border border-dashed border-slate-700/40 rounded-lg text-sm text-slate-500">
              📁 文件上传功能需 RAGFlow API 配置完成后启用
              <span className="text-xs text-slate-600 mt-2">支持 PDF, DOCX, TXT, MD 格式</span>
            </div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={handleImport}
            disabled={loading || mode === "file"}
            className="px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-400/30 text-blue-200 hover:bg-blue-500/30 transition-all text-sm disabled:opacity-50"
          >
            {loading ? "导入中..." : "导入"}
          </button>
          {message && (
            <span className={`text-xs ${message.startsWith("✅") ? "text-green-300" : "text-red-300"}`}>
              {message}
            </span>
          )}
        </div>

        {/* 说明 */}
        <div className="px-4 py-2 border-t border-slate-700/40 text-xs text-slate-500">
          导入的内容会被自动解析和索引，后续对话中提到相关内容时，助手会自动检索并标注来源。
        </div>
      </div>
    </div>
  );
}
