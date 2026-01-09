# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a second-brain application that indexes and searches web content using Vespa search engine. The system supports both text-based search (BM25) and hybrid search (text + semantic embeddings).

## Development Setup

### Initial Setup

```bash
# Install Python dependencies
pip install requests

# Start Vespa container
docker run --detach --name vespa --hostname vespa-container \
  --publish 8080:8080 --publish 19071:19071 \
  vespaengine/vespa

# Configure Vespa CLI
vespa config set target local

# Wait for Vespa to be ready
vespa status deploy --wait 300

# Deploy the application
vespa deploy --wait 300 vespa/app
```

### Running the Application

Install dependencies and start the FastAPI server:
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Access the web UI at: http://localhost:8000

Check sync status: http://localhost:8000/status

### Legacy Scripts (Reference Only)

The original scripts are kept in `scripts/` for reference:
- `scripts/load-browsing-history.py` - Manual history indexing
- `scripts/load-and-search.py` - Example search queries

## Architecture

### FastAPI Application

The application is a FastAPI web server with automated Chrome history indexing:

**Core Modules:**
- **app.py**: Main FastAPI application with lifespan management, endpoints, and background sync orchestration
- **config.py**: Configuration using environment variables (VESPA_URL, CHROME_HISTORY_PATH, SYNC_INTERVAL_SECONDS, STATE_FILE_PATH, LOG_LEVEL)
- **indexer.py**: Chrome history loading and Vespa indexing logic (async with httpx)
- **searcher.py**: Hybrid search implementation (BM25 + embeddings)
- **state.py**: Indexed URLs state persistence (JSON file at ~/.second-brain-indexed-urls.json)

**Endpoints:**
- `GET /` - Web UI with search interface (inline HTML/CSS/JS)
- `POST /search` - Execute hybrid search query (request: {query, hits}, response: {results, query, count})
- `GET /status` - Sync status (indexed_urls_count, last_sync_time, sync_error_count, sync_in_progress)

**Background Sync:**
- Runs initial sync on startup
- Periodic sync every 5 minutes (configurable via SYNC_INTERVAL_SECONDS)
- Uses asyncio.Lock to prevent overlapping runs
- Tracks indexed URLs to avoid re-indexing (incremental sync)
- Saves state to JSON file after each successful sync

### Vespa Configuration

The Vespa backend is defined in `vespa/app/` with the following structure:

- **schemas/websites.sd**: Document schema definition with fields (url, title, domain, content) and embedding field for semantic search
- **services.xml**: Defines the Vespa container with search API, document API, and the e5-small-v2-int8 embedder component
- **search/query-profiles/default.xml**: Default query profile configuration
- **model/**: Contains the embedding model files (tokenizer.json and e5-small-v2-int8.onnx)

### Search Ranking Profiles

The websites schema defines multiple ranking profiles in `vespa/app/schemas/websites.sd`:

- **bm25**: Text-based ranking using BM25 on title field
- **closeness**: Vector-based semantic search using HNSW index on embeddings
- **hybrid**: Combines BM25 text search with vector similarity, weighted by query parameters `wTitle` and `wVector`

### Indexing Flow

The FastAPI application automatically indexes Chrome history:

1. Background task runs every 5 minutes (and once on startup)
2. Chrome History SQLite database is copied to temp location (to avoid locking)
3. New URLs are extracted using query: `SELECT url, title, last_visit_time FROM urls`
4. Only URLs not in the indexed_urls set are processed (incremental)
5. Documents are POSTed to Vespa at `/document/v1/docs/websites/docid/{doc_id}`
6. URLs are encoded as document IDs using URL encoding (`quote(url, safe='')`)
7. The e5 embedder automatically generates embeddings from the title field
8. Documents are indexed with both text (BM25) and vector (HNSW) indices
9. State is saved to ~/.second-brain-indexed-urls.json after each sync

### Search API

**Web UI (Recommended):**

Visit http://localhost:8000 for the search interface. The UI uses hybrid search by default.

**FastAPI Endpoint:**

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Vespa", "hits": 10}'
```

**Direct Vespa API (Lower-level):**

Text search:
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"yql": "select * from sources * where userQuery()", "hits": 3, "query": "Vespa"}' \
  http://localhost:8080/search/
```

Hybrid search (text + embeddings):
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"yql": "select * from sources * where rank({targetHits:100}nearestNeighbor(embedding,q), userQuery())", "hits": 3, "query": "embedding", "type": "weakAnd", "ranking": "hybrid", "input.query(q)": "embed(e5, \"embedding\")"}' \
  http://localhost:8080/search/
```

## Key Implementation Details

- Vespa deployment changes require: `vespa deploy --wait 300 vespa/app`
- Document IDs are URL-encoded versions of the actual URLs
- The embedding field uses a 384-dimensional tensor with angular distance metric
- HNSW index configuration: max-links-per-node=32, neighbors-to-explore-at-insert=200
- Browser history is read from Chrome's SQLite database at `~/Library/Application Support/Google/Chrome/Default/History`
