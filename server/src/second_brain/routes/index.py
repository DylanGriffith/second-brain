import logging
from fastapi import APIRouter, Request
from second_brain.models import IndexRequest, IndexResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/v1/documents", response_model=IndexResponse)
async def index_documents(request: Request, body: IndexRequest) -> IndexResponse:
    storage = request.app.state.storage
    settings = request.app.state.settings
    namespace = settings.default_namespace
    errors = 0
    indexed = 0
    for doc in body.documents:
        try:
            await storage.index_document(doc, namespace)
            indexed += 1
        except Exception as e:
            logger.error(f"Failed to index {doc.global_id}: {e}")
            errors += 1
    return IndexResponse(indexed=indexed, errors=errors)
