from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_community.retrievers import BM25Retriever
from app.models.factory import get_chat_model
from app.rag.vector_store import VectorStoreFactory
from app.services.agent_service import AgentService
from app.storage.paths import PROMPTS_DIR
from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("RagService")
settings = get_settings()


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
        # 强制关闭 RAG 内部模型的流式输出，防止其事件冒泡导致 Agent 回复重复
        self.model = get_chat_model(streaming=False)
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

    def _retrieve_docs(self, collection_name: str, query: str) -> list:
        """统一的文档检索入口，支持混合检索、MMR 等优化策略"""
        store = self.store_factory.get_store(collection_name)
        k = settings.SEARCH_K
        
        # 1. 基础配置
        mmr_enabled = settings.MMR_ENABLED
        multi_query_enabled = settings.MULTI_QUERY_ENABLED
        rerank_enabled = settings.RERANK_ENABLED
        parent_retriever_enabled = settings.PARENT_RETRIEVER_ENABLED
        hybrid_weight_dense = settings.HYBRID_WEIGHT_DENSE
        hybrid_weight_sparse = settings.HYBRID_WEIGHT_SPARSE
        
        # 2. 获取基础检索器
        if parent_retriever_enabled:
            base_retriever = self.store_factory.get_parent_retriever(collection_name)
        elif mmr_enabled:
            base_retriever = store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": k,
                    "fetch_k": settings.MMR_FETCH_K,
                    "lambda_mult": settings.MMR_LAMBDA
                }
            )
        else:
            base_retriever = store.as_retriever(search_kwargs={"k": k})

        # 3. 装饰检索器 (Multi-Query)
        if multi_query_enabled:
            base_retriever = MultiQueryRetriever.from_llm(
                retriever=base_retriever,
                llm=self.model
            )

        # 4. 装饰检索器 (Rerank/Compression)
        if rerank_enabled:
            compressor = LLMChainExtractor.from_llm(self.model)
            base_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )

        # 5. 混合检索逻辑 (如果启用且非空)
        try:
            # 仅在需要混合检索时获取全量数据
            if hybrid_weight_sparse > 0:
                all_docs_data = store.get()
                all_docs = []
                for i in range(len(all_docs_data["documents"])):
                    all_docs.append(
                        Document(
                            page_content=all_docs_data["documents"][i],
                            metadata=all_docs_data["metadatas"][i]
                        )
                    )
                
                if all_docs:
                    bm25_retriever = BM25Retriever.from_documents(all_docs)
                    bm25_retriever.k = k
                    
                    ensemble_retriever = EnsembleRetriever(
                        retrievers=[bm25_retriever, base_retriever],
                        weights=[hybrid_weight_sparse, hybrid_weight_dense]
                    )
                    return ensemble_retriever.invoke(query)
        except Exception as e:
            logger.warning(f"混合检索初始化失败，退回到单一检索: {e}")

        # 6. 执行检索
        if multi_query_enabled or mmr_enabled or rerank_enabled or parent_retriever_enabled:
            return base_retriever.invoke(query)

        # 7. 退回到基础带分数过滤的检索 (为了保持向后兼容的距离过滤)
        docs_and_scores = store.similarity_search_with_score(query, k=k)
        docs = []
        max_distance = settings.MAX_DISTANCE
        for doc, score in docs_and_scores:
            if score <= max_distance:
                docs.append(doc)
        return docs

    def ask(self, db, agent_id: str, question: str, history: list[dict] = None, session_id: str = None) -> dict:
        agent = self.agent_service.get_agent(db, agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到问题: {question[:50]}...")
        
        # 格式化对话历史
        history_text = format_history(history or [], limit=settings.HISTORY_LIMIT)

        # 【核心优化】基于历史对话重写查询语句，消除代词指代
        search_query = self._rewrite_query(question, history_text)

        # 使用统一检索入口
        docs = self._retrieve_docs(agent["vector_collection_name"], search_query)

        logger.info(f"检索到 {len(docs)} 条相关文档")
        context = format_docs(docs)

        # ===== 增加混合长记忆支持 =====
        summary = "暂无摘要"
        history_context = "暂无相关历史"
        first_question = "暂无"
        
        if session_id:
            # 引入 SessionService，避免循环引用可在方法内引入
            from app.services.session_service import SessionService
            session = SessionService().get_session(db, session_id)
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
                h_docs = [d for d, s in h_docs_scores if s <= settings.MAX_DISTANCE]
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

    def ask_stream(self, db, agent_id: str, question: str, history: list[dict] = None, session_id: str = None):
        """流式问答，返回 (references, stream_generator)"""
        agent = self.agent_service.get_agent(db, agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        logger.info(f"Agent {agent_id} 收到流式问题: {question[:50]}...")
        history_text = format_history(history or [], limit=rag_conf.get("history_limit", 5))

        search_query = self._rewrite_query(question, history_text)

        # 使用统一检索入口
        docs = self._retrieve_docs(agent["vector_collection_name"], search_query)

        logger.info(f"流式问答检索到 {len(docs)} 条相关文档")
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
            from app.services.session_service import SessionService
            session = SessionService().get_session(db, session_id)
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