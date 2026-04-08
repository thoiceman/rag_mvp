import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from src.storage.paths import DATA_DIR


def get_logger(name: str = "custom_rag_platform") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # 1. 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 文件输出（按天轮转，保留 30 天）
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用 TimedRotatingFileHandler:
    # - when="midnight": 每天午夜轮转
    # - backupCount=30: 保留 30 份旧日志
    # 强制转为 str 避免在某些 Python 版本下兼容性问题
    file_handler = TimedRotatingFileHandler(
        str(log_dir / "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger