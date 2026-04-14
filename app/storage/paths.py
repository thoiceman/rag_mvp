from pathlib import Path

# src 目录
SRC_DIR = Path(__file__).resolve().parent.parent
# 项目根目录
BASE_DIR = SRC_DIR.parent

DATA_DIR = BASE_DIR / "data"
AGENTS_DIR = DATA_DIR / "agents"
UPLOADS_DIR = DATA_DIR / "uploads"
SESSIONS_DIR = DATA_DIR / "sessions"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

PROMPTS_DIR = SRC_DIR / "prompts"
CONFIG_DIR = SRC_DIR / "config"


def ensure_dirs() -> None:
    for path in [DATA_DIR, AGENTS_DIR, UPLOADS_DIR, SESSIONS_DIR, VECTOR_DB_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def resolve_file_path(stored_path: str, agent_id: str = None, file_name: str = None) -> Path:
    """解析 meta.json 中存储的文件路径，兼容相对路径和旧版绝对路径（含跨平台迁移场景）。"""
    # 统一路径分隔符，将 Windows 的 \ 替换为 /
    # 在 Path 对象解析时，/ 会被自动处理为当前系统的分隔符
    normalized_path = stored_path.replace("\\", "/")
    p = Path(normalized_path)

    if not p.is_absolute():
        return BASE_DIR / p

    # 绝对路径检查，若存在则直接返回
    if p.exists():
        return p

    # 旧版绝对路径（如从 Windows 迁移到 macOS），尝试按已知目录结构重建
    if agent_id and file_name:
        candidate = UPLOADS_DIR / agent_id / file_name
        if candidate.exists():
            return candidate

    return p