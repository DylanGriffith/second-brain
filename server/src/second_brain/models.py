from typing import Optional
from pydantic import BaseModel


class Document(BaseModel):
    global_id: str
    title: str
    domain: str
    snippet: str
    last_seen: int  # unix millis
    url: Optional[str] = None
    content: Optional[str] = None


class IndexRequest(BaseModel):
    documents: list[Document]


class IndexResponse(BaseModel):
    indexed: int
    errors: int


class SearchResult(BaseModel):
    global_id: str
    title: str
    domain: str
    snippet: str
    last_seen: Optional[int] = None
    url: Optional[str] = None
    relevance: float
    bm25_score: Optional[float] = None
    embedding_score: Optional[float] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    count: int


class StatusResponse(BaseModel):
    indexed_documents_count: int
    vespa_healthy: bool
    vespa_url: str
