import os
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from app.storage.paths import CONFIG_DIR
from app.utils.config_loader import ConfigLoader
model_conf = ConfigLoader.load_yaml(CONFIG_DIR / "model.yml")
def check_api_ket_set():
    """
    检查环境变量是否设置，并校验 API Key 的有效性（初步校验格式）
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "未找到 DASHSCOPE_API_KEY 环境变量。\n"
            "请参考 .env.example 文件在当前目录下创建 .env 文件，或在系统环境变量中设置。"
        )
    
    # 简单的格式校验：DashScope 的 key 通常以 sk- 开头
    if not api_key.startswith("sk-"):
        raise EnvironmentError("DASHSCOPE_API_KEY 格式不正确，请检查您的 API Key。")
        
    return api_key
def get_chat_model(streaming: bool = True):
    """
    获取百炼 Tongyi 聊天模型（LangChain 1.x 写法）
    """
    api_key = check_api_ket_set()
    return ChatTongyi(
        model_name=model_conf["chat_model_name"],
        dashscope_api_key=api_key,
        temperature=model_conf.get("temperature", 0.7),
        streaming=streaming,
    )

def get_embedding_model():
    """
    获取向量模型（DashScope Embedding）
    """
    api_key = check_api_ket_set()
    return DashScopeEmbeddings(
        model=model_conf["embedding_model_name"],
        dashscope_api_key=api_key,
    )


