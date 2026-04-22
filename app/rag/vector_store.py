from langchain_chroma import Chroma
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.factory import get_embedding_model
from app.storage.paths import VECTOR_DB_DIR, PARENT_DOCS_DIR
from app.core.config import get_settings

settings = get_settings()


class VectorStoreFactory:
    def get_store(self, collection_name: str) -> Chroma:
        return Chroma(
            collection_name=collection_name,
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=get_embedding_model(),
        )

    def get_parent_retriever(self, collection_name: str) -> ParentDocumentRetriever:
        """获取父文档检索器"""
        store = self.get_store(collection_name)
        
        # 为每个 collection 创建独立的父文档存储目录
        child_dir = PARENT_DOCS_DIR / collection_name
        child_dir.mkdir(parents=True, exist_ok=True)
        
        fs = LocalFileStore(str(child_dir))
        docstore = create_kv_docstore(fs)
        
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.PARENT_CHUNK_SIZE,
            chunk_overlap=settings.PARENT_CHUNK_OVERLAP
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHILD_CHUNK_SIZE,
            chunk_overlap=settings.CHILD_CHUNK_OVERLAP
        )
        
        return ParentDocumentRetriever(
            vectorstore=store,
            docstore=docstore,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter
        )

    def delete_by_file_id(self, collection_name: str, file_id: str) -> None:
        store = self.get_store(collection_name)
        try:
            store._collection.delete(where={"file_id": file_id})
        except Exception:
            pass

    def clear_collection(self, collection_name: str) -> None:
        store = self.get_store(collection_name)
        try:
            all_data = store.get()
            ids = all_data.get("ids", [])
            if ids:
                store.delete(ids=ids)
        except Exception:
            pass