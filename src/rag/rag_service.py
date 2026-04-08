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
        self.rewrite_template = (PROMPTS_DIR / "query_rewrite_prompt.txt").read_text(encoding="utf-8")

    def _rewrite_query(self, question: str, history_text: str) -> str:
        """根据历史对话重写用户问题，解决代词指代和省略主语的问题"""
        if not history_text or history_text == "暂无对话历史":
            return question

        prompt = PromptTemplate.from_template(self.rewrite_template)
        chain = prompt | self.model | StrOutputParser()
        
        try:
            rewritten_query = chain.invoke({
                "history": history_text,
                "question": question,
            }).strip()
            
            logger.info(f"查询重写完成: 原问题=[{question}] -> 新问题=[{rewritten_query}]")
            return rewritten_query
        except Exception as e:
            logger.error(f"查询重写失败，降级使用原问题: {e}")
            return question

    def ask(self, agent_id: str, question: str, history: list[dict] = None, session_id: str = None) -> dict:
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到问题: {question[:50]}...")
        
        # 格式化对话历史
        history_text = format_history(history or [], limit=rag_conf.get("history_limit", 5))

        # 【核心优化】基于历史对话重写查询语句，消除代词指代
        search_query = self._rewrite_query(question, history_text)

        store = self.store_factory.get_store(agent["vector_collection_name"])
        # 使用带分数的检索，以便过滤掉相关性低的文档（Chroma 默认使用 L2 距离，越小越相关）
        docs_and_scores = store.similarity_search_with_score(search_query, k=rag_conf.get("search_k", 4))
        
        docs = []
        max_distance = rag_conf.get("max_distance", 1.2)
        for doc, score in docs_and_scores:
            if score <= max_distance:
                docs.append(doc)
            else:
                logger.debug(f"过滤掉不相关的文档，距离为 {score:.4f}: {doc.page_content[:30]}...")

        logger.info(f"检索到 {len(docs)} 条相关文档 (已过滤距离 > {max_distance})")
        context = format_docs(docs)

        # ===== 增加混合长记忆支持 =====
        summary = "暂无摘要"
        history_context = "暂无相关历史"
        first_question = "暂无"
        
        if session_id:
            # 引入 SessionService，避免循环引用可在方法内引入
            from src.services.session_service import SessionService
            session = SessionService().get_session(session_id)
            if session:
                summary = session.get("summary", "暂无摘要")
                messages = session.get("messages", [])
                if messages:
                    # 找到用户的第一条提问作为初始诉求
                    for msg in messages:
                        if msg["role"] == "user":
                            first_question = msg["content"]
                            break
            
            # 从向量化历史库检索过去的对话细节
            try:
                history_store = self.store_factory.get_store(f"history_{session_id}")
                h_docs_scores = history_store.similarity_search_with_score(search_query, k=2)
                # 同样的距离过滤机制
                h_docs = [d for d, s in h_docs_scores if s <= rag_conf.get("max_distance", 1.2)]
                if h_docs:
                    history_context = "\n".join([f"【历史片段】{d.page_content}" for d in h_docs])
            except Exception as e:
                logger.warning(f"检索历史对话异常: {e}")

        prompt = PromptTemplate.from_template(self.rag_template)
        chain = prompt | self.model | StrOutputParser()
        answer = chain.invoke({
            "agent_name": agent["name"],
            "system_prompt": agent["system_prompt"],
            "first_question": first_question,
            "summary": summary,
            "context": context,
            "history_context": history_context,
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

    def ask_stream(self, agent_id: str, question: str, history: list[dict] = None, session_id: str = None):
        """流式问答，返回 (references, stream_generator)"""
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到流式问题: {question[:50]}...")
        history_text = format_history(history or [], limit=rag_conf.get("history_limit", 5))

        search_query = self._rewrite_query(question, history_text)

        store = self.store_factory.get_store(agent["vector_collection_name"])
        docs_and_scores = store.similarity_search_with_score(search_query, k=rag_conf.get("search_k", 4))
        
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

        # ===== 增加混合长记忆支持 =====
        summary = "暂无摘要"
        history_context = "暂无相关历史"
        first_question = "暂无"

        if session_id:
            from src.services.session_service import SessionService
            session = SessionService().get_session(session_id)
            if session:
                summary = session.get("summary", "暂无摘要")
                messages = session.get("messages", [])
                if messages:
                    for msg in messages:
                        if msg["role"] == "user":
                            first_question = msg["content"]
                            break
            
            try:
                history_store = self.store_factory.get_store(f"history_{session_id}")
                h_docs_scores = history_store.similarity_search_with_score(search_query, k=2)
                h_docs = [d for d, s in h_docs_scores if s <= rag_conf.get("max_distance", 1.2)]
                if h_docs:
                    history_context = "\n".join([f"【历史片段】{d.page_content}" for d in h_docs])
            except Exception as e:
                logger.warning(f"检索历史对话异常: {e}")

        prompt = PromptTemplate.from_template(self.rag_template)
        chain = prompt | self.model | StrOutputParser()
        
        # 返回元数据和流生成器
        stream_gen = chain.stream({
            "agent_name": agent["name"],
            "system_prompt": agent["system_prompt"],
            "first_question": first_question,
            "summary": summary,
            "context": context,
            "history_context": history_context,
            "history": history_text,
            "question": question,
        })
        
        return {
            "references": references,
            "hit_count": len(docs),
            "stream": stream_gen
        }