import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Plus, Trash2, MessageSquare, Upload, Loader2, X, Database } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { siteConfig } from '../../config/site';

interface KnowledgeBase {
  id: string;
  name: string;
  file_count: number;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

interface Conversation {
  id: string;
  title: string;
  model: string;
  messages: Message[];
  knowledgeFile?: string;
  createdAt: number;
}

const STORAGE_KEY = 'ai_conversations';
const DAILY_LIMIT = 5;

function loadConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch { return []; }
}

function saveConversations(convs: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
}

/** 每日对话次数管理（基于 localStorage，每天重置） */
function getTodayKey() {
  return `ai_chat_count_${new Date().toISOString().slice(0, 10)}`;
}

function getTodayCount(): number {
  return parseInt(localStorage.getItem(getTodayKey()) || '0', 10);
}

function incrementTodayCount(): number {
  const count = getTodayCount() + 1;
  localStorage.setItem(getTodayKey(), String(count));
  return count;
}

export default function AIChat() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(siteConfig.model_options[0]?.id || '');
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null);
  const [selectedKbId, setSelectedKbId] = useState('');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [backendCount, setBackendCount] = useState(getTodayCount);

  // 从后端获取真实计数（防止 localStorage 被清绕过）
  useEffect(() => {
    fetch('/api/ai/chat-count')
      .then(res => res.json())
      .then(data => {
        if (typeof data.used === 'number') {
          setBackendCount(data.used);
        }
      })
      .catch(() => {});
  }, []);

  // 实际计数取后端值（更可靠）
  const actualCount = Math.max(getTodayCount(), backendCount);

  const activeConversation = conversations.find((c) => c.id === activeId) || null;

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages.length]);

  // 获取知识库列表
  useEffect(() => {
    const fetchKbs = async () => {
      try {
        const resp = await fetch('/api/knowledge/');
        if (resp.ok) {
          const data = await resp.json() as KnowledgeBase[];
          setKnowledgeBases(data);
        }
      } catch (err) {
        console.error('Failed to fetch knowledge bases:', err);
      }
    };
    fetchKbs();
  }, []);

  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const createConversation = () => {
    const conv: Conversation = {
      id: crypto.randomUUID(),
      title: '新对话',
      model: selectedModel,
      messages: [],
      createdAt: Date.now(),
    };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setSidebarOpen(false);
  };

  const deleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  };

  const clearAll = () => {
    setConversations([]);
    setActiveId(null);
  };

  const updateMessages = useCallback((convId: string, updater: (msgs: Message[]) => Message[]) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, messages: updater(c.messages) } : c))
    );
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    let convId = activeId;
    if (!convId) {
      const conv: Conversation = {
        id: crypto.randomUUID(),
        title: input.slice(0, 30),
        model: selectedModel,
        messages: [],
        createdAt: Date.now(),
      };
      setConversations((prev) => [conv, ...prev]);
      convId = conv.id;
      setActiveId(convId);
    }

    // 检查每日限制
    if (actualCount >= DAILY_LIMIT) {
      const errMsg: Message = {
        role: 'assistant',
        content: `**今日对话次数已用完** (${DAILY_LIMIT}/${DAILY_LIMIT})\n\n每位用户每天最多 ${DAILY_LIMIT} 次对话，请明天再来吧 🙏`,
        timestamp: Date.now(),
      };
      updateMessages(convId!, (msgs) => [...msgs, errMsg]);
      return;
    }

    setConversations((prev) =>
      prev.map((c) =>
        c.id === convId && c.messages.length === 0
          ? { ...c, title: input.slice(0, 30), model: selectedModel, knowledgeFile: knowledgeFile?.name }
          : c
      )
    );

    const userMsg: Message = { role: 'user', content: input.trim(), timestamp: Date.now() };
    updateMessages(convId, (msgs) => [...msgs, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('message', input.trim());
      formData.append('model', selectedModel);
      if (selectedKbId) formData.append('kb_id', selectedKbId);
      if (knowledgeFile) formData.append('knowledge_file', knowledgeFile);

      const currentConv = conversations.find((c) => c.id === convId);
      const history = currentConv?.messages || [];
      formData.append('history', JSON.stringify(history));

      const resp = await fetch('/api/ai/chat', {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error((errData as Record<string, string>).detail || `请求失败 (${resp.status})`);
      }

      const data = await resp.json() as { reply: string };
      incrementTodayCount(); // 成功回复后才计数
      const remaining = DAILY_LIMIT - getTodayCount();
      let reply = data.reply;
      if (remaining > 0 && remaining <= 2) {
        reply += `\n\n---\n💡 今日剩余对话次数：${remaining}/${DAILY_LIMIT}`;
      } else if (remaining === 0) {
        reply += `\n\n---\n📝 今日对话次数已用完 (${DAILY_LIMIT}/${DAILY_LIMIT})，明天再来吧！`;
      }
      const assistantMsg: Message = { role: 'assistant', content: reply, timestamp: Date.now() };
      updateMessages(convId, (msgs) => [...msgs, assistantMsg]);
    } catch (err) {
      const errMsg: Message = {
        role: 'assistant',
        content: `**错误**: ${err instanceof Error ? err.message : '请求失败，请稍后重试'}`,
        timestamp: Date.now(),
      };
      updateMessages(convId!, (msgs) => [...msgs, errMsg]);
    } finally {
      setLoading(false);
      setKnowledgeFile(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex" style={{ height: 'calc(100vh - 3.5rem)' }}>
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div className="sidebar-backdrop md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar Toggle (Mobile) */}
      <button
        className="md:hidden fixed bottom-20 left-4 z-30 btn-primary !p-3 !rounded-full shadow-lg"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        <MessageSquare className="h-5 w-5" />
      </button>

      {/* Sidebar */}
      <aside className={`
        fixed md:relative inset-y-0 left-0 z-20 w-64 shrink-0
        bg-[var(--color-bg)] border-r border-[var(--color-border)]
        flex flex-col transition-transform duration-200 ease-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `} style={{ top: '3.5rem' }}>
        {/* Sidebar Header */}
        <div className="p-3 border-b border-[var(--color-border)] shrink-0">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-sm">对话列表</h2>
            <div className="flex gap-1">
              <button onClick={clearAll} className="p-1.5 rounded-lg hover:bg-[var(--color-bg-soft)] text-[var(--color-text-muted)] transition-colors" title="清空所有">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <button onClick={createConversation} className="p-1.5 rounded-lg hover:bg-[var(--color-bg-soft)] text-[var(--color-accent)] transition-colors" title="新建对话">
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="select w-full text-xs mb-2"
          >
            {siteConfig.model_options.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.provider})</option>
            ))}
          </select>
          {/* 每日限制提示 */}
          <div className="flex items-center gap-1.5 text-xs px-1 py-1.5 mb-2 rounded-lg bg-[var(--color-bg-soft)]">
            <span className="text-[var(--color-text-secondary)]">💬 今日剩余：</span>
            <span className={`font-semibold ${actualCount >= DAILY_LIMIT ? 'text-red-500' : 'text-[var(--color-accent)]'}`}>
              {DAILY_LIMIT - actualCount}/{DAILY_LIMIT}
            </span>
          </div>
          {knowledgeBases.length > 0 && (
            <select
              value={selectedKbId}
              onChange={(e) => setSelectedKbId(e.target.value)}
              className="select w-full text-xs"
            >
              <option value="">不使用知识库</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>{kb.name} ({kb.file_count} 文件)</option>
              ))}
            </select>
          )}
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => { setActiveId(conv.id); setSidebarOpen(false); }}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors mb-0.5
                ${activeId === conv.id
                  ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-medium'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-soft)]'
                }`}
            >
              <MessageSquare className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1 truncate">{conv.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                className="p-0.5 rounded hover:bg-[var(--color-bg-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-center text-xs text-[var(--color-text-muted)] py-8">暂无对话</p>
          )}
        </div>
      </aside>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {!activeConversation ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-[var(--color-accent-soft)] flex items-center justify-center mb-5">
                <MessageSquare className="h-8 w-8 text-[var(--color-accent)]" />
              </div>
              <h2 className="text-xl font-bold mb-2 text-[var(--color-text)]">AI 对话</h2>
              <p className="text-[var(--color-text-secondary)] max-w-sm text-sm">
                选择或新建对话，与 AI 大模型进行智能对话。支持上传知识库文件进行 RAG 问答。
              </p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {activeConversation.messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                  <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3
                    ${msg.role === 'user'
                      ? 'bg-[var(--color-accent)] text-white rounded-br-sm'
                      : 'bg-[var(--color-bg-soft)] border border-[var(--color-border)] rounded-bl-sm'
                    }`}>
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none
                        prose-p:my-1.5
                        prose-headings:mt-3 prose-headings:mb-1.5
                        prose-code:text-[var(--color-accent)] prose-code:bg-[var(--color-bg-muted)] prose-code:px-1 prose-code:rounded
                        prose-pre:bg-[var(--color-bg-muted)] prose-pre:border prose-pre:border-[var(--color-border)] prose-pre:rounded-lg prose-pre:my-2
                      ">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start animate-fade-in">
                  <div className="bg-[var(--color-bg-soft)] border border-[var(--color-border)] rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-[var(--color-accent)]" />
                      <span className="text-sm text-[var(--color-text-secondary)]">思考中...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-bg)] p-4 sm:px-8">
          <div className="max-w-3xl mx-auto">
            {(selectedKbId || knowledgeFile) && (
              <div className="flex items-center gap-3 mb-2 text-xs text-[var(--color-accent)]">
                {selectedKbId && (
                  <span className="flex items-center gap-1">
                    <Database className="h-3.5 w-3.5" />
                    RAG: {knowledgeBases.find(kb => kb.id === selectedKbId)?.name || selectedKbId}
                  </span>
                )}
                {knowledgeFile && (
                  <span className="flex items-center gap-1">
                    <Upload className="h-3.5 w-3.5" />
                    文件: {knowledgeFile.name}
                    <button onClick={() => setKnowledgeFile(null)} className="p-0.5 hover:bg-[var(--color-bg-soft)] rounded transition-colors">
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
              </div>
            )}
            <div className="flex items-end gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                onChange={(e) => setKnowledgeFile(e.target.files?.[0] || null)}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="p-2.5 rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] hover:border-[var(--color-accent)] transition-colors shrink-0"
                title="上传知识库文件"
              >
                <Upload className="h-5 w-5" />
              </button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... (Shift+Enter 换行)"
                rows={1}
                className="input flex-1 resize-none !py-2.5 leading-relaxed"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="btn-primary !p-2.5 !rounded-xl shrink-0 disabled:!opacity-40"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
