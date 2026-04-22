from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# 获取项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    Values can be overridden by environment variables.
    """
    # App Settings
    APP_NAME: str = "RAG MVP"
    API_V1_STR: str = "/api/v1"
    UPLOAD_MAX_FILES: int = 20
    ALLOWED_FILE_TYPES: List[str] = ["txt", "md", "pdf", "docx"]
    
    # Model Settings
    CHAT_MODEL_NAME: str = "qwen3-max"
    EMBEDDING_MODEL_NAME: str = "text-embedding-v4"
    TEMPERATURE: float = 0.7
    
    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 80
    SEARCH_K: int = 4
    HISTORY_LIMIT: int = 5
    MAX_DISTANCE: float = 1.2
    
    # Hybrid Search (Dense + Sparse)
    HYBRID_WEIGHT_DENSE: float = 0.7
    HYBRID_WEIGHT_SPARSE: float = 0.3
    
    # Retrieval Strategy
    RERANK_ENABLED: bool = False
    MULTI_QUERY_ENABLED: bool = False
    MMR_ENABLED: bool = True
    MMR_LAMBDA: float = 0.5
    MMR_FETCH_K: int = 20
    
    # Parent Document Retrieval
    PARENT_RETRIEVER_ENABLED: bool = False
    PARENT_CHUNK_SIZE: int = 2000
    PARENT_CHUNK_OVERLAP: int = 200
    CHILD_CHUNK_SIZE: int = 400
    CHILD_CHUNK_OVERLAP: int = 50
    
    # Secrets (Loaded from .env)
    DASHSCOPE_API_KEY: Optional[str] = None
    SENIVERSE_API_KEY: Optional[str] = None
    
    # Paths
    BASE_DIR: Path = ROOT_DIR
    DATA_DIR: Path = ROOT_DIR / "data"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of Settings.
    """
    return Settings()
