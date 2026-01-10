# Second Brain - Personal Knowledge Search

A FastAPI application that automatically indexes your personal data into Vespa and provides a web interface for hybrid search (BM25 + semantic embeddings).

## Features

- Extensible data source architecture for indexing different types of personal data
- Currently indexes: Chrome browsing history
- Easy to add new sources: bash history, psql history, neovim files, etc.
- Automatic indexing every 5 minutes
- Hybrid search combining keyword matching (BM25) and semantic search (embeddings)
- Clean web UI for searching your personal knowledge
- Incremental indexing (only new items are processed)
- RESTful API for search queries

## Setup

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Start Vespa Container

```bash
docker run --rm --detach --name vespa --hostname vespa-container \
  --publish 127.0.0.1:8080:8080 --publish 127.0.0.1:19071:19071 \
  vespaengine/vespa
```

### Deploy Vespa Application

```bash
curl -L -o vespa/app/model/e5-small-v2-int8.onnx https://github.com/vespa-engine/sample-apps/raw/master/examples/model-exporting/model/e5-small-v2-int8.onnx
vespa config set target local
vespa status deploy --wait 300
vespa deploy --wait 300 vespa/app
```

### Start the FastAPI Application

```bash
uvicorn app:app --reload
```

The application will:
- Perform an initial sync of your Chrome history on startup
- Continue syncing every 5 minutes in the background
- Serve the web UI at http://localhost:8000

## Usage

### Web Interface

Open http://localhost:8000 in your browser to search your browsing history.

### API Endpoints

**Search:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query", "hits": 10}'
```

**Status:**
```bash
curl http://localhost:8000/status
```

## Adding New Data Sources

To index additional types of personal data (bash history, psql history, neovim files, etc.):

1. Create a new file in `sources/` (e.g., `bash_history.py`)
2. Implement a class inheriting from `DataSource` (see `sources/base.py`)
3. Implement required methods:
   - `source_type` - Unique identifier (e.g., "bash_history")
   - `display_name` - Human-readable name
   - `load_new_items(indexed_ids)` - Load new items from source
   - `is_available()` - Check if source exists on system
4. Register the source in `sources/__init__.py` in `get_active_sources()`
5. Map your data to the document format with required fields:
   - `global_id` - Set to "" (will be auto-populated)
   - `title` - Display title
   - `domain` - Category/source indicator
   - `snippet` - Short searchable snippet
   - `last_seen` - Unix timestamp in milliseconds
   - `url` - Optional, for web URLs
   - `content` - Optional, for full text

See `sources/chrome_history.py` for a complete example.

## Configuration

Configure via environment variables:

- `VESPA_URL` - Vespa API URL (default: http://localhost:8080)
- `CHROME_HISTORY_PATH` - Path to Chrome History database (default: ~/Library/Application Support/Google/Chrome/Default/History)
- `SYNC_INTERVAL_SECONDS` - Background sync interval (default: 300 = 5 minutes)
- `STATE_FILE_PATH` - Indexed items state file (default: .second-brain-indexed-urls.json)
- `LOG_LEVEL` - Logging level (default: INFO)

## Direct Vespa API Examples

Text search only:

```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"yql": "select * from sources * where userQuery()", "hits": 3, "query": "Vespa"}' \
  http://localhost:8080/search/
```

Hybrid search:

```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"yql": "select * from sources * where rank({targetHits:100}nearestNeighbor(embedding,q), userQuery())", "hits": 3, "query": "embedding", "type": "weakAnd", "ranking": "hybrid", "input.query(q)": "embed(e5, \"embedding\")"}' \
  http://localhost:8080/search/
```

## TODO

1. [ ] Optimize performance of get_indexed_ids_for_source . We should not loop the entire list every time.
1. [ ] Add last visited time to search results
1. [ ] Use SQLite DB for state
1. [x] Use templating library
1. [ ] Add bash history index
1. [ ] Sync bookmarks from instapaper
