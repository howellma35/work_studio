import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Plus, Trash2, MessageSquare, Upload, Loader2, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { siteConfig } from '../../config/site';

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

function loadConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch { return []; }
}

function saveConversations(convs: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
}

export default function AIChat() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(siteConfig.model_options[0]?.id || '');
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeConversation = conversations.find((c) => c.id === activeId) || null;

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages.length]);

  // Auto-resize textarea
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
      const assistantMsg: Message = { role: 'assistant', content: data.reply, timestamp: Date.now() };
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
    <div className="flex h-full" style={{ height: 'calc(100vh - 4rem)' }}>
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div className="sidebar-backdrop md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar Toggle (Mobile) */}
      <button
        className="md:hidden fixed bottom-20 left-4 z-30 btn-primary !p-3 !rounded-full shadow-xl"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        <MessageSquare className="h-5 w-5" />
      </button>

      {/* Sidebar */}
      <aside className={`
        fixed md:relative inset-y-0 left-0 z-20 w-72 flex-shrink-0
        bg-[var(--color-bg-primary)]/95 backdrop-blur-xl border-r border-white/10
        flex flex-col transition-transform duration-200 ease-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `} style={{ top: '4rem' }}>
        <div className="p-4 border-b border-white/10 flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-base">对话列表</h2>
            <div className="flex gap-1">
              <button onClick={clearAll} className="p-1.5 rounded-lg hover:bg-white/5 text-[var(--color-text-secondary)] transition-colors" title="清空所有">
                <Trash2 className="h-4 w-4" />
              </button>
              <button onClick={createConversation} className="p-1.5 rounded-lg hover:bg-white/5 text-[var(--color-accent-light)] transition-colors" title="新建对话">
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]/50 transition-colors"
          >
            {siteConfig.model_options.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.provider})</option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => { setActiveId(conv.id); setSidebarOpen(false); }}
              className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-all mb-1
                ${activeId === conv.id ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent-light)]' : 'text-[var(--color-text-secondary)] hover:bg-white/5 hover:text-[var(--color-text-primary)]'}`}
            >
              <MessageSquare className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1 truncate">{conv.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                className="p-0.5 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-secondary)] py-8 opacity-50">暂无对话</p>
          )}
        </div>
      </aside>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {!activeConversation ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-400/20 flex items-center justify-center mb-6">
                <MessageSquare className="h-10 w-10 text-[var(--color-accent-light)]" />
              </div>
              <h2 className="text-2xl font-bold mb-3 text-[var(--color-text-primary)]">AI 前沿探索</h2>
              <p className="text-[var(--color-text-secondary)] max-w-md leading-relaxed">
                选择或新建对话，与 AI 大模型进行智能对话。<br />支持上传知识库文件进行 RAG 问答。
              </p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-5">
              {activeConversation.messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-in`}>
                  <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3
                    ${msg.role === 'user'
                      ? 'bg-[var(--color-accent)] text-white rounded-br-sm'
                      : 'glass-card rounded-bl-sm'
                    }`}>
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-invert prose-sm max-w-none
                        prose-p:my-1.5 prose-p:text-[var(--color-text-primary)]
                        prose-headings:mt-3 prose-headings:mb-1.5
                        prose-code:text-[var(--color-accent-light)] prose-code:bg-white/5 prose-code:px-1 prose-code:rounded
                        prose-pre:bg-[var(--color-bg-secondary)] prose-pre:border prose-pre:border-white/10 prose-pre:rounded-lg prose-pre:my-2
                        prose-ul:my-1.5 prose-ol:my-1.5
                        prose-li:text-[var(--color-text-secondary)]
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
                <div className="flex justify-start animate-slide-in">
                  <div className="glass-card rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-[var(--color-accent-light)]" />
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
        <div className="flex-shrink-0 border-t border-white/10 bg-[var(--color-bg-primary)]/50 backdrop-blur-sm p-4 sm:px-8">
          <div className="max-w-3xl mx-auto">
            {knowledgeFile && (
              <div className="flex items-center gap-2 mb-2 text-xs text-[var(--color-accent-light)]">
                <Upload className="h-3.5 w-3.5" />
                <span>知识库: {knowledgeFile.name}</span>
                <button onClick={() => setKnowledgeFile(null)} className="p-0.5 hover:bg-white/10 rounded transition-colors">
                  <X className="h-3 w-3" />
                </button>
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
                className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] hover:border-[var(--color-accent)]/30 transition-all flex-shrink-0"
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
                className="flex-1 resize-none rounded-xl bg-white/5 border border-white/10 px-4 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]/50 placeholder:text-[var(--color-text-secondary)]/40 transition-colors leading-relaxed"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="btn-primary !p-2.5 !rounded-xl flex-shrink-0 disabled:!opacity-40"
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
