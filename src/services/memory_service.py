import threading
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from src.model.factory import get_chat_model
from src.rag.vector_store import VectorStoreFactory
from src.services.session_service import SessionService
from src.storage.paths import PROMPTS_DIR
from src.utils.logger import get_logger

logger = get_logger("MemoryService")


class MemoryService:
    def __init__(self):
        self.session_service = SessionService()
        self.store_factory = VectorStoreFactory()
        self.model = get_chat_model()
        self.summary_template = (PROMPTS_DIR / "session_summary_prompt.txt").read_text(encoding="utf-8")

    def process_memory_async(self, session_id: str):
        """异步处理记忆：向量化历史记录与生成滚动摘要"""
        threading.Thread(target=self._process_memory, args=(session_id,)).start()

    def _process_memory(self, session_id: str):
        try:
            session = self.session_service.get_session(session_id)
            if not session:
                return

            messages = session.get("messages", [])
            if not messages:
                return

            vectorized_index = session.get("vectorized_index", 0)
            summarized_index = session.get("summarized_index", 0)
            summary = session.get("summary", "暂无摘要")

            # 1. 向量化历史记录 (将对话合并为 QA 对进行切片)
            docs_to_add = []
            new_vectorized_index = vectorized_index
            for i in range(vectorized_index, len(messages) - 1, 2):
                if messages[i]["role"] == "user" and messages[i+1]["role"] == "assistant":
                    content = f"User: {messages[i]['content']}\nAssistant: {messages[i+1]['content']}"
                    doc = Document(page_content=content, metadata={"session_id": session_id, "msg_index": i})
                    docs_to_add.append(doc)
                    new_vectorized_index = i + 2
            
            if docs_to_add:
                collection_name = f"history_{session_id}"
                store = self.store_factory.get_store(collection_name)
                store.add_documents(docs_to_add)
                logger.info(f"Session {session_id} 成功向量化 {len(docs_to_add)} 条对话对")

            # 2. 滚动摘要 (保留最近 5 条即约 2 个 QA 对不摘要，其余全部压缩进全局摘要)
            target_summarize_index = max(0, len(messages) - 5)
            new_summarized_index = summarized_index
            new_summary = summary

            # 至少积累了 2 个对话对再触发一次摘要，避免频繁调用大模型
            if target_summarize_index - summarized_index >= 4:
                msgs_to_summarize = messages[summarized_index:target_summarize_index]
                new_msgs_text = "\n".join([f"{m['role']}: {m['content']}" for m in msgs_to_summarize])
                
                prompt = PromptTemplate.from_template(self.summary_template)
                chain = prompt | self.model | StrOutputParser()
                
                new_summary = chain.invoke({
                    "summary": summary,
                    "new_messages": new_msgs_text
                }).strip()
                new_summarized_index = target_summarize_index
                logger.info(f"Session {session_id} 全局摘要已更新")

            # 3. 保存更新后的状态
            if new_vectorized_index != vectorized_index or new_summarized_index != summarized_index:
                self.session_service.update_memory_state(
                    session_id, new_summary, new_summarized_index, new_vectorized_index
                )

        except Exception as e:
            logger.error(f"处理Session {session_id} 的记忆时发生错误: {e}")
