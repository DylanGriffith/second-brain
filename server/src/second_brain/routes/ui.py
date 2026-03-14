from datetime import datetime
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html.jinja", {"request": request})


@router.get("/search", response_class=HTMLResponse)
async def search_ui(request: Request, q: str = "", hits: int = 10):
    if not q or not q.strip():
        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": None,
            "results": None,
            "count": 0,
            "error": None,
        })
    storage = request.app.state.storage
    settings = request.app.state.settings
    namespace = settings.default_namespace
    try:
        results = await storage.search(q, hits=hits, namespace=namespace)
        search_results = []
        for r in results:
            result_dict = r.model_dump()
            if r.last_seen:
                dt = datetime.fromtimestamp(r.last_seen / 1000)
                result_dict["last_seen_formatted"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result_dict["last_seen_formatted"] = None
            search_results.append(result_dict)
        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": q,
            "results": search_results,
            "count": len(search_results),
            "error": None,
        })
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": q,
            "results": None,
            "count": 0,
            "error": str(e),
        })
