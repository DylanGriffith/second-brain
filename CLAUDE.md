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
docker run --rm --detach --name vespa --hostname vespa-container \
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

The application is a FastAPI web server with automated data source indexing:

**Core Modules:**
- **app.py**: Main FastAPI application with lifespan management, endpoints, and background sync orchestration
- **config.py**: Configuration using environment variables (VESPA_URL, CHROME_HISTORY_PATH, SYNC_INTERVAL_SECONDS, STATE_FILE_PATH, LOG_LEVEL)
- **indexer.py**: Generic indexing logic that works with all data sources (async with httpx)
- **searcher.py**: Hybrid search implementation (BM25 + embeddings)
- **state.py**: Indexed items state persistence using composite keys (JSON file at .second-brain-indexed-urls.json)

**Data Sources Architecture:**
- **sources/base.py**: Abstract `DataSource` class defining the interface for all data sources
- **sources/chrome_history.py**: Chrome browsing history implementation
- **sources/__init__.py**: Data source registry where new sources are registered

To add a new data source (e.g., bash history, psql history, neovim files):
1. Create a new file in `sources/` (e.g., `bash_history.py`)
2. Implement a class inheriting from `DataSource` with methods:
   - `source_type` property (unique identifier like "bash_history")
   - `display_name` property (human-readable name)
   - `load_new_items(indexed_ids)` method (returns list of (item_id, document) tuples)
   - `is_available()` method (check if source exists on system)
3. Register it in `sources/__init__.py` in the `get_active_sources()` function

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

- **schemas/items.sd**: Generic document schema for all item types with fields:
  - `global_id` (required): Unique identifier (composite key: source_type:item_id)
  - `title` (required): Display title for search results
  - `domain` (required): Category/source indicator
  - `snippet` (required): Short searchable snippet/description
  - `last_seen` (required): Unix timestamp (milliseconds) when item was last seen
  - `url` (optional): Web URL for clickable items
  - `content` (optional): Full text content (for websites: full page content)
  - `embedding`: 384-dimensional tensor for semantic search
- **services.xml**: Defines the Vespa container with search API, document API, and the e5-small-v2-int8 embedder component
- **search/query-profiles/default.xml**: Default query profile configuration
- **model/**: Contains the embedding model files (tokenizer.json and e5-small-v2-int8.onnx)

### Search Ranking Profiles

The items schema defines multiple ranking profiles in `vespa/app/schemas/items.sd`:

- **bm25**: Text-based ranking using BM25 across title, snippet, and content fields
- **closeness**: Vector-based semantic search using HNSW index on embeddings
- **hybrid**: Combines BM25 text search with vector similarity, weighted by query parameters `wText` and `wVector`

### Indexing Flow

The FastAPI application automatically indexes data from all active sources:

1. Background task runs every 5 minutes (and once on startup)
2. `indexer.sync_all_sources()` iterates through all active data sources from the registry
3. For each source:
   - Get already indexed item IDs using composite keys (format: `{source_type}:{item_id}`)
   - Call source's `load_new_items(indexed_ids)` method
   - For Chrome history: copies SQLite database to temp, queries new URLs
   - For future sources: each implements its own loading logic
4. Only items not in the indexed set are processed (incremental indexing)
5. Each document gets its `global_id` field set to the composite key
6. Documents are POSTed to Vespa at `/document/v1/docs/items/docid/{url_encoded_composite_key}`
7. The e5 embedder automatically generates embeddings from the title + snippet fields
8. Documents are indexed with both text (BM25 on title/snippet/content) and vector (HNSW) indices
9. Composite keys are added to state (e.g., `"chrome_history:https://google.com"`)
10. State is saved to .second-brain-indexed-urls.json after each sync

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
- Schema changed from `websites` to generic `items` schema
- Document IDs are URL-encoded composite keys (format: `source_type:item_id`)
- The embedding field uses a 384-dimensional tensor with angular distance metric
- Embeddings generated from: `title + " " + snippet`
- HNSW index configuration: max-links-per-node=32, neighbors-to-explore-at-insert=200
- Browser history is read from Chrome's SQLite database at `~/Library/Application Support/Google/Chrome/Default/History`
- Chrome timestamps are converted from microseconds since 1601 to unix milliseconds
- All data sources must provide: global_id, title, domain, snippet, last_seen
- Optional fields: url (for websites), content (for full text)
