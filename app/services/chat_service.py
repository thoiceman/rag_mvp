from sqlmodel import Session
from app.services.agentic_workflow_service import AgenticWorkflowService
from app.services.session_service import SessionService
from app.services.memory_service import MemoryService


class ChatService:
    def __init__(self):
        self.agentic_service = AgenticWorkflowService()
        self.session_service = SessionService()
        self.memory_service = MemoryService()

    def chat(self, db: Session, agent_id: str, session_id: str, question: str) -> dict:
        session = self.session_service.get_session(db, session_id)
        if not session:
            raise ValueError("会话不存在")
        
        # 先取历史
        history = session.get("messages", [])
        
        # 保存当前提问
        self.session_service.append_message(db, session_id, "user", question)
        
        # 发起 Agent 问答（内部集成了 RAG 等工具）
        result = self.agentic_service.ask(db, agent_id, question, history=history, session_id=session_id)
        
        # 保存回复
        self.session_service.append_message(db, session_id, "assistant", result["answer"])
        
        # 【触发异步记忆处理】
        # 这里可能需要考虑是否要在后台任务执行时传递 db，由于是异步且 db 可能被关闭，通常内存服务需要自己获取 db 或传入新建的 db
        self.memory_service.process_memory_async(session_id)
        
        return result

    async def chat_stream(self, db: Session, agent_id: str, session_id: str, question: str):
        """流式聊天"""
        session = self.session_service.get_session(db, session_id)
        if not session:
            raise ValueError("会话不存在")
        
        history = session.get("messages", [])
        self.session_service.append_message(db, session_id, "user", question)
        
        # 调用 Agent 流式接口（真实异步流）
        result = await self.agentic_service.ask_stream(db, agent_id, question, history=history, session_id=session_id)
        
        # 返回一个包装异步生成器，以便在流结束时保存回复到历史记录
        async def stream_wrapper():
            full_answer = ""
            async for chunk in result["stream"]:
                full_answer += chunk
                yield chunk
            
            # 流结束后，保存完整回复
            self.session_service.append_message(db, session_id, "assistant", full_answer)
            
            # 【触发异步记忆处理】
            self.memory_service.process_memory_async(session_id)
            
        return {
            "get_references": lambda: self.agentic_service._last_references,
            "get_hit_count": lambda: self.agentic_service._last_hit_count,
            "stream": stream_wrapper()
        }

chat_service = ChatService()
