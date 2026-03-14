import logging
from urllib.parse import quote

import httpx

from second_brain.models import Document, SearchResult
from second_brain.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class VespaStorage(StorageBackend):
    def __init__(self, vespa_url: str):
        self.vespa_url = vespa_url.rstrip("/")

    def _doc_id(self, global_id: str) -> str:
        return quote(global_id, safe="")

    async def index_document(self, doc: Document, namespace: str = "default") -> None:
        doc_id = self._doc_id(doc.global_id)
        endpoint = f"{self.vespa_url}/document/v1/{namespace}/items/docid/{doc_id}"
        fields = doc.model_dump(exclude_none=True)
        fields["namespace"] = namespace
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json={"fields": fields},
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()

    async def index_documents(self, docs: list[Document], namespace: str = "default") -> int:
        indexed = 0
        for doc in docs:
            try:
                await self.index_document(doc, namespace)
                indexed += 1
            except Exception as e:
                logger.error(f"Failed to index {doc.global_id}: {e}")
        return indexed

    async def search(self, query: str, hits: int = 10, namespace: str = "default") -> list[SearchResult]:
        search_data = {
            "yql": f"select * from sources * where namespace contains '{namespace}' and rank({{targetHits:100}}nearestNeighbor(embedding,q), userQuery())",
            "hits": hits,
            "query": query,
            "type": "weakAnd",
            "ranking": "hybrid",
            "input.query(q)": f'embed(e5, "{query}")',
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.vespa_url}/search/",
                json=search_data,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        root = data.get("root", {})
        children = root.get("children", [])
        for hit in children:
            fields = hit.get("fields", {})
            relevance = hit.get("relevance", 0.0)
            match_features = fields.get("matchfeatures", {})
            last_seen = None
            if "last_seen" in fields:
                try:
                    last_seen = int(fields["last_seen"])
                except (ValueError, TypeError):
                    pass
            result = SearchResult(
                global_id=fields.get("global_id", ""),
                title=fields.get("title", ""),
                domain=fields.get("domain", ""),
                snippet=fields.get("snippet", ""),
                last_seen=last_seen,
                url=fields.get("url"),
                relevance=relevance,
                bm25_score=match_features.get("bm25(title)"),
                embedding_score=match_features.get("closeness(field, embedding)"),
            )
            results.append(result)
        logger.info(f"Search for '{query}' in ns '{namespace}' returned {len(results)} results")
        return results

    async def delete_document(self, global_id: str, namespace: str = "default") -> None:
        doc_id = self._doc_id(global_id)
        endpoint = f"{self.vespa_url}/document/v1/{namespace}/items/docid/{doc_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(endpoint, timeout=10.0)
            response.raise_for_status()

    async def delete_all_in_namespace(self, namespace: str) -> None:
        endpoint = f"{self.vespa_url}/document/v1/{namespace}/items/docid/?selection=true&cluster=docs"
        async with httpx.AsyncClient() as client:
            response = await client.delete(endpoint, timeout=30.0)
            response.raise_for_status()

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.vespa_url}/state/v1/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def count_documents(self, namespace: str = "default") -> int:
        search_data = {
            "yql": f"select * from sources * where namespace contains '{namespace}'",
            "hits": 0,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.vespa_url}/search/",
                    json=search_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("root", {}).get("fields", {}).get("totalCount", 0)
        except Exception:
            return 0
