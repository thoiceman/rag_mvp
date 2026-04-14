from sqlmodel import Session
from app.models.agent import Agent
from app.repositories.agent_repository import agent_repository
from app.schemas.agent import AgentCreateRequest, AgentUpdateRequest
from app.utils.id_util import new_id
from app.utils.time_util import now_str

class AgentService:
    def __init__(self):
        self.repository = agent_repository

    def create_agent(self, db: Session, name: str, category: str, description: str, system_prompt: str) -> dict:
        agent_id = new_id()
        agent = Agent(
            agent_id=agent_id,
            name=name,
            category=category,
            description=description,
            system_prompt=system_prompt,
            knowledge_status="not_indexed",
            created_at=now_str(),
            updated_at=now_str(),
            vector_collection_name=f"agent_{agent_id}",
            search_k=4,
            chunk_size=500,
            chunk_overlap=80,
        )
        created_agent = self.repository.create(db, obj_in=agent)
        return created_agent.model_dump()

    def list_agents(self, db: Session) -> list[dict]:
        agents = self.repository.get_all(db)
        return sorted([a.model_dump() for a in agents], key=lambda x: x.get("updated_at", ""), reverse=True)

    def get_agent(self, db: Session, agent_id: str) -> dict | None:
        agent = self.repository.get(db, agent_id)
        return agent.model_dump() if agent else None

    def update_agent(self, db: Session, agent_id: str, **kwargs) -> dict:
        agent = self.repository.get(db, agent_id)
        if not agent:
            raise ValueError("Agent不存在")

        allowed = {
            "name", "category", "description", "system_prompt", "knowledge_status",
            "search_k", "chunk_size", "chunk_overlap", "vector_collection_name"
        }
        
        update_data = {}
        for key, value in kwargs.items():
            if key in allowed and value is not None:
                update_data[key] = value

        update_data["updated_at"] = now_str()
        
        updated_agent = self.repository.update(db, db_obj=agent, obj_in=update_data)
        return updated_agent.model_dump()

    def delete_agent(self, db: Session, agent_id: str) -> None:
        self.repository.delete(db, id=agent_id)

agent_service = AgentService()
