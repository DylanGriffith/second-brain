from fastapi import APIRouter, Request
from second_brain.models import StatusResponse

router = APIRouter()


@router.get("/api/v1/status", response_model=StatusResponse)
async def status(request: Request) -> StatusResponse:
    storage = request.app.state.storage
    settings = request.app.state.settings
    namespace = settings.default_namespace
    healthy = await storage.health_check()
    count = await storage.count_documents(namespace)
    return StatusResponse(
        indexed_documents_count=count,
        vespa_healthy=healthy,
        vespa_url=settings.vespa_url,
    )
