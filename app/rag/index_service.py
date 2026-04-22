from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from app.rag.document_loader import DocumentLoader
from app.rag.splitter import get_text_splitters
from app.rag.vector_store import VectorStoreFactory
from app.services.file_service import FileService
from app.services.agent_service import AgentService
from app.storage.paths import resolve_file_path, PARENT_DOCS_DIR
from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("IndexService")
settings = get_settings()


class IndexService:
    def __init__(self):
        self.file_service = FileService()
        self.agent_service = AgentService()
        self.loader = DocumentLoader()
        self.md_splitter, self.rec_splitter = get_text_splitters()
        self.store_factory = VectorStoreFactory()

    def build_index(self, db, agent_id: str, file_id: str = None, progress_callback=None) -> dict:
        agent = self.agent_service.get_agent(db, agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            raise ValueError("Agent不存在")

        files = self.file_service.list_unindexed_files(db, agent_id)
        
        # 如果指定了 file_id，则仅过滤出该文件
        if file_id:
            files = [f for f in files if f.get("file_id") == file_id]

        if not files:
            logger.info(f"Agent {agent_id} 没有待处理的新文件")
            return {
                "agent_id": agent_id,
                "indexed_files": 0,
                "indexed_chunks": 0,
                "status": "no_new_files",
            }

        logger.info(f"Agent {agent_id} 开始索引，共 {len(files)} 个文件")
        all_docs = []
        indexed_file_ids = []

        store = self.store_factory.get_store(agent["vector_collection_name"])
        total_files = len(files)
        parent_retriever_enabled = settings.PARENT_RETRIEVER_ENABLED
        
        for i, file_meta in enumerate(files):
            file_id = file_meta["file_id"]
            file_name = file_meta["file_name"]
            
            if progress_callback:
                progress_callback(i / total_files, f"正在处理 ({i+1}/{total_files}): {file_name}")
            
            # 向量化前检查并清理旧数据（增量/重试逻辑）
            logger.info(f"检查并清理旧索引: {file_name} ({file_id})")
            try:
                # 直接通过 file_id 删除可能存在的旧向量，确保不重复
                self.store_factory.delete_by_file_id(agent["vector_collection_name"], file_id)
            except Exception as e:
                logger.warning(f"清理旧索引失败 (可能不存在): {str(e)}")

            abs_path = resolve_file_path(
                file_meta["file_path"],
                file_meta.get("agent_id"),
                file_meta.get("file_name"),
            )
            logger.debug(f"正在加载文件: {abs_path}")
            try:
                docs = self.loader.load_file(str(abs_path))
                if progress_callback:
                    progress_callback((i + 0.3) / total_files, f"文件读取完成: {file_name}")

                for doc in docs:
                    doc.metadata["agent_id"] = agent_id
                    doc.metadata["file_id"] = file_id
                    doc.metadata["file_name"] = file_name
                    doc.metadata["md5"] = file_meta.get("md5")

                if parent_retriever_enabled:
                    # 使用父文档检索器
                    retriever = self.store_factory.get_parent_retriever(agent["vector_collection_name"])
                    retriever.add_documents(docs)
                else:
                    # 原有的切片逻辑
                    split_docs = []
                    for doc in docs:
                        # 第一步：根据 Markdown 标题进行结构化切片
                        md_splits = self.md_splitter.split_text(doc.page_content)
                        # 第二步：对于结构化切片后依然过长的内容，使用字符切片器二次切分
                        rec_splits = self.rec_splitter.split_documents(md_splits)
                        
                        # 合并文档原本的 Metadata 和切片过程中产生的 Metadata (如 Header)
                        for chunk in rec_splits:
                            chunk.metadata.update(doc.metadata)
                            split_docs.append(chunk)
                    all_docs.extend(split_docs)
                
                indexed_file_ids.append(file_id)
                if progress_callback:
                    progress_callback((i + 0.7) / total_files, f"文件处理完成: {file_name}")
            except Exception as e:
                logger.error(f"处理文件 {file_name} 失败: {str(e)}")

        if not indexed_file_ids:
            logger.warning(f"Agent {agent_id} 没有有效文本内容")
            raise ValueError("没有可写入向量库的有效文本内容")

        if progress_callback:
            progress_callback(0.95, "正在写入向量库...")

        if not parent_retriever_enabled and all_docs:
            logger.info(f"Agent {agent_id} 开始写入向量库，共 {len(all_docs)} 个切片")
            store = self.store_factory.get_store(agent["vector_collection_name"])
            store.add_documents(all_docs)

        for file_id in indexed_file_ids:
            self.file_service.mark_indexed(db, agent_id, file_id)

        self.agent_service.update_agent(db, agent_id, knowledge_status="indexed")
        logger.info(f"Agent {agent_id} 索引构建成功")

        if progress_callback:
            progress_callback(1.0, "索引构建完成")

        return {
            "agent_id": agent_id,
            "indexed_files": len(indexed_file_ids),
            "indexed_chunks": len(all_docs),
            "status": "success",
        }

    def remove_index(self, db, agent_id: str, file_id: str) -> bool:
        """从向量库中移除指定文件的索引"""
        agent = self.agent_service.get_agent(db, agent_id)
        if not agent:
            return False
        
        logger.info(f"正在从向量库中移除文件索引: Agent={agent_id}, File={file_id}")
        try:
            self.store_factory.delete_by_file_id(agent["vector_collection_name"], file_id)
            return True
        except Exception as e:
            logger.error(f"移除索引失败: {str(e)}")
            return False