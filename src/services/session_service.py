from src.storage.paths import SESSIONS_DIR
from src.storage.json_store import JsonStore
from src.utils.id_util import new_id
from src.utils.time_util import now_str


class SessionService:
    def create_session(self, agent_id: str, title: str = "新会话") -> dict:
        session_id = new_id()
        session = {
            "session_id": session_id,
            "agent_id": agent_id,
            "title": title,
            "created_at": now_str(),
            "updated_at": now_str(),
            "messages": [],
        }
        JsonStore.save(SESSIONS_DIR / f"{session_id}.json", session)
        return session

    def get_session(self, session_id: str) -> dict | None:
        return JsonStore.load(SESSIONS_DIR / f"{session_id}.json", default=None)

    def list_sessions(self, agent_id: str) -> list[dict]:
        sessions = []
        for path in SESSIONS_DIR.glob("*.json"):
            session = JsonStore.load(path, default={})
            if session and session.get("agent_id") == agent_id:
                sessions.append(session)
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        path = SESSIONS_DIR / f"{session_id}.json"
        session = JsonStore.load(path, default=None)
        if not session:
            raise ValueError("会话不存在")

        # 优化：如果是用户的第一条消息，自动截取部分内容作为会话标题
        if role == "user" and session.get("title") == "新会话":
            # 取第一行的前15个字符作为标题
            first_line = content.strip().split('\n')[0]
            new_title = first_line[:15]
            if len(first_line) > 15 or len(content) > len(first_line):
                new_title += "..."
            session["title"] = new_title

        session["messages"].append({
            "role": role,
            "content": content,
            "created_at": now_str(),
        })
        session["updated_at"] = now_str()
        JsonStore.save(path, session)
        return session