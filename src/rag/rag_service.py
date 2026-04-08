from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.model.factory import get_chat_model
from src.rag.vector_store import VectorStoreFactory
from src.services.agent_service import AgentService
from src.storage.paths import PROMPTS_DIR, CONFIG_DIR
from src.utils.config_loader import ConfigLoader
from src.utils.logger import get_logger

logger = get_logger("RagService")

rag_conf = ConfigLoader.load_yaml(CONFIG_DIR / "rag.yml")


def format_docs(docs) -> str:
    blocks = []
    for doc in docs:
        source = doc.metadata.get("file_name") or doc.metadata.get("source") or "未知来源"
        page = doc.metadata.get("page")
        title = f"来源：{source}" if page is None else f"来源：{source} 第{page}页"
        blocks.append(f"【{title}】{doc.page_content}")
    return "".join(blocks)


def format_history(messages: list[dict], limit: int = 5) -> str:
    """格式化对话历史，仅取最后 N 条"""
    if not messages:
        return "暂无对话历史"

    # 只取最后 N 条
    recent = messages[-limit:]
    history_str = ""
    for msg in recent:
        role = "用户" if msg["role"] == "user" else msg.get("agent_name", "AI")
        history_str += f"{role}: {msg['content']}\n"
    return history_str


class RagService:
    def __init__(self):
        self.model = get_chat_model()
        self.agent_service = AgentService()
        self.store_factory = VectorStoreFactory()
        self.rag_template = (PROMPTS_DIR / "rag_qa_prompt.txt").read_text(encoding="utf-8")

    def ask(self, agent_id: str, question: str, history: list[dict] = None) -> dict:
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到问题: {question[:50]}...")
        
        # 格式化对话历史
        history_text = format_history(history or [], limit=rag_conf.get("history_limit", 5))

        store = self.store_factory.get_store(agent["vector_collection_name"])
        # 使用带分数的检索，以便过滤掉相关性低的文档（Chroma 默认使用 L2 距离，越小越相关）
        docs_and_scores = store.similarity_search_with_score(question, k=rag_conf.get("search_k", 4))
        
        docs = []
        max_distance = rag_conf.get("max_distance", 1.2)
        for doc, score in docs_and_scores:
            if score <= max_distance:
                docs.append(doc)
            else:
                logger.debug(f"过滤掉不相关的文档，距离为 {score:.4f}: {doc.page_content[:30]}...")

        logger.info(f"检索到 {len(docs)} 条相关文档 (已过滤距离 > {max_distance})")
        context = format_docs(docs)

        prompt = PromptTemplate.from_template(self.rag_template)
        chain = prompt | self.model | StrOutputParser()
        answer = chain.invoke({
            "agent_name": agent["name"],
            "system_prompt": agent["system_prompt"],
            "context": context,
            "history": history_text,
            "question": question,
        })
        logger.info("LLM 回复生成成功")

        references = []
        for doc in docs:
            references.append({
                "file_name": doc.metadata.get("file_name") or doc.metadata.get("source") or "未知来源",
                "page": doc.metadata.get("page", "N/A"),
                "preview": doc.page_content[:220],
            })

        return {
            "answer": answer,
            "references": references,
            "hit_count": len(docs),
        }

    def ask_stream(self, agent_id: str, question: str, history: list[dict] = None):
        """流式问答，返回 (references, stream_generator)"""
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到流式问题: {question[:50]}...")
        history_text = format_history(history or [], limit=rag_conf.get("history_limit", 5))

        store = self.store_factory.get_store(agent["vector_collection_name"])
        docs_and_scores = store.similarity_search_with_score(question, k=rag_conf.get("search_k", 4))
        
        docs = []
        max_distance = rag_conf.get("max_distance", 1.2)
        for doc, score in docs_and_scores:
            if score <= max_distance:
                docs.append(doc)
            else:
                logger.debug(f"过滤掉不相关的文档，距离为 {score:.4f}: {doc.page_content[:30]}...")

        logger.info(f"流式问答检索到 {len(docs)} 条相关文档 (已过滤距离 > {max_distance})")
        context = format_docs(docs)

        references = []
        for doc in docs:
            references.append({
                "file_name": doc.metadata.get("file_name") or doc.metadata.get("source") or "未知来源",
                "page": doc.metadata.get("page", "N/A"),
                "preview": doc.page_content[:220],
            })

        prompt = PromptTemplate.from_template(self.rag_template)
        chain = prompt | self.model | StrOutputParser()
        
        # 返回元数据和流生成器
        stream_gen = chain.stream({
            "agent_name": agent["name"],
            "system_prompt": agent["system_prompt"],
            "context": context,
            "history": history_text,
            "question": question,
        })
        
        return {
            "references": references,
            "hit_count": len(docs),
            "stream": stream_gen
        }