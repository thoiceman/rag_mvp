from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.services.session_service import session_service

router = APIRouter()

@router.post("")
async def create_session(agent_id: str, db: Session = Depends(get_session)):
    return session_service.create_session(db, agent_id)

@router.get("/{session_id}")
async def get_session(session_id: str, db: Session = Depends(get_session)):
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_session)):
    deleted = session_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}

