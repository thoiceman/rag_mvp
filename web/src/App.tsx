import React, { useState, useEffect, useRef } from 'react';
import { Layout, MessageSquare, Database, Settings, Plus, Trash2, Send, Paperclip, Clock, AlertCircle, CheckCircle2, Loader2, Play, Bot, UserCircle2, Sparkles, MoreHorizontal } from 'lucide-react';
import { agentApi, fileApi, chatApi, indexApi } from './services/api';
import type { Agent, Message, FileMeta, Session } from './types';

type ConfirmDialogConfig = {
  title: string;
  description: string;
  confirmText?: string;
  danger?: boolean;
  onConfirm: () => void | Promise<void>;
};

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'knowledge' | 'settings'>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<FileMeta[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);

  // UI 增强状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: '', description: '', system_prompt: '你是一个专业的助手。' });
  const [editAgent, setEditAgent] = useState<Partial<Agent>>({});
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingTarget, setIndexingTarget] = useState<string | 'all' | null>(null);
  const [indexingProgress, setIndexingProgress] = useState<number>(0);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string, type: 'success' | 'error' | 'info' } | null>(null);
  const [showChatActions, setShowChatActions] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogConfig | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const chatActionsRef = useRef<HTMLDivElement | null>(null);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const formatTime = (time: string) => {
    try {
      return new Date(time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const requestConfirm = (config: ConfirmDialogConfig) => {
    setConfirmDialog(config);
  };

  const runConfirmedAction = async () => {
    if (!confirmDialog) return;
    const action = confirmDialog.onConfirm;
    setConfirmDialog(null);
    await action();
  };

  // 初始化获取 Agents
  const fetchAgents = async () => {
    try {
      const res = await agentApi.list();
      setAgents(res.data);
      if (res.data.length > 0 && !selectedAgentId) {
        setSelectedAgentId(res.data[0].agent_id);
      }
      return res.data;
    } catch (err) {
      showToast('获取 Agent 列表失败', 'error');
      return [];
    }
  };

  const fetchFiles = async (agentId: string) => {
    try {
      const res = await fileApi.list(agentId);
      setFiles(res.data);
    } catch (err) {
      showToast('获取文件列表失败', 'error');
    }
  };

  const fetchSessions = async (agentId: string) => {
    try {
      const res = await chatApi.listSessions(agentId);
      setSessions(res.data);
      return res.data;
    } catch (err) {
      showToast('获取会话列表失败', 'error');
      return [];
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  useEffect(() => {
    if (activeTab !== 'chat') return;
    messageEndRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, activeTab, sessionId]);

  useEffect(() => {
    const onPointerDownOutside = (event: MouseEvent) => {
      if (!showChatActions) return;
      const target = event.target as Node;
      if (!chatActionsRef.current?.contains(target)) {
        setShowChatActions(false);
      }
    };

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowChatActions(false);
      }
    };

    document.addEventListener('mousedown', onPointerDownOutside);
    document.addEventListener('keydown', onEscape);
    return () => {
      document.removeEventListener('mousedown', onPointerDownOutside);
      document.removeEventListener('keydown', onEscape);
    };
  }, [showChatActions]);

  // 切换 Agent 时加载文件和会话，并同步编辑状态
  useEffect(() => {
    if (selectedAgentId) {
      const agent = agents.find(a => a.agent_id === selectedAgentId);
      if (agent) setEditAgent(agent);

      fetchFiles(selectedAgentId);
      fetchSessions(selectedAgentId).then(sessionList => {
        if (sessionList.length > 0) {
          // 默认加载最新会话
          const latest = sessionList[0];
          setSessionId(latest.session_id);
          setMessages(latest.messages || []);
        } else {
          // 如果没有会话，创建一个
          chatApi.createSession(selectedAgentId).then(res => {
            setSessionId(res.data.session_id);
            setMessages([]);
            fetchSessions(selectedAgentId);
          }).catch(() => showToast('创建会话失败', 'error'));
        }
      });
    }
  }, [selectedAgentId]);

  const handleCreateAgent = async () => {
    if (!newAgent.name.trim()) return;
    try {
      await agentApi.create(newAgent.name, newAgent.system_prompt, newAgent.description);
      setShowCreateModal(false);
      setNewAgent({ name: '', description: '', system_prompt: '你是一个专业的助手。' });
      const updatedAgents = await fetchAgents();
      if (updatedAgents.length > 0) {
        setSelectedAgentId(updatedAgents[0].agent_id);
      }
      showToast('创建成功', 'success');
    } catch (err) {
      showToast('创建失败', 'error');
    }
  };

  const handleDeleteAgent = async (id: string) => {
    requestConfirm({
      title: '删除 Agent',
      description: '确定要删除这个 Agent 吗？这将同时删除所有相关资料和对话。',
      confirmText: '确认删除',
      danger: true,
      onConfirm: async () => {
        try {
          await agentApi.delete(id);
          const updatedAgents = await fetchAgents();
          if (updatedAgents.length > 0) {
            setSelectedAgentId(updatedAgents[0].agent_id);
          } else {
            setSelectedAgentId(null);
          }
          showToast('删除成功', 'success');
        } catch (err) {
          showToast('删除失败', 'error');
        }
      },
    });
  };

  const handleUpdateAgent = async () => {
    if (!selectedAgentId || !editAgent.name?.trim()) return;
    try {
      await agentApi.update(selectedAgentId, {
        name: editAgent.name,
        description: editAgent.description,
        system_prompt: editAgent.system_prompt,
      });
      showToast('保存成功', 'success');
      fetchAgents();
    } catch (err) {
      showToast('保存失败', 'error');
    }
  };

  const startNewSession = async () => {
    if (!selectedAgentId) return;
    try {
      const res = await chatApi.createSession(selectedAgentId);
      setSessionId(res.data.session_id);
      setMessages([]);
      fetchSessions(selectedAgentId);
      showToast('已开启新会话', 'success');
    } catch (err) {
      showToast('创建新会话失败', 'error');
    }
  };

  const handleSwitchSession = async (sId: string) => {
    try {
      const res = await chatApi.getSession(sId);
      setSessionId(res.data.session_id);
      setMessages(res.data.messages || []);
    } catch (err) {
      showToast('加载会话失败', 'error');
    }
  };

  const handleDeleteSession = async (targetSessionId: string) => {
    if (!selectedAgentId) return;
    requestConfirm({
      title: '删除历史会话',
      description: '确定要删除这个历史会话吗？',
      confirmText: '确认删除',
      danger: true,
      onConfirm: async () => {
        try {
          await chatApi.deleteSession(targetSessionId);
          const updatedSessions = await fetchSessions(selectedAgentId);

          if (sessionId === targetSessionId) {
            if (updatedSessions.length > 0) {
              const nextSession = updatedSessions[0];
              setSessionId(nextSession.session_id);
              setMessages(nextSession.messages || []);
            } else {
              const res = await chatApi.createSession(selectedAgentId);
              setSessionId(res.data.session_id);
              setMessages([]);
              await fetchSessions(selectedAgentId);
            }
          }
          showToast('会话已删除', 'success');
        } catch (err) {
          showToast('删除会话失败', 'error');
        }
      },
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAgentId) return;

    try {
      setUploadProgress(0);
      await fileApi.upload(selectedAgentId, file, (percent) => {
        setUploadProgress(percent);
      });
      showToast('上传成功', 'success');
      fetchFiles(selectedAgentId);
      e.target.value = ''; // 清除选择
    } catch (err) {
      showToast('上传失败', 'error');
    } finally {
      setTimeout(() => setUploadProgress(null), 1000);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!selectedAgentId) return;
    requestConfirm({
      title: '删除文件',
      description: '确定要删除该文件及对应的索引吗？',
      confirmText: '确认删除',
      danger: true,
      onConfirm: async () => {
        try {
          await fileApi.delete(selectedAgentId, fileId);
          showToast('文件已删除', 'success');
          fetchFiles(selectedAgentId);
        } catch (err) {
          showToast('删除失败', 'error');
        }
      },
    });
  };

  const handleStartIndexing = async (fileId?: string) => {
    if (!selectedAgentId) return;
    setIsIndexing(true);
    setIndexingTarget(fileId || 'all');
    setIndexingProgress(0);
    try {
      const response = await indexApi.build(selectedAgentId, fileId);
      if (!response.ok) throw new Error('网络请求失败');
      
      const reader = response.body?.getReader();
      if (!reader) return;
      
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === 'progress') {
              setIndexingProgress(data.percent);
            } else if (data.type === 'result') {
              if (data.data.status === 'no_new_files') {
                showToast('没有新的未索引文件', 'info');
              } else {
                showToast(`向量化完成：新增文件数 ${data.data.indexed_files}，切片数 ${data.data.indexed_chunks}`, 'success');
              }
            } else if (data.type === 'error') {
              showToast(data.message || '向量化失败', 'error');
            }
          } catch (e) {
            console.error('解析流数据失败:', e, line);
          }
        }
      }
      fetchFiles(selectedAgentId);
    } catch (err) {
      showToast('向量化失败', 'error');
    } finally {
      setIsIndexing(false);
      setIndexingTarget(null);
      setIndexingProgress(0);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedAgentId || !sessionId) return;

    const userMsg: Message = { role: 'user', content: input, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    try {
      const response = await chatApi.chatStream(selectedAgentId, sessionId, input);
      if (!response.ok) throw new Error('网络请求失败');
      
      const reader = response.body?.getReader();
      if (!reader) return;

      let assistantMsg: Message = { role: 'assistant', content: '', created_at: new Date().toISOString(), references: [] };
      setMessages(prev => [...prev, assistantMsg]);

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保持最后一行不完整的部分在 buffer 中
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === 'metadata') {
              assistantMsg.references = data.references || [];
              setMessages(prev => [...prev.slice(0, -1), { ...assistantMsg }]);
            } else if (data.type === 'content') {
              assistantMsg.content += data.content;
              setMessages(prev => [...prev.slice(0, -1), { ...assistantMsg }]);
            }
          } catch (e) {
            console.error('解析流数据失败:', e, line);
          }
        }
      }
    } catch (err) {
      showToast('消息发送失败', 'error');
    }
  };

  const currentAgent = agents.find(a => a.agent_id === selectedAgentId);

  return (
    <div className="flex h-screen bg-background text-slate-900 overflow-hidden relative">
      {/* Toast 通知 */}
      {toast && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-300 ${
          toast.type === 'error' ? 'bg-red-500 text-white' : 
          toast.type === 'success' ? 'bg-accent text-white' : 'bg-slate-800 text-white'
        }`}>
          {toast.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* 侧边栏 */}
      <div className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Layout className="w-6 h-6 text-primary" />
            RAG_MVP
          </h1>
        </div>
        
        <div className="flex-1 overflow-y-auto app-scrollbar p-4 space-y-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2">
            Agents
          </div>
          {agents.map(agent => (
            <div key={agent.agent_id} className="group relative">
              <button
                onClick={() => setSelectedAgentId(agent.agent_id)}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                  selectedAgentId === agent.agent_id ? 'bg-primary text-white' : 'hover:bg-slate-800 text-slate-400'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${agent.knowledge_status === 'indexed' ? 'bg-accent' : 'bg-secondary'}`} />
                <span className="truncate flex-1">{agent.name}</span>
              </button>
              {selectedAgentId === agent.agent_id && (
                <button 
                  onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.agent_id); }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}
          <button 
            onClick={() => setShowCreateModal(true)}
            className="w-full mt-4 flex items-center gap-2 px-4 py-2 border border-dashed border-slate-700 rounded-lg text-slate-500 hover:text-white hover:border-white transition-all"
          >
            <Plus className="w-4 h-4" /> 新建 Agent
          </button>

          {/* 历史会话列表 */}
          {selectedAgentId && (
            <div className="mt-8">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Clock className="w-3 h-3" /> 历史会话
                </span>
                <button
                  onClick={startNewSession}
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
                  title="新建会话"
                >
                  <Plus className="w-3 h-3" />
                  新建
                </button>
              </div>
              {sessions.length > 0 ? (
                <div className="space-y-1">
                  {sessions.map(s => (
                    <div key={s.session_id} className="group relative">
                      <button
                        onClick={() => handleSwitchSession(s.session_id)}
                        className={`w-full text-left px-4 py-2 rounded-lg text-sm transition-colors truncate pr-10 ${
                          sessionId === s.session_id ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
                        }`}
                      >
                        {s.title || '新会话'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(s.session_id);
                        }}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-colors ${
                          sessionId === s.session_id
                            ? 'text-slate-300 hover:text-red-300 hover:bg-slate-700'
                            : 'text-slate-500 hover:text-red-400 hover:bg-slate-800 opacity-0 group-hover:opacity-100'
                        }`}
                        title="删除会话"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-2 py-3 text-xs text-slate-500">暂无历史会话</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 主工作区 */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-white">
        {/* Header */}
        <header className="h-16 border-b flex items-center justify-between px-8 bg-white/50 backdrop-blur-md sticky top-0 z-10">
          <div>
            <h2 className="text-lg font-semibold">{currentAgent?.name || '请选择 Agent'}</h2>
            <p className="text-xs text-slate-500 truncate max-w-[200px]">{currentAgent?.description}</p>
          </div>
          
          <div className="flex bg-slate-100 p-1 rounded-xl">
            {[
              { id: 'chat', icon: MessageSquare, label: '对话' },
              { id: 'knowledge', icon: Database, label: '知识库' },
              { id: 'settings', icon: Settings, label: '设置' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id ? 'bg-white shadow-sm text-primary' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <tab.icon className="w-4 h-4" /> {tab.label}
              </button>
            ))}
          </div>
        </header>

        {/* 内容区 */}
        <main className="flex-1 min-h-0 overflow-hidden relative">
          {activeTab === 'chat' && (
            <div className="h-full min-h-0 flex flex-col max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between gap-4 py-4">
                <div className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  <Sparkles className="w-3.5 h-3.5" />
                  智能对话
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-xs text-slate-500">共 {messages.length} 条消息</div>
                  <div className="relative" ref={chatActionsRef}>
                    <button
                      onClick={() => setShowChatActions((prev) => !prev)}
                      className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors"
                      title="更多操作"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                    {showChatActions && (
                      <div className="absolute right-0 top-9 w-36 bg-white border border-slate-200 rounded-xl shadow-lg p-1.5 z-20">
                        <button
                          onClick={() => {
                            setShowChatActions(false);
                            requestConfirm({
                              title: '清空历史消息',
                              description: '确定清空当前会话消息吗？',
                              confirmText: '确认清空',
                              danger: true,
                              onConfirm: () => {
                                setMessages([]);
                              },
                            });
                          }}
                          className="w-full flex items-center gap-2 px-2.5 py-2 text-sm rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                          清空历史
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-y-auto app-scrollbar scroll-smooth mt-2 px-4 sm:px-6 pt-6 pb-20 space-y-6 rounded-[28px] border border-slate-200/80 bg-gradient-to-b from-slate-50 via-white to-white shadow-inner">
                {messages.length === 0 && (
                  <div className="h-full flex items-center justify-center">
                    <div className="max-w-md text-center p-8 rounded-3xl border border-slate-200 bg-white shadow-sm">
                      <div className="mx-auto w-14 h-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-4">
                        <MessageSquare className="w-7 h-7" />
                      </div>
                      <p className="text-base font-semibold text-slate-700">开始与 {currentAgent?.name} 对话吧</p>
                      <p className="text-sm text-slate-500 mt-2">你可以提问、追问，或让它基于知识库总结要点。</p>
                    </div>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={i} className={`flex items-end gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center shadow-sm shrink-0">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div className={`max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                      <div className={`rounded-2xl px-4 py-3 shadow-sm border ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-br from-primary to-blue-500 text-white rounded-br-md border-primary/40'
                          : 'bg-white text-slate-800 rounded-bl-md border-slate-200'
                      }`}>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400 px-1">
                        {msg.role === 'user' ? '你' : (currentAgent?.name || '助手')} · {formatTime(msg.created_at)}
                      </p>
                    </div>

                    {msg.role === 'user' && (
                      <div className="w-8 h-8 rounded-full bg-primary/15 text-primary flex items-center justify-center shadow-sm shrink-0">
                        <UserCircle2 className="w-4 h-4" />
                      </div>
                    )}

                    {msg.role === 'assistant' && msg.references && msg.references.length > 0 && (
                      <div className="mt-2 w-[85%] ml-11">
                        <details className="group">
                          <summary className="text-xs text-slate-500 cursor-pointer hover:text-primary transition-colors flex items-center gap-1.5 list-none">
                            <Database className="w-3.5 h-3.5" />
                            参考资料 ({msg.references.length})
                          </summary>
                          <div className="mt-2 p-3 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-3">
                            {msg.references.map((ref, idx) => (
                              <div key={idx} className="space-y-1">
                                <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                                  <span className="bg-slate-200 px-1.5 py-0.5 rounded text-[10px]">{idx + 1}</span>
                                  {ref.file_name} {ref.page && `| 第 ${ref.page} 页`}
                                </div>
                                <p className="text-[11px] text-slate-500 italic leading-relaxed pl-6 border-l-2 border-slate-200">
                                  "{ref.preview}"
                                </p>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messageEndRef} />
              </div>
              
              <div className="py-4">
                <div className="relative flex items-end gap-2 bg-white px-3 py-2.5 rounded-2xl border border-slate-200 shadow-lg shadow-slate-200/40 focus-within:ring-4 ring-primary/10 transition-all">
                  <textarea
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="输入问题..."
                    className="flex-1 bg-transparent border-none focus:ring-0 p-2 text-sm resize-none placeholder:text-slate-400"
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || !selectedAgentId || !sessionId}
                    className="p-2.5 bg-primary text-white rounded-xl hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-2 px-1">Enter 发送，Shift + Enter 换行</p>
              </div>
            </div>
          )}

          {activeTab === 'knowledge' && (
            <div className="p-8 max-w-5xl mx-auto w-full space-y-8 overflow-y-auto app-scrollbar h-full">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <h3 className="text-xl font-bold">知识库资料</h3>
                  {uploadProgress !== null && (
                    <div className="flex items-center gap-2">
                      <div className="w-32 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-accent transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                      </div>
                      <span className="text-[10px] font-bold text-slate-500">{uploadProgress}%</span>
                    </div>
                  )}
                </div>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-xl text-sm hover:bg-slate-800 transition-colors cursor-pointer">
                    <Paperclip className="w-4 h-4" /> 上传文件
                    <input type="file" className="hidden" onChange={handleFileUpload} accept=".txt,.md,.pdf,.docx" />
                  </label>
                  <button 
                    onClick={() => handleStartIndexing()}
                    disabled={isIndexing}
                    className={`flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm hover:opacity-90 transition-opacity ${
                      isIndexing ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {isIndexing && indexingTarget === 'all' ? (
                      <svg className="transform -rotate-90 w-4 h-4 mr-1">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-white/30" />
                        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-white transition-all duration-300" strokeDasharray={2 * Math.PI * 6} strokeDashoffset={(2 * Math.PI * 6) * (1 - indexingProgress / 100)} />
                      </svg>
                    ) : isIndexing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : null}
                    {isIndexing && indexingTarget === 'all' ? `正在向量化 ${Math.round(indexingProgress)}%` : isIndexing ? '正在向量化...' : '开始向量化'}
                  </button>
                </div>
              </div>

              <div className="bg-white border rounded-2xl overflow-hidden shadow-sm">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 border-b text-slate-500 uppercase text-xs font-semibold">
                    <tr>
                      <th className="px-6 py-4">文件名</th>
                      <th className="px-6 py-4">状态</th>
                      <th className="px-6 py-4">上传时间</th>
                      <th className="px-6 py-4">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {files.map(file => (
                      <tr key={file.file_id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 font-medium">{file.file_name}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            file.status === 'indexed' ? 'bg-accent/10 text-accent' : 'bg-secondary/10 text-secondary'
                          }`}>
                            {file.status === 'indexed' ? '已索引' : '待处理'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-500">{file.upload_time}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            {isIndexing && indexingTarget === file.file_id ? (
                              <div className="relative inline-flex items-center justify-center p-2" title={`向量化中 ${Math.round(indexingProgress)}%`}>
                                <svg className="transform -rotate-90 w-5 h-5">
                                  <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-slate-200" />
                                  <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-primary transition-all duration-300" strokeDasharray={2 * Math.PI * 8} strokeDashoffset={(2 * Math.PI * 8) * (1 - indexingProgress / 100)} />
                                </svg>
                              </div>
                            ) : file.status !== 'indexed' && (
                              <button 
                                onClick={() => handleStartIndexing(file.file_id)}
                                disabled={isIndexing}
                                className={`p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors ${isIndexing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                title="向量化此文件"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            )}
                            <button 
                              onClick={() => handleDeleteFile(file.file_id)}
                              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                              title="删除文件"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {files.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-slate-400">
                          暂无资料，请上传
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="p-8 max-w-2xl mx-auto w-full space-y-8 overflow-y-auto app-scrollbar h-full">
              <div className="space-y-6">
                <h3 className="text-xl font-bold">Agent 设置</h3>
                
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">Agent 名称</label>
                  <input
                    type="text"
                    value={editAgent.name || ''}
                    onChange={e => setEditAgent(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">描述</label>
                  <textarea
                    rows={3}
                    value={editAgent.description || ''}
                    onChange={e => setEditAgent(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none resize-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">系统 Prompt</label>
                  <textarea
                    rows={8}
                    value={editAgent.system_prompt || ''}
                    onChange={e => setEditAgent(prev => ({ ...prev, system_prompt: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none font-mono text-sm"
                  />
                </div>

                <div className="pt-4">
                  <button 
                    onClick={handleUpdateAgent}
                    className="w-full py-3 bg-primary text-white rounded-xl font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
                  >
                    保存配置
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* 创建 Agent 弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-8 space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">新建 Agent</h3>
                <button onClick={() => setShowCreateModal(false)} className="p-2 hover:bg-slate-100 rounded-full">
                  <Trash2 className="w-5 h-5 text-slate-400 rotate-45" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-semibold text-slate-700">名称</label>
                  <input
                    autoFocus
                    type="text"
                    value={newAgent.name}
                    onChange={e => setNewAgent(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none"
                    placeholder="例如：论文润色助手"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-semibold text-slate-700">描述</label>
                  <input
                    type="text"
                    value={newAgent.description}
                    onChange={e => setNewAgent(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none"
                    placeholder="简短说明 Agent 的用途"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-semibold text-slate-700">系统 Prompt</label>
                  <textarea
                    rows={4}
                    value={newAgent.system_prompt}
                    onChange={e => setNewAgent(prev => ({ ...prev, system_prompt: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-50 border rounded-xl focus:ring-2 ring-primary/20 outline-none resize-none"
                    placeholder="定义 Agent 的人格、任务和限制..."
                  />
                </div>
              </div>

              <div className="flex gap-4 pt-4">
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 border border-slate-200 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
                >
                  取消
                </button>
                <button 
                  onClick={handleCreateAgent}
                  className="flex-1 py-3 bg-primary text-white rounded-xl font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
                >
                  立即创建
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {confirmDialog && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/45 backdrop-blur-sm p-4"
          onClick={() => setConfirmDialog(null)}
        >
          <div
            className="bg-white rounded-2xl w-full max-w-md shadow-2xl border border-slate-100"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <h3 className="text-lg font-semibold text-slate-900">{confirmDialog.title}</h3>
              <p className="text-sm text-slate-600 mt-2">{confirmDialog.description}</p>
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setConfirmDialog(null)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={runConfirmedAction}
                  className={`flex-1 py-2.5 rounded-xl text-white transition-opacity ${
                    confirmDialog.danger ? 'bg-red-500 hover:opacity-90' : 'bg-primary hover:opacity-90'
                  }`}
                >
                  {confirmDialog.confirmText || '确认'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
