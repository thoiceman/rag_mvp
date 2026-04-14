import os
from sqlmodel import SQLModel, create_engine, Session as DbSession
from app.storage.paths import BASE_DIR

# 数据库文件保存在 data 目录下
DB_FILE = BASE_DIR / "data" / "rag_mvp.db"
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

sqlite_url = f"sqlite:///{DB_FILE}"
# 启用 check_same_thread=False 允许跨线程共享连接池，适合 FastAPI
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

def init_db():
    from app.models.agent import Agent
    from app.models.file_meta import FileMeta
    from app.models.session import Session
    SQLModel.metadata.create_all(engine)

def get_session():
    with DbSession(engine) as session:
        yield session