from typing import Optional
from pydantic import BaseModel

class AgentCreateRequest(BaseModel):
    name: str
    system_prompt: str
    category: str = "custom"
    description: str = ""

class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    knowledge_status: Optional[str] = None
    vector_collection_name: Optional[str] = None
    search_k: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
