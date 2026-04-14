import json
from fastapi import APIRouter, Depends, Form
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from app.core.database import get_session
from app.services.chat_service import chat_service

router = APIRouter()

@router.post("/stream")
async def chat_stream(
    agent_id: str = Form(...),
    session_id: str = Form(...),
    question: str = Form(...),
    db: Session = Depends(get_session)
):
    result = await chat_service.chat_stream(db, agent_id, session_id, question)
    
    async def event_generator():
        # 先发送元数据（参考资料），此时可能为空
        yield json.dumps({
            "type": "metadata",
            "references": result.get("get_references", lambda: [])(),
            "hit_count": result.get("get_hit_count", lambda: 0)()
        }) + "\n"
        
        # 发送流式文本
        async for chunk in result["stream"]:
            yield json.dumps({"type": "content", "content": chunk}) + "\n"
            
        # 结束后再发送一次元数据，确保异步更新的 references 能同步给前端
        yield json.dumps({
            "type": "metadata",
            "references": result.get("get_references", lambda: [])(),
            "hit_count": result.get("get_hit_count", lambda: 0)()
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
