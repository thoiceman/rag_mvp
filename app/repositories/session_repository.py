from sqlmodel import Session, select
from typing import List
from app.repositories.base_repository import BaseRepository
from app.models.session import Session as ChatSessionModel
from pydantic import BaseModel

class SessionCreate(BaseModel):
    pass

class SessionUpdate(BaseModel):
    pass

class SessionRepository(BaseRepository[ChatSessionModel, SessionCreate, SessionUpdate]):
    def get_by_agent_id(self, db: Session, agent_id: str) -> List[ChatSessionModel]:
        statement = select(self.model).where(self.model.agent_id == agent_id)
        return db.exec(statement).all()

session_repository = SessionRepository(ChatSessionModel)
