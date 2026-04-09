from src.services.agentic_workflow_service import AgenticWorkflowService
from src.services.session_service import SessionService
from src.services.memory_service import MemoryService


class ChatService:
    def __init__(self):
        self.agentic_service = AgenticWorkflowService()
        self.session_service = SessionService()
        self.memory_service = MemoryService()

    def chat(self, agent_id: str, session_id: str, question: str) -> dict:
        session = self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")
        
        # 先取历史
        history = session.get("messages", [])
        
        # 保存当前提问
        self.session_service.append_message(session_id, "user", question)
        
        # 发起 Agent 问答（内部集成了 RAG 等工具）
        result = self.agentic_service.ask(agent_id, question, history=history, session_id=session_id)
        
        # 保存回复
        self.session_service.append_message(session_id, "assistant", result["answer"])
        
        # 【触发异步记忆处理】
        self.memory_service.process_memory_async(session_id)
        
        return result

    def chat_stream(self, agent_id: str, session_id: str, question: str):
        """流式聊天"""
        session = self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")
        
        history = session.get("messages", [])
        self.session_service.append_message(session_id, "user", question)
        
        # 调用 Agent 流式接口（模拟流）
        result = self.agentic_service.ask_stream(agent_id, question, history=history, session_id=session_id)
        
        # 返回一个包装生成器，以便在流结束时保存回复到历史记录
        def stream_wrapper():
            full_answer = ""
            for chunk in result["stream"]:
                full_answer += chunk
                yield chunk
            
            # 流结束后，保存完整回复
            self.session_service.append_message(session_id, "assistant", full_answer)
            
            # 【触发异步记忆处理】
            self.memory_service.process_memory_async(session_id)
            
        return {
            "references": result["references"],
            "hit_count": result["hit_count"],
            "stream": stream_wrapper()
        }