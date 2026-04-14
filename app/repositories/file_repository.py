from sqlmodel import Session, select
from typing import List
from app.repositories.base_repository import BaseRepository
from app.models.file_meta import FileMeta
from pydantic import BaseModel

class FileMetaCreate(BaseModel):
    pass

class FileMetaUpdate(BaseModel):
    pass

class FileRepository(BaseRepository[FileMeta, FileMetaCreate, FileMetaUpdate]):
    def get_by_agent_id(self, db: Session, agent_id: str) -> List[FileMeta]:
        statement = select(self.model).where(self.model.agent_id == agent_id)
        return db.exec(statement).all()

file_repository = FileRepository(FileMeta)
