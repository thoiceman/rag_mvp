from src.rag.rag_service import RagService
from src.services.session_service import SessionService


class ChatService:
    def __init__(self):
        self.rag_service = RagService()
        self.session_service = SessionService()

    def chat(self, agent_id: str, session_id: str, question: str) -> dict:
        session = self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")
        
        # 先取历史
        history = session.get("messages", [])
        
        # 保存当前提问
        self.session_service.append_message(session_id, "user", question)
        
        # 发起 RAG 问答，传入历史
        result = self.rag_service.ask(agent_id, question, history=history)
        
        # 保存回复
        self.session_service.append_message(session_id, "assistant", result["answer"])
        return result

    def chat_stream(self, agent_id: str, session_id: str, question: str):
        """流式聊天"""
        session = self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")
        
        history = session.get("messages", [])
        self.session_service.append_message(session_id, "user", question)
        
        # 调用 RAG 流式接口
        result = self.rag_service.ask_stream(agent_id, question, history=history)
        
        # 返回一个包装生成器，以便在流结束时保存回复到历史记录
        def stream_wrapper():
            full_answer = ""
            for chunk in result["stream"]:
                full_answer += chunk
                yield chunk
            
            # 流结束后，保存完整回复
            self.session_service.append_message(session_id, "assistant", full_answer)
            
        return {
            "references": result["references"],
            "hit_count": result["hit_count"],
            "stream": stream_wrapper()
        }