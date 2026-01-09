"""Vespa hybrid search module."""

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Pydantic models
class SearchRequest(BaseModel):
    query: str
    hits: int = 10


class SearchResult(BaseModel):
    global_id: str
    title: str
    domain: str
    snippet: str
    last_seen: Optional[int] = None
    url: Optional[str] = None
    content: Optional[str] = None
    relevance: float
    bm25_score: Optional[float] = None
    embedding_score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    count: int


async def hybrid_search(
    vespa_url: str,
    query: str,
    hits: int = 10
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search (BM25 + embeddings) against Vespa.

    Args:
        vespa_url: Base URL of Vespa API
        query: Search query string
        hits: Maximum number of results to return

    Returns:
        List of result dictionaries with fields:
        - global_id: Global identifier
        - title: Document title
        - domain: Document domain
        - snippet: Short snippet
        - last_seen: Timestamp when last seen
        - url: Document URL (optional, for websites)
        - content: Full content (optional)
        - relevance: Overall relevance score
        - bm25_score: BM25 text matching score (optional)
        - embedding_score: Semantic similarity score (optional)

    Raises:
        httpx.HTTPError: If search request fails
    """
    search_data = {
        "yql": "select * from sources * where rank({targetHits:100}nearestNeighbor(embedding,q), userQuery())",
        "hits": hits,
        "query": query,
        "type": "weakAnd",
        "ranking": "hybrid",
        "input.query(q)": f'embed(e5, "{query}")'
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vespa_url}/search/",
            json=search_data,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

    results = []

    # Parse Vespa response
    root = data.get("root", {})
    children = root.get("children", [])

    for hit in children:
        fields = hit.get("fields", {})
        relevance = hit.get("relevance", 0.0)
        match_features = hit.get("matchfeatures", {})

        # Try to parse last_seen as int, fall back to None if not present or invalid
        last_seen = None
        if "last_seen" in fields:
            try:
                last_seen = int(fields["last_seen"])
            except (ValueError, TypeError):
                pass

        result = {
            "global_id": fields.get("global_id", ""),
            "title": fields.get("title", ""),
            "domain": fields.get("domain", ""),
            "snippet": fields.get("snippet", ""),
            "last_seen": last_seen,
            "url": fields.get("url"),
            "content": fields.get("content"),
            "relevance": relevance,
            "bm25_score": match_features.get("bm25(title)"),
            "embedding_score": match_features.get("closeness(field, embedding)")
        }

        results.append(result)

    logger.info(f"Search for '{query}' returned {len(results)} results")

    return results
