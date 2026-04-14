import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JsonStore:
    @staticmethod
    def load(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default

    @staticmethod
    def save(path: Path, data: Any) -> None:
        """原子化写入 JSON 文件：先写临时文件，再重命名。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 tempfile 创建临时文件，确保在同一文件系统中以支持原子 rename
        dir_name = path.parent
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            temp_name = tf.name
        
        try:
            # 原子替换
            os.replace(temp_name, path)
        except Exception as e:
            # 如果失败，清理临时文件
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise e