import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Upload, Trash2, FileText, Loader2, Database, CheckCircle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

interface FileItem {
  file_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  chunk_count: number;
  uploaded_at: string;
}

interface KbDetail {
  id: string;
  name: string;
  description: string;
  files: FileItem[];
  chunk_count: number;
  created_at: string;
}

const SUPPORTED_TYPES = '.pdf,.docx,.txt,.md,.csv,.html,.htm';

export default function KnowledgeDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<KbDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    try {
      const resp = await fetch(`/api/knowledge/${id}`);
      if (resp.ok) {
        const data = await resp.json() as KbDetail;
        setDetail(data);
      } else {
        setError('知识库不存在');
      }
    } catch (err) {
      setError('获取知识库详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length || !id) return;

    setUploading(true);
    setUploadResult(null);
    setError(null);

    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch(`/api/knowledge/${id}/files`, {
        method: 'POST',
        body: formData,
      });

      if (resp.ok) {
        const data = await resp.json() as { chunk_count: number; filename: string };
        setUploadResult(`${data.filename} 已上传，生成 ${data.chunk_count} 个文档块`);
        fetchDetail();
      } else {
        const errData = await resp.json().catch(() => ({}));
        setError((errData as Record<string, string>).detail || '上传失败');
      }
    } catch (err) {
      setError('上传失败，请检查网络连接');
    } finally {
      setUploading(false);
    }
  }, [id, fetchDetail]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt', '.md', '.csv'],
      'text/html': ['.html', '.htm'],
    },
    multiple: false,
    disabled: uploading,
  });

  const deleteFile = async (fileId: string) => {
    if (!id || !confirm('确定要删除此文件吗？')) return;
    try {
      const resp = await fetch(`/api/knowledge/${id}/files/${fileId}`, { method: 'DELETE' });
      if (resp.ok) fetchDetail();
    } catch (err) {
      console.error('Failed to delete file:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--color-accent)]" />
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 text-center">
        <p className="text-[var(--color-danger)]">{error}</p>
        <Link to="/knowledge" className="btn-secondary mt-4 inline-flex">
          <ArrowLeft className="h-4 w-4" /> 返回知识库列表
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
      {/* Header */}
      <div className="mb-6">
        <Link to="/knowledge" className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors mb-3">
          <ArrowLeft className="h-4 w-4" /> 返回知识库列表
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-[var(--color-accent-soft)] flex items-center justify-center">
            <Database className="h-6 w-6 text-[var(--color-accent)]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--color-text)]">{detail?.name || id}</h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {detail?.files.length || 0} 个文件 · {detail?.chunk_count || 0} 个文档块
            </p>
          </div>
        </div>
      </div>

      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`card p-6 mb-6 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]' : 'hover:border-[var(--color-accent)]'}
          ${uploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-[var(--color-accent)]" />
            <p className="text-sm text-[var(--color-text-secondary)]">正在处理文件...</p>
          </div>
        ) : (
          <>
            <Upload className="h-8 w-8 text-[var(--color-text-muted)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-text-secondary)]">
              {isDragActive ? '松开以上传文件' : '拖拽文件到此处，或点击选择文件'}
            </p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              支持: PDF、DOCX、TXT、MD、CSV、HTML
            </p>
          </>
        )}
      </div>

      {/* Status Messages */}
      {uploadResult && (
        <div className="flex items-center gap-2 mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm animate-fade-in">
          <CheckCircle className="h-4 w-4 shrink-0" />
          {uploadResult}
        </div>
      )}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm animate-fade-in">
          {error}
        </div>
      )}

      {/* File List */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border)]">
          <h2 className="font-semibold text-sm">文件列表</h2>
        </div>
        {detail?.files.length ? (
          <div className="divide-y divide-[var(--color-border-light)]">
            {detail.files.map((file) => (
              <div key={file.file_id} className="flex items-center gap-3 px-4 py-3 group">
                <FileText className="h-4 w-4 text-[var(--color-text-muted)] shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--color-text)] truncate">{file.filename}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {file.file_type.toUpperCase()} · {file.chunk_count} 个文档块
                  </p>
                </div>
                <button
                  onClick={() => deleteFile(file.file_id)}
                  className="p-1.5 rounded-lg hover:bg-[var(--color-bg-muted)] text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center">
            <p className="text-sm text-[var(--color-text-muted)]">暂无文件，请上传文档</p>
          </div>
        )}
      </div>
    </div>
  );
}
