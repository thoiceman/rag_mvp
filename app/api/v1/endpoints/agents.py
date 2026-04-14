from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.schemas.agent import AgentCreateRequest, AgentUpdateRequest
from app.services.agent_service import agent_service

router = APIRouter()

@router.get("")
async def list_agents(db: Session = Depends(get_session)):
    return agent_service.list_agents(db)

@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: Session = Depends(get_session)):
    agent = agent_service.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("")
async def create_agent(req: AgentCreateRequest, db: Session = Depends(get_session)):
    return agent_service.create_agent(db, req.name, req.category, req.description, req.system_prompt)

@router.patch("/{agent_id}")
async def update_agent(agent_id: str, req: AgentUpdateRequest, db: Session = Depends(get_session)):
    try:
        update_data = req.model_dump(exclude_unset=True)
        return agent_service.update_agent(db, agent_id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: Session = Depends(get_session)):
    agent_service.delete_agent(db, agent_id)
    return {"status": "success"}

from app.services.session_service import session_service

@router.get("/{agent_id}/sessions")
async def list_sessions(agent_id: str, db: Session = Depends(get_session)):
    return session_service.list_sessions(db, agent_id)
