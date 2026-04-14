from sqlmodel import Session as DbSession, select
from src.storage.database import engine
from src.model.db_models import Agent
from src.utils.id_util import new_id
from src.utils.time_util import now_str


class AgentService:
    def create_agent(self, name: str, category: str, description: str, system_prompt: str) -> dict:
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
        with DbSession(engine) as session:
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent.model_dump()

    def list_agents(self) -> list[dict]:
        with DbSession(engine) as session:
            statement = select(Agent)
            agents = session.exec(statement).all()
            return sorted([a.model_dump() for a in agents], key=lambda x: x.get("updated_at", ""), reverse=True)

    def get_agent(self, agent_id: str) -> dict | None:
        with DbSession(engine) as session:
            agent = session.get(Agent, agent_id)
            return agent.model_dump() if agent else None

    def update_agent(self, agent_id: str, **kwargs) -> dict:
        with DbSession(engine) as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                raise ValueError("Agent不存在")

            allowed = {
                "name", "category", "description", "system_prompt", "knowledge_status",
                "search_k", "chunk_size", "chunk_overlap", "vector_collection_name"
            }
            for key, value in kwargs.items():
                if key in allowed and value is not None:
                    setattr(agent, key, value)

            agent.updated_at = now_str()
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent.model_dump()

    def delete_agent(self, agent_id: str) -> None:
        with DbSession(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent:
                session.delete(agent)
                session.commit()