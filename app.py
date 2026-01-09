"""FastAPI application for Second Brain search."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Set

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from config import (
    CHROME_HISTORY_PATH,
    LOG_LEVEL,
    STATE_FILE_PATH,
    SYNC_INTERVAL_SECONDS,
    VESPA_URL,
)
from indexer import sync_chrome_history
from searcher import SearchRequest, SearchResponse, SearchResult, hybrid_search
from state import load_indexed_urls, save_indexed_urls

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
indexed_urls: Set[str] = set()
sync_lock = asyncio.Lock()
last_sync_time: Optional[datetime] = None
sync_error_count: int = 0


async def perform_sync():
    """Perform a Chrome history sync."""
    global last_sync_time, sync_error_count

    if sync_lock.locked():
        logger.warning("Previous sync still running, skipping")
        return

    async with sync_lock:
        try:
            logger.info("Starting Chrome history sync...")
            stats = await sync_chrome_history(
                CHROME_HISTORY_PATH,
                VESPA_URL,
                indexed_urls,
                STATE_FILE_PATH
            )
            last_sync_time = datetime.now()
            sync_error_count = stats.get("errors", 0)
            logger.info(
                f"Sync complete: {stats['new_urls']} new URLs indexed, "
                f"{stats['errors']} errors"
            )
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sync_error_count += 1


async def periodic_chrome_sync():
    """Background task that periodically syncs Chrome history."""
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
    global indexed_urls
    indexed_urls = load_indexed_urls(STATE_FILE_PATH)
    logger.info(f"Loaded {len(indexed_urls)} indexed URLs from state file")

    # Start background sync task
    sync_task = asyncio.create_task(periodic_chrome_sync())
    logger.info(f"Background sync started (interval: {SYNC_INTERVAL_SECONDS}s)")

    yield

    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        logger.info("Background sync task cancelled")

    # Save state one last time
    save_indexed_urls(indexed_urls, STATE_FILE_PATH)
    logger.info("State saved on shutdown")


# Create FastAPI app
app = FastAPI(
    title="Second Brain Search",
    description="Search your Chrome browsing history with hybrid search",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the search UI."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Second Brain Search</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        h1 {
            font-size: 2em;
            margin-bottom: 10px;
            color: #2c3e50;
        }

        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 0.95em;
        }

        .search-form {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }

        .search-input {
            flex: 1;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
            outline: none;
            transition: border-color 0.3s;
        }

        .search-input:focus {
            border-color: #3498db;
        }

        .search-button {
            padding: 12px 24px;
            font-size: 16px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .search-button:hover {
            background: #2980b9;
        }

        .search-button:disabled {
            background: #95a5a6;
            cursor: not-allowed;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }

        .error {
            background: #e74c3c;
            color: white;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }

        .results-header {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 15px;
        }

        .result {
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            transition: box-shadow 0.3s;
        }

        .result:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .result-title {
            font-size: 1.2em;
            margin-bottom: 5px;
        }

        .result-title a {
            color: #3498db;
            text-decoration: none;
        }

        .result-title a:hover {
            text-decoration: underline;
        }

        .result-url {
            color: #27ae60;
            font-size: 0.9em;
            margin-bottom: 8px;
            word-break: break-all;
        }

        .result-domain {
            display: inline-block;
            background: #ecf0f1;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            color: #7f8c8d;
            margin-bottom: 8px;
        }

        .result-scores {
            font-size: 0.85em;
            color: #95a5a6;
            margin-top: 8px;
        }

        .no-results {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Second Brain Search</h1>
        <p class="subtitle">Search your Chrome browsing history with hybrid search (BM25 + embeddings)</p>

        <form class="search-form" id="searchForm">
            <input
                type="text"
                class="search-input"
                id="searchInput"
                placeholder="Search your browsing history..."
                autofocus
                required
            >
            <button type="submit" class="search-button" id="searchButton">Search</button>
        </form>

        <div id="errorContainer"></div>
        <div id="resultsContainer"></div>
    </div>

    <script>
        const searchForm = document.getElementById('searchForm');
        const searchInput = document.getElementById('searchInput');
        const searchButton = document.getElementById('searchButton');
        const resultsContainer = document.getElementById('resultsContainer');
        const errorContainer = document.getElementById('errorContainer');

        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const query = searchInput.value.trim();
            if (!query) return;

            // Clear previous results and errors
            resultsContainer.innerHTML = '<div class="loading">Searching...</div>';
            errorContainer.innerHTML = '';
            searchButton.disabled = true;

            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query, hits: 10 })
                });

                if (!response.ok) {
                    throw new Error(`Search failed: ${response.statusText}`);
                }

                const data = await response.json();
                displayResults(data);

            } catch (error) {
                errorContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                resultsContainer.innerHTML = '';
            } finally {
                searchButton.disabled = false;
            }
        });

        function displayResults(data) {
            const { results, query, count } = data;

            if (results.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="no-results">
                        No results found for "${escapeHtml(query)}"
                    </div>
                `;
                return;
            }

            let html = `<div class="results-header">Found ${count} result(s) for "${escapeHtml(query)}"</div>`;

            results.forEach(result => {
                const scores = [];
                if (result.relevance) {
                    scores.push(`Relevance: ${result.relevance.toFixed(3)}`);
                }
                if (result.bm25_score) {
                    scores.push(`BM25: ${result.bm25_score.toFixed(2)}`);
                }
                if (result.embedding_score) {
                    scores.push(`Embedding: ${result.embedding_score.toFixed(3)}`);
                }

                html += `
                    <div class="result">
                        <div class="result-title">
                            <a href="${escapeHtml(result.url)}" target="_blank" rel="noopener noreferrer">
                                ${escapeHtml(result.title || result.url)}
                            </a>
                        </div>
                        <div class="result-url">${escapeHtml(result.url)}</div>
                        <div class="result-domain">${escapeHtml(result.domain)}</div>
                        ${scores.length > 0 ? `<div class="result-scores">${scores.join(' • ')}</div>` : ''}
                    </div>
                `;
            });

            resultsContainer.innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
    """
    return html_content


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Execute a hybrid search query."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        results = await hybrid_search(VESPA_URL, request.query, request.hits)

        return SearchResponse(
            results=[SearchResult(**r) for r in results],
            query=request.query,
            count=len(results)
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/status")
async def status():
    """Get sync status."""
    return {
        "indexed_urls_count": len(indexed_urls),
        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
        "sync_error_count": sync_error_count,
        "sync_in_progress": sync_lock.locked(),
        "vespa_url": VESPA_URL,
        "sync_interval_seconds": SYNC_INTERVAL_SECONDS,
    }
