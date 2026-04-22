import axios from 'axios';
import type { Agent, Session, FileMeta } from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1').replace(/\/$/, '');

const api = axios.create({
  baseURL: `${API_BASE}/`,
});

export const agentApi = {
  list: () => api.get<Agent[]>('agents'),
  get: (id: string) => api.get<Agent>(`agents/${id}`),
  create: (name: string, system_prompt: string, description: string, category: string = 'custom') => 
    api.post<Agent>('agents', { name, system_prompt, description, category }),
  update: (id: string, data: Partial<Agent>) => api.patch<Agent>(`agents/${id}`, data),
  delete: (id: string) => api.delete(`agents/${id}`),
};

export const fileApi = {
  list: (agentId: string) => api.get<FileMeta[]>(`agents/${agentId}/files`),
  upload: (agentId: string, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<FileMeta>(`agents/${agentId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });
  },
  delete: (agentId: string, fileId: string) => 
    api.delete(`agents/${agentId}/files/${fileId}`),
};

export const indexApi = {
  build: (agentId: string, fileId?: string) => {
    let url = `${API_BASE}/agents/${agentId}/index`;
    if (fileId) url += `?file_id=${fileId}`;
    return fetch(url, { method: 'POST' });
  }
};

export const chatApi = {
  createSession: (agentId: string) => api.post<Session>('sessions', null, { params: { agent_id: agentId } }),
  getSession: (sessionId: string) => api.get<Session>(`sessions/${sessionId}`),
  listSessions: (agentId: string) => api.get<Session[]>(`agents/${agentId}/sessions`),
  deleteSession: (sessionId: string) => api.delete(`sessions/${sessionId}`),
  // 注意：流式接口通常使用 fetch 或 EventSource
  chatStream: (agentId: string, sessionId: string, question: string) => {
    const formData = new FormData();
    formData.append('agent_id', agentId);
    formData.append('session_id', sessionId);
    formData.append('question', question);
    
    return fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      body: formData,
    });
  },
};
