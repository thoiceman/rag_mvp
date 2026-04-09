import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# 加载 .env 文件中的环境变量
load_dotenv()

from typing import List, Optional
import uvicorn

from src.services.agent_service import AgentService
from src.services.file_service import FileService
from src.services.chat_service import ChatService
from src.services.session_service import SessionService
from src.services.agentic_workflow_service import AgenticWorkflowService
from src.rag.index_service import IndexService
from src.model.factory import check_api_ket_set
from src.utils.logger import get_logger

from contextlib import asynccontextmanager

logger = get_logger("API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        check_api_ket_set()
        logger.info("API 启动：API Key 校验通过")
    except EnvironmentError as e:
        logger.error(f"API 启动失败：{str(e)}")
        # 在生产环境下可以考虑停止进程，开发环境下仅记录日志
    yield
    # 这里可以放置关闭应用时的清理逻辑

app = FastAPI(title="RAG MVP API", lifespan=lifespan)

# 允许跨域（React 前端调用必选）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
agent_service = AgentService()
file_service = FileService()
chat_service = ChatService()
session_service = SessionService()
index_service = IndexService()
agentic_workflow_service = AgenticWorkflowService()

# --- Agent 路由 ---

@app.get("/agents")
async def list_agents():
    return agent_service.list_agents()

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.post("/agents")
async def create_agent(name: str, system_prompt: str, category: str = "custom", description: str = ""):
    return agent_service.create_agent(name, category, description, system_prompt)

@app.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, data: dict):
    try:
        return agent_service.update_agent(agent_id, **data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    agent_service.delete_agent(agent_id)
    return {"status": "success"}

# --- 文件管理 路由 ---

@app.get("/agents/{agent_id}/files")
async def list_files(agent_id: str):
    return file_service.list_files(agent_id)

@app.post("/agents/{agent_id}/files")
async def upload_file(agent_id: str, file: UploadFile = File(...)):
    # 模拟 Streamlit 的上传文件对象
    class UploadedFileProxy:
        def __init__(self, upload_file: UploadFile):
            self.name = upload_file.filename
            self._content = None
        
        def getbuffer(self):
            class BufferProxy:
                def __init__(self, content): self.content = content
                def tobytes(self): return self.content
            if self._content is None:
                import asyncio
                # 注意：这里在异步环境中使用同步读取可能需要处理
                # 但由于 save_uploaded_file 内部是同步写，这里简单处理
                return BufferProxy(None) 
            return BufferProxy(self._content)

    # 实际开发中建议重构 file_service 接受 bytes，这里先做适配
    content = await file.read()
    class SimpleProxy:
        def __init__(self, name, content):
            self.name = name
            self.content = content
        def getbuffer(self):
            class B:
                def __init__(self, c): self.c = c
                def tobytes(self): return self.c
            return B(self.content)

    return file_service.save_uploaded_file(agent_id, SimpleProxy(file.filename, content))

@app.delete("/agents/{agent_id}/files/{file_id}")
async def delete_file(agent_id: str, file_id: str):
    # 同步逻辑：移除索引并删除文件
    if index_service.remove_index(agent_id, file_id):
        file_service.delete_file(agent_id, file_id)
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="删除索引失败")

# --- 索引路由 ---

@app.post("/agents/{agent_id}/index")
async def build_index(agent_id: str, file_id: Optional[str] = None):
    import queue
    import threading
    import json
    q = queue.Queue()

    def progress_cb(percent, msg):
        q.put({"type": "progress", "percent": percent * 100, "message": msg})

    def worker():
        try:
            res = index_service.build_index(agent_id, file_id=file_id, progress_callback=progress_cb)
            q.put({"type": "result", "data": res})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put(None)

    threading.Thread(target=worker).start()

    import asyncio
    async def event_generator():
        while True:
            try:
                # 非阻塞获取，防止阻塞主事件循环
                item = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue
                
            if item is None:
                break
            # 加入额外换行符，确保遵循 SSE 规范并强制刷新缓冲区
            yield json.dumps(item) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 聊天路由 ---

@app.post("/chat/stream")
async def chat_stream(agent_id: str = Form(...), session_id: str = Form(...), question: str = Form(...)):
    result = chat_service.chat_stream(agent_id, session_id, question)
    
    def event_generator():
        # 先发送元数据（参考资料）
        import json
        yield json.dumps({
            "type": "metadata",
            "references": result["references"],
            "hit_count": result["hit_count"]
        }) + "\n"
        
        # 再发送流式文本
        for chunk in result["stream"]:
            yield json.dumps({"type": "content", "content": chunk}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/sessions")
async def create_session(agent_id: str):
    return session_service.create_session(agent_id)

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    return session_service.get_session(session_id)

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}

@app.get("/agents/{agent_id}/sessions")
async def list_sessions(agent_id: str):
    return session_service.list_sessions(agent_id)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
