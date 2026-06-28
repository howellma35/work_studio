import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Database, Plus, Trash2, FileText, Loader2 } from 'lucide-react';

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  file_count: number;
  chunk_count: number;
  created_at: string;
}

export default function KnowledgeList() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const fetchKbs = async () => {
    try {
      const resp = await fetch('/api/knowledge/');
      if (resp.ok) {
        const data = await resp.json() as KnowledgeBase[];
        setKbs(data);
      }
    } catch (err) {
      console.error('Failed to fetch knowledge bases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKbs(); }, []);

  const createKb = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const resp = await fetch('/api/knowledge/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), description: newDesc.trim() }),
      });
      if (resp.ok) {
        setNewName('');
        setNewDesc('');
        setShowCreate(false);
        fetchKbs();
      }
    } catch (err) {
      console.error('Failed to create knowledge base:', err);
    } finally {
      setCreating(false);
    }
  };

  const deleteKb = async (id: string) => {
    if (!confirm('确定要删除此知识库及其所有数据吗？')) return;
    try {
      const resp = await fetch(`/api/knowledge/${id}`, { method: 'DELETE' });
      if (resp.ok) fetchKbs();
    } catch (err) {
      console.error('Failed to delete knowledge base:', err);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]">知识库</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            上传文档构建知识库，AI 对话时自动检索相关内容
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4" />
          新建知识库
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="card p-5 mb-6 animate-fade-in">
          <h3 className="font-semibold text-sm mb-3">新建知识库</h3>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="知识库名称"
            className="input mb-2"
            autoFocus
          />
          <input
            type="text"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="描述（可选）"
            className="input mb-3"
          />
          <div className="flex gap-2">
            <button onClick={createKb} disabled={creating || !newName.trim()} className="btn-primary">
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              创建
            </button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">
              取消
            </button>
          </div>
        </div>
      )}

      {/* Knowledge Base List */}
      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--color-accent)] mx-auto" />
        </div>
      ) : kbs.length === 0 ? (
        <div className="text-center py-16">
          <Database className="h-12 w-12 text-[var(--color-text-muted)] mx-auto mb-4" />
          <p className="text-[var(--color-text-secondary)]">暂无知识库</p>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            点击右上角「新建知识库」开始
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {kbs.map((kb) => (
            <Link
              key={kb.id}
              to={`/knowledge/${kb.id}`}
              className="card card-hover p-5 group relative"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-[var(--color-accent-soft)] flex items-center justify-center shrink-0">
                  <Database className="h-5 w-5 text-[var(--color-accent)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-[var(--color-text)] truncate">{kb.name}</h3>
                  {kb.description && (
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 line-clamp-2">
                      {kb.description}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-[var(--color-text-muted)]">
                    <span className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      {kb.file_count} 个文件
                    </span>
                    <span>{kb.chunk_count} 个文档块</span>
                  </div>
                </div>
              </div>
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); deleteKb(kb.id); }}
                className="absolute top-3 right-3 p-1.5 rounded-lg hover:bg-[var(--color-bg-muted)] text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
