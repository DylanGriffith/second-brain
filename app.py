"""FastAPI application for Second Brain search."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Set

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import (
    LOG_LEVEL,
    STATE_FILE_PATH,
    SYNC_INTERVAL_SECONDS,
    VESPA_URL,
)
from indexer import sync_all_sources
from searcher import SearchResult, hybrid_search
from state import load_indexed_items, save_indexed_items

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
indexed_items: Set[str] = set()
sync_lock = asyncio.Lock()
last_sync_time: Optional[datetime] = None
sync_error_count: int = 0


async def perform_sync():
    """Perform a sync of all active data sources."""
    global last_sync_time, sync_error_count

    if sync_lock.locked():
        logger.warning("Previous sync still running, skipping")
        return

    async with sync_lock:
        try:
            logger.info("Starting data source sync...")
            stats = await sync_all_sources(
                VESPA_URL,
                indexed_items,
                STATE_FILE_PATH
            )
            last_sync_time = datetime.now()
            sync_error_count = stats.get("errors", 0)
            logger.info(
                f"Sync complete: {stats['new_items']} new items indexed, "
                f"{stats['errors']} errors, "
                f"{stats['sources_synced']} sources synced"
            )
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sync_error_count += 1


async def periodic_sync():
    """Background task that periodically syncs all data sources."""
    # Initial sync on startup
    await perform_sync()

    # Periodic sync
    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        await perform_sync()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    global indexed_items
    indexed_items = load_indexed_items(STATE_FILE_PATH)
    logger.info(f"Loaded {len(indexed_items)} indexed items from state file")

    # Start background sync task
    sync_task = asyncio.create_task(periodic_sync())
    logger.info(f"Background sync started (interval: {SYNC_INTERVAL_SECONDS}s)")

    yield

    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        logger.info("Background sync task cancelled")

    # Save state one last time
    save_indexed_items(indexed_items, STATE_FILE_PATH)
    logger.info("State saved on shutdown")


# Create FastAPI app
app = FastAPI(
    title="Second Brain Search",
    description="Search your Chrome browsing history with hybrid search",
    version="1.0.0",
    lifespan=lifespan
)

# Configure templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the search UI."""
    return templates.TemplateResponse("index.html.jinja", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", hits: int = 10):
    """Execute a hybrid search query and render results."""
    if not q or not q.strip():
        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": None,
            "results": None,
            "count": 0,
            "error": None
        })

    try:
        results = await hybrid_search(VESPA_URL, q, hits)
        search_results = []

        for r in results:
            result = SearchResult(**r)
            # Convert to dict and add formatted timestamp
            result_dict = result.model_dump()
            if result.last_seen:
                dt = datetime.fromtimestamp(result.last_seen / 1000)
                result_dict["last_seen_formatted"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result_dict["last_seen_formatted"] = None
            search_results.append(result_dict)

        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": q,
            "results": search_results,
            "count": len(search_results),
            "error": None
        })
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return templates.TemplateResponse("index.html.jinja", {
            "request": request,
            "query": q,
            "results": None,
            "count": 0,
            "error": str(e)
        })


@app.get("/status")
async def status():
    """Get sync status."""
    return {
        "indexed_items_count": len(indexed_items),
        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
        "sync_error_count": sync_error_count,
        "sync_in_progress": sync_lock.locked(),
        "vespa_url": VESPA_URL,
        "sync_interval_seconds": SYNC_INTERVAL_SECONDS,
    }
