import hashlib
from pathlib import Path
from sqlmodel import Session as DbSession, select
from src.storage.database import engine
from src.model.db_models import FileMeta
from src.storage.paths import UPLOADS_DIR, BASE_DIR, resolve_file_path
from src.utils.time_util import now_str
from src.utils.id_util import new_id
from src.utils.logger import get_logger

logger = get_logger("FileService")


class FileService:
    @staticmethod
    def _calc_md5_bytes(content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def save_uploaded_file(self, agent_id: str, filename: str, content: bytes) -> dict:
        agent_dir = UPLOADS_DIR / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        file_md5 = self._calc_md5_bytes(content)

        # 检查当前 Agent 下是否存在完全相同的文件（MD5 + 文件名）
        for meta in self.list_files(agent_id):
            if meta.get("md5") == file_md5 and meta.get("file_name") == filename:
                logger.info(f"文件已存在: {filename} (Agent: {agent_id})")
                return meta

        file_id = new_id()
        safe_file_name = f"{file_id}_{filename}"
        file_path = agent_dir / safe_file_name
        
        logger.info(f"保存新文件: {filename} -> {safe_file_name}")
        with open(file_path, "wb") as f:
            f.write(content)

        file_meta = FileMeta(
            file_id=file_id,
            agent_id=agent_id,
            file_name=filename,
            file_path=str(file_path.relative_to(BASE_DIR)),
            upload_time=now_str(),
            status="uploaded",
            md5=file_md5,
            indexed_at=None,
        )
        
        with DbSession(engine) as db:
            db.add(file_meta)
            db.commit()
            db.refresh(file_meta)
            return file_meta.model_dump()

    def list_files(self, agent_id: str) -> list[dict]:
        with DbSession(engine) as db:
            statement = select(FileMeta).where(FileMeta.agent_id == agent_id)
            files = db.exec(statement).all()
            return sorted([f.model_dump() for f in files], key=lambda x: x.get("upload_time", ""), reverse=True)

    def list_unindexed_files(self, agent_id: str) -> list[dict]:
        return [f for f in self.list_files(agent_id) if f.get("status") != "indexed"]

    def get_file_meta(self, agent_id: str, file_id: str) -> dict | None:
        with DbSession(engine) as db:
            file_meta = db.get(FileMeta, file_id)
            return file_meta.model_dump() if file_meta else None

    def mark_indexed(self, agent_id: str, file_id: str) -> None:
        with DbSession(engine) as db:
            file_meta = db.get(FileMeta, file_id)
            if file_meta:
                file_meta.status = "indexed"
                file_meta.indexed_at = now_str()
                db.add(file_meta)
                db.commit()

    def mark_uploaded(self, agent_id: str, file_id: str) -> None:
        with DbSession(engine) as db:
            file_meta = db.get(FileMeta, file_id)
            if file_meta:
                file_meta.status = "uploaded"
                file_meta.indexed_at = None
                db.add(file_meta)
                db.commit()

    def delete_file(self, agent_id: str, file_id: str) -> None:
        """
        只删除源文件和元数据，不处理向量。
        向量删除交给上层索引服务处理。
        """
        with DbSession(engine) as db:
            file_meta = db.get(FileMeta, file_id)
            if not file_meta:
                return

            file_path = resolve_file_path(file_meta.file_path, file_meta.agent_id, file_meta.file_name)
            if file_path.exists():
                file_path.unlink()

            db.delete(file_meta)
            db.commit()