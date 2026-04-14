from sqlmodel import Session as DbSession, select
from src.storage.database import engine
from src.model.db_models import Session
from src.utils.id_util import new_id
from src.utils.time_util import now_str


class SessionService:
    def create_session(self, agent_id: str, title: str = "新会话") -> dict:
        session_id = new_id()
        session = Session(
            session_id=session_id,
            agent_id=agent_id,
            title=title,
            created_at=now_str(),
            updated_at=now_str(),
            messages=[]
        )
        with DbSession(engine) as db:
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.model_dump_with_messages()

    def get_session(self, session_id: str) -> dict | None:
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            return session.model_dump_with_messages() if session else None

    def delete_session(self, session_id: str) -> bool:
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if not session:
                return False
            db.delete(session)
            db.commit()
            return True

    def list_sessions(self, agent_id: str) -> list[dict]:
        with DbSession(engine) as db:
            statement = select(Session).where(Session.agent_id == agent_id)
            sessions = db.exec(statement).all()
            return sorted([s.model_dump_with_messages() for s in sessions], key=lambda x: x.get("updated_at", ""), reverse=True)

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
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
            
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.model_dump_with_messages()

    def update_memory_state(self, session_id: str, summary: str, summarized_index: int, vectorized_index: int) -> None:
        """更新会话的长对话记忆状态"""
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if session:
                session.summary = summary
                session.summarized_index = summarized_index
                session.vectorized_index = vectorized_index
                db.add(session)
                db.commit()
