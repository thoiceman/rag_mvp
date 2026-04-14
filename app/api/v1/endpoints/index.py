import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from app.core.database import get_session
from app.rag.index_service import IndexService

router = APIRouter()
index_service = IndexService()

@router.post("/{agent_id}/index")
async def build_index(agent_id: str, file_id: Optional[str] = None, db: Session = Depends(get_session)):
    q = asyncio.Queue()

    def progress_cb(percent, msg):
        try:
            q.put_nowait({"type": "progress", "percent": percent * 100, "message": msg})
        except asyncio.QueueFull:
            pass

    async def worker():
        try:
            loop = asyncio.get_running_loop()
            # 传递 db 给 index_service.build_index
            res = await loop.run_in_executor(
                None,
                lambda: index_service.build_index(db, agent_id, file_id=file_id, progress_callback=progress_cb)
            )
            await q.put({"type": "result", "data": res})
        except Exception as e:
            await q.put({"type": "error", "message": str(e)})
        finally:
            await q.put(None)

    asyncio.create_task(worker())

    async def event_generator():
        while True:
            item = await q.get()
            if item is None:
                break
            yield json.dumps(item) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
