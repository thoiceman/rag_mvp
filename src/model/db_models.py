import json
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, String

class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    agent_id: str = Field(primary_key=True, index=True)
    name: str
    category: str
    description: str
    system_prompt: str
    knowledge_status: str = Field(default="not_indexed")
    created_at: str
    updated_at: str
    vector_collection_name: str
    search_k: int = Field(default=4)
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=80)

class FileMeta(SQLModel, table=True):
    __tablename__ = "files"
    file_id: str = Field(primary_key=True, index=True)
    agent_id: str = Field(index=True)
    file_name: str
    file_path: str
    upload_time: str
    status: str = Field(default="uploaded")
    md5: str
    indexed_at: Optional[str] = Field(default=None)

class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    session_id: str = Field(primary_key=True, index=True)
    agent_id: str = Field(index=True)
    title: str = Field(default="新会话")
    created_at: str
    updated_at: str
    summary: str = Field(default="暂无摘要")
    summarized_index: int = Field(default=0)
    vectorized_index: int = Field(default=0)
    
    # Store messages as JSON string in the database
    messages_json: str = Field(default="[]")

    @property
    def messages(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.messages_json)
        except json.JSONDecodeError:
            return []

    @messages.setter
    def messages(self, value: List[Dict[str, Any]]):
        self.messages_json = json.dumps(value, ensure_ascii=False)

    def model_dump_with_messages(self) -> Dict[str, Any]:
        """Custom dump method to return parsed messages list instead of string"""
        data = self.model_dump()
        data["messages"] = self.messages
        del data["messages_json"]
        return data