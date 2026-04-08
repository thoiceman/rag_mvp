export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  system_prompt: string;
  created_at: string;
  vector_collection_name: string;
  knowledge_status: string;
}

export interface FileMeta {
  file_id: string;
  agent_id: string;
  file_name: string;
  file_path: string;
  upload_time: string;
  status: 'uploaded' | 'indexed';
  md5: string;
  indexed_at: string | null;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  references?: Reference[];
}

export interface Session {
  session_id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface Reference {
  file_name: string;
  page: string | number;
  preview: string;
}

export interface ChatResult {
  answer: string;
  references: Reference[];
  hit_count: number;
}
