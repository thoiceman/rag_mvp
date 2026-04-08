import hashlib
from pathlib import Path

from src.storage.paths import UPLOADS_DIR, BASE_DIR, resolve_file_path
from src.utils.time_util import now_str
from src.utils.id_util import new_id
from src.storage.json_store import JsonStore
from src.utils.logger import get_logger

logger = get_logger("FileService")


class FileService:
    @staticmethod
    def _calc_md5_bytes(content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def save_uploaded_file(self, agent_id: str, uploaded_file) -> dict:
        agent_dir = UPLOADS_DIR / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        content = uploaded_file.getbuffer().tobytes()
        file_md5 = self._calc_md5_bytes(content)

        # 检查当前 Agent 下是否存在完全相同的文件（MD5 + 文件名）
        for meta in self.list_files(agent_id):
            if meta.get("md5") == file_md5 and meta.get("file_name") == uploaded_file.name:
                logger.info(f"文件已存在: {uploaded_file.name} (Agent: {agent_id})")
                return meta

        file_id = new_id()
        # 为了避免文件名冲突（如同名但内容不同），物理存储使用 file_id 作为前缀或目录名
        # 这里选择保持原始文件名，但存放在以 file_id 命名的子目录下，或者直接重命名文件
        # 考虑到 paths.py 的 resolve_file_path，我们使用 file_id 保证唯一性
        safe_file_name = f"{file_id}_{uploaded_file.name}"
        file_path = agent_dir / safe_file_name
        
        logger.info(f"保存新文件: {uploaded_file.name} -> {safe_file_name}")
        with open(file_path, "wb") as f:
            f.write(content)

        meta = {
            "file_id": file_id,
            "agent_id": agent_id,
            "file_name": uploaded_file.name,
            "file_path": str(file_path.relative_to(BASE_DIR)),
            "upload_time": now_str(),
            "status": "uploaded",
            "md5": file_md5,
            "indexed_at": None,
        }
        JsonStore.save(agent_dir / f"{file_id}.meta.json", meta)
        return meta

    def list_files(self, agent_id: str) -> list[dict]:
        agent_dir = UPLOADS_DIR / agent_id
        if not agent_dir.exists():
            return []

        result = []
        for path in agent_dir.glob("*.meta.json"):
            meta = JsonStore.load(path, default={})
            if meta:
                result.append(meta)

        return sorted(result, key=lambda x: x.get("upload_time", ""), reverse=True)

    def list_unindexed_files(self, agent_id: str) -> list[dict]:
        return [f for f in self.list_files(agent_id) if f.get("status") != "indexed"]

    def get_file_meta(self, agent_id: str, file_id: str) -> dict | None:
        meta_path = UPLOADS_DIR / agent_id / f"{file_id}.meta.json"
        return JsonStore.load(meta_path, default=None)

    def mark_indexed(self, agent_id: str, file_id: str) -> None:
        meta_path = UPLOADS_DIR / agent_id / f"{file_id}.meta.json"
        meta = JsonStore.load(meta_path, default=None)
        if not meta:
            return

        meta["status"] = "indexed"
        meta["indexed_at"] = now_str()
        JsonStore.save(meta_path, meta)

    def mark_uploaded(self, agent_id: str, file_id: str) -> None:
        meta_path = UPLOADS_DIR / agent_id / f"{file_id}.meta.json"
        meta = JsonStore.load(meta_path, default=None)
        if not meta:
            return

        meta["status"] = "uploaded"
        meta["indexed_at"] = None
        JsonStore.save(meta_path, meta)

    def delete_file(self, agent_id: str, file_id: str) -> None:
        """
        只删除源文件和元数据，不处理向量。
        向量删除交给上层索引服务处理。
        """
        meta_path = UPLOADS_DIR / agent_id / f"{file_id}.meta.json"
        meta = JsonStore.load(meta_path, default=None)
        if not meta:
            return

        file_path = resolve_file_path(meta["file_path"], meta.get("agent_id"), meta.get("file_name"))
        if file_path.exists():
            file_path.unlink()

        if meta_path.exists():
            meta_path.unlink()