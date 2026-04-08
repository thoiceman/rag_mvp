from langchain_chroma import Chroma
from src.model.factory import get_embedding_model
from src.storage.paths import VECTOR_DB_DIR


class VectorStoreFactory:
    def get_store(self, collection_name: str) -> Chroma:
        return Chroma(
            collection_name=collection_name,
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=get_embedding_model(),
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