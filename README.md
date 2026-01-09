# Second Brain - Chrome History Search

A FastAPI application that automatically indexes your Chrome browsing history into Vespa and provides a web interface for hybrid search (BM25 + semantic embeddings).

## Features

- Automatic Chrome history indexing every 5 minutes
- Hybrid search combining keyword matching (BM25) and semantic search (embeddings)
- Clean web UI for searching your browsing history
- Incremental indexing (only new URLs are processed)
- RESTful API for search queries

## Setup

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Start Vespa Container

```bash
docker run --detach --name vespa --hostname vespa-container \
  --publish 8080:8080 --publish 19071:19071 \
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

## Configuration

Configure via environment variables:

- `VESPA_URL` - Vespa API URL (default: http://localhost:8080)
- `CHROME_HISTORY_PATH` - Path to Chrome History database (default: ~/Library/Application Support/Google/Chrome/Default/History)
- `SYNC_INTERVAL_SECONDS` - Background sync interval (default: 300 = 5 minutes)
- `STATE_FILE_PATH` - Indexed URLs state file (default: ~/.second-brain-indexed-urls.json)
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
