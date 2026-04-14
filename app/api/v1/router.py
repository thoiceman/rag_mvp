from fastapi import APIRouter
from app.api.v1.endpoints import agents, files, index, chat, sessions

api_router = APIRouter()

api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(files.router, prefix="/agents", tags=["files"])
api_router.include_router(index.router, prefix="/agents", tags=["index"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
