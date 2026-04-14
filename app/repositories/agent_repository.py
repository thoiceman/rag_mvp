from sqlmodel import Session, select
from typing import List
from app.repositories.base_repository import BaseRepository
from app.models.agent import Agent
from app.schemas.agent import AgentCreateRequest, AgentUpdateRequest

class AgentRepository(BaseRepository[Agent, AgentCreateRequest, AgentUpdateRequest]):
    def get_all(self, db: Session) -> List[Agent]:
        statement = select(self.model)
        return db.exec(statement).all()

agent_repository = AgentRepository(Agent)
