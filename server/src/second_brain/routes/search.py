import logging
from fastapi import APIRouter, Request, Query
from second_brain.models import SearchResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/v1/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: str = Query(..., description="Search query"),
    hits: int = Query(10, description="Number of results"),
) -> SearchResponse:
    storage = request.app.state.storage
    settings = request.app.state.settings
    namespace = settings.default_namespace
    results = await storage.search(q, hits=hits, namespace=namespace)
    return SearchResponse(results=results, query=q, count=len(results))
