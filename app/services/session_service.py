from sqlmodel import Session as DbSession
from app.models.session import Session
from app.repositories.session_repository import session_repository
from app.utils.id_util import new_id
from app.utils.time_util import now_str


class SessionService:
    def __init__(self):
        self.repository = session_repository

    def create_session(self, db: DbSession, agent_id: str, title: str = "新会话") -> dict:
        session_id = new_id()
        session = Session(
            session_id=session_id,
            agent_id=agent_id,
            title=title,
            created_at=now_str(),
            updated_at=now_str(),
            messages=[]
        )
        created_session = self.repository.create(db, obj_in=session)
        return created_session.model_dump_with_messages()

    def get_session(self, db: DbSession, session_id: str) -> dict | None:
        session = self.repository.get(db, session_id)
        return session.model_dump_with_messages() if session else None

    def delete_session(self, db: DbSession, session_id: str) -> bool:
        return self.repository.delete(db, id=session_id)

    def list_sessions(self, db: DbSession, agent_id: str) -> list[dict]:
        sessions = self.repository.get_by_agent_id(db, agent_id)
        return sorted([s.model_dump_with_messages() for s in sessions], key=lambda x: x.get("updated_at", ""), reverse=True)

    def append_message(self, db: DbSession, session_id: str, role: str, content: str) -> dict:
        session = self.repository.get(db, session_id)
        if not session:
            raise ValueError("会话不存在")

        # 优化：如果是用户的第一条消息，自动截取部分内容作为会话标题
        if role == "user" and session.title == "新会话":
            first_line = content.strip().split('\n')[0]
            new_title = first_line[:15]
            if len(first_line) > 15 or len(content) > len(first_line):
                new_title += "..."
            session.title = new_title

        current_messages = session.messages
        current_messages.append({
            "role": role,
            "content": content,
            "created_at": now_str(),
        })
        
        session.messages = current_messages
        session.updated_at = now_str()
        
        updated_session = self.repository.update(db, db_obj=session, obj_in={})
        return updated_session.model_dump_with_messages()

    def update_memory_state(self, db: DbSession, session_id: str, summary: str, summarized_index: int, vectorized_index: int) -> None:
        """更新会话的长对话记忆状态"""
        session = self.repository.get(db, session_id)
        if session:
            self.repository.update(db, db_obj=session, obj_in={
                "summary": summary,
                "summarized_index": summarized_index,
                "vectorized_index": vectorized_index
            })

session_service = SessionService()
