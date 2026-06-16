import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { ArrowLeft, Upload, FileText, Download, Loader2, AlertCircle, Check } from 'lucide-react';

type ExportFormat = 'txt' | 'md' | 'json';
type ParseStatus = 'idle' | 'uploading' | 'parsing' | 'done' | 'error';

interface ParseResult {
  fileName: string;
  pages: number;
  text: string;
  metadata: Record<string, string>;
}

export default function PdfParser() {
  const [status, setStatus] = useState<ParseStatus>('idle');
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState('');
  const [exportFormat, setExportFormat] = useState<ExportFormat>('txt');
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setError('请上传 PDF 格式文件');
      setStatus('error');
      return;
    }

    setError('');
    setStatus('uploading');

    // Create preview URL
    const url = URL.createObjectURL(file);
    setFilePreviewUrl(url);

    // Upload and parse
    setStatus('parsing');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch('/api/pdf/parse', {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error((errData as Record<string, string>).detail || `解析失败 (${resp.status})`);
      }

      const data = await resp.json() as ParseResult;
      setResult(data);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : '解析失败，请重试');
      setStatus('error');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleExport = () => {
    if (!result) return;

    let content: string;
    let mimeType: string;
    let ext: string;

    switch (exportFormat) {
      case 'md':
        content = `# ${result.fileName}\n\n> 共 ${result.pages} 页\n\n${result.text}`;
        mimeType = 'text/markdown';
        ext = 'md';
        break;
      case 'json':
        content = JSON.stringify(result, null, 2);
        mimeType = 'application/json';
        ext = 'json';
        break;
      default:
        content = result.text;
        mimeType = 'text/plain';
        ext = 'txt';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.fileName.replace('.pdf', '')}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <Link
        to="/tools"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] mb-8 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> 返回工具列表
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
          PDF 解析工具
        </h1>
        <p className="text-[var(--color-text-secondary)]">上传 PDF 文件，提取文本内容，支持多格式导出</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: Upload + Preview */}
        <div className="flex flex-col gap-4">
          {/* Drop Zone */}
          <div
            {...getRootProps()}
            className={`glass-card p-8 text-center cursor-pointer transition-all border-2 border-dashed
              ${isDragActive ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5' : 'border-white/10 hover:border-white/20'}`}
          >
            <input {...getInputProps()} />
            <Upload className={`h-12 w-12 mx-auto mb-4 ${isDragActive ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-secondary)]'}`} />
            {isDragActive ? (
              <p className="text-[var(--color-accent-light)] font-medium">松开以上传文件</p>
            ) : (
              <>
                <p className="text-[var(--color-text-primary)] font-medium mb-1">拖拽 PDF 文件到此处</p>
                <p className="text-sm text-[var(--color-text-secondary)]">或点击选择文件（最大 50MB）</p>
              </>
            )}
          </div>

          {/* Preview */}
          {filePreviewUrl && (
            <div className="glass-card flex-1 min-h-[300px] overflow-hidden">
              <iframe
                src={filePreviewUrl}
                className="w-full h-full min-h-[400px]"
                title="PDF Preview"
              />
            </div>
          )}
        </div>

        {/* Right: Results */}
        <div className="flex flex-col gap-4">
          {/* Status */}
          {status === 'parsing' && (
            <div className="glass-card p-6 flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-[var(--color-accent-light)]" />
              <span className="text-[var(--color-text-secondary)]">正在解析文件...</span>
            </div>
          )}

          {status === 'error' && (
            <div className="glass-card p-6 flex items-start gap-3 border border-[var(--color-danger)]/30">
              <AlertCircle className="h-5 w-5 text-[var(--color-danger)] flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-[var(--color-danger)] font-medium">解析失败</p>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">{error}</p>
              </div>
            </div>
          )}

          {status === 'done' && result && (
            <>
              {/* Info */}
              <div className="glass-card p-4 flex items-center gap-3">
                <Check className="h-5 w-5 text-[var(--color-success)]" />
                <div>
                  <p className="font-medium">{result.fileName}</p>
                  <p className="text-sm text-[var(--color-text-secondary)]">共 {result.pages} 页</p>
                </div>
              </div>

              {/* Export Controls */}
              <div className="flex items-center gap-3">
                <div className="flex gap-1 bg-white/5 rounded-lg p-1 border border-white/10">
                  {(['txt', 'md', 'json'] as ExportFormat[]).map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => setExportFormat(fmt)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all
                        ${exportFormat === fmt ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
                    >
                      {fmt.toUpperCase()}
                    </button>
                  ))}
                </div>
                <button onClick={handleExport} className="btn-primary flex items-center gap-2 text-sm px-4 py-2">
                  <Download className="h-4 w-4" />
                  导出文件
                </button>
              </div>

              {/* Text Content */}
              <div className="glass-card p-4 flex-1 min-h-[300px] overflow-auto">
                <div className="flex items-center gap-2 mb-3 text-sm text-[var(--color-text-secondary)]">
                  <FileText className="h-4 w-4" />
                  提取内容
                </div>
                <pre className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap leading-relaxed font-sans">
                  {result.text}
                </pre>
              </div>
            </>
          )}

          {status === 'idle' && (
            <div className="glass-card p-8 flex flex-col items-center justify-center text-center flex-1 min-h-[300px]">
              <FileText className="h-16 w-16 text-[var(--color-text-secondary)] opacity-20 mb-4" />
              <p className="text-[var(--color-text-secondary)]">上传 PDF 文件后，解析结果将显示在这里</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
