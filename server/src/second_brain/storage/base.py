from abc import ABC, abstractmethod
from second_brain.models import Document, SearchResult


class StorageBackend(ABC):
    @abstractmethod
    async def index_document(self, doc: Document, namespace: str = "default") -> None:
        pass

    @abstractmethod
    async def index_documents(self, docs: list[Document], namespace: str = "default") -> int:
        pass

    @abstractmethod
    async def search(self, query: str, hits: int = 10, namespace: str = "default") -> list[SearchResult]:
        pass

    @abstractmethod
    async def delete_document(self, global_id: str, namespace: str = "default") -> None:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    async def count_documents(self, namespace: str = "default") -> int:
        pass
