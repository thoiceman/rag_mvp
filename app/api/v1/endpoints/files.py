from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from app.core.database import get_session
from app.services.file_service import file_service
from app.rag.index_service import IndexService

router = APIRouter()
index_service = IndexService()

@router.get("/{agent_id}/files")
async def list_files(agent_id: str, db: Session = Depends(get_session)):
    return file_service.list_files(db, agent_id)

@router.post("/{agent_id}/files")
async def upload_file(agent_id: str, file: UploadFile = File(...), db: Session = Depends(get_session)):
    content = await file.read()
    return file_service.save_uploaded_file(db, agent_id, file.filename, content)

@router.delete("/{agent_id}/files/{file_id}")
async def delete_file(agent_id: str, file_id: str, db: Session = Depends(get_session)):
    if index_service.remove_index(db, agent_id, file_id):
        file_service.delete_file(db, agent_id, file_id)
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="删除索引失败")
