from typing import Optional
from sqlmodel import SQLModel, Field

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
