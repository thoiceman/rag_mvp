from sqlmodel import SQLModel, Field

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
