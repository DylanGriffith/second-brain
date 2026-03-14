# Second Brain - Personal Knowledge Search

A personal knowledge base that indexes your local data and provides hybrid search (BM25 + semantic embeddings).

## Architecture

```
┌─────────────────────┐     POST /api/v1/documents     ┌──────────────────────┐
│   Go Indexer (sb)   │ ──────────────────────────────> │  Python Server       │
│                     │                                  │  (FastAPI + Vespa)   │
│  Sources:           │                                  │                      │
│  - Chrome history   │                                  │  - Hybrid search     │
│  - Bash history     │                                  │  - Web UI            │
│  - Psql history     │                                  │  - REST API          │
│  - Neovim files     │                                  └──────────────────────┘
│                     │                                           │
│  Offline queue      │                                           ▼
│  ~/.second-brain/   │                                    ┌────────────┐
└─────────────────────┘                                    │   Vespa    │
                                                           └────────────┘
```

The **Python server** (`server/`) handles storage and search. The **Go indexer** (`indexer/`) collects local data and sends it to the server. A **Neovim integration** tracks opened files.

---

## Python Server Setup

### Prerequisites

- [uv](https://astral.sh/uv) for Python package management
- Docker for Vespa

### Start Vespa

```bash
docker run --rm --detach --name vespa --hostname vespa-container \
  --publish 127.0.0.1:8080:8080 --publish 127.0.0.1:19071:19071 \
  vespaengine/vespa
```

### Deploy Vespa Application

```bash
curl -L -o server/vespa/app/model/e5-small-v2-int8.onnx \
  https://github.com/vespa-engine/sample-apps/raw/master/examples/model-exporting/model/e5-small-v2-int8.onnx

vespa config set target local
vespa status deploy --wait 300
vespa deploy --wait 300 server/vespa/app
```

### Install Dependencies and Run

```bash
cd server
uv sync
uv run uvicorn second_brain.app:app --reload
```

Access the web UI at http://localhost:8000.

### Server Configuration (environment variables with `SB_` prefix)

| Variable | Default | Description |
|----------|---------|-------------|
| `SB_VESPA_URL` | `http://localhost:8080` | Vespa API URL |
| `SB_DEFAULT_NAMESPACE` | `default` | Document namespace |
| `SB_LOG_LEVEL` | `INFO` | Logging level |

### API Reference

**Index documents (used by Go indexer):**
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"global_id": "bash_history:abc123", "title": "git status", "domain": "hostname", "snippet": "git status", "last_seen": 1710000000000}]}'
```

**Search:**
```bash
curl "http://localhost:8000/api/v1/search?q=git+status&hits=10"
```

**Status:**
```bash
curl http://localhost:8000/api/v1/status
```

### Running Tests

Tests run against a real Vespa instance (uses a random namespace per session for isolation):

```bash
cd server
SB_VESPA_URL=http://vespa-01:8080 uv run pytest tests/ -v
```

---

## Go Indexer Setup

### Build

```bash
cd indexer
go build -o sb .
```

### One-shot sync

```bash
./sb sync --server-url http://localhost:8000
```

### Run as daemon (syncs every 5 minutes)

```bash
./sb run --server-url http://localhost:8000
```

### Check status

```bash
./sb status
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--server-url` | `http://localhost:8000` | Python server URL |
| `--state-dir` | `~/.second-brain/` | State and queue directory |
| `--interval` | `5m` | Sync interval for daemon mode |

### Data sources

| Source | File | Notes |
|--------|------|-------|
| Bash history | `~/.bash_history` | Resumes from last 10 known lines |
| Psql history | `~/.psql_history` | Resumes from last 10 known lines |
| Chrome history | `~/.config/google-chrome/Default/History` (Linux) or `~/Library/Application Support/Google/Chrome/Default/History` (Mac) | Cursor-based resume |
| Neovim files | `~/.second-brain/neovim-opened-files.log` | Written by Neovim integration |

### Offline queue

When the server is unavailable, documents are queued in `~/.second-brain/queue/`. On the next successful sync, queued documents are sent first.

### Running Go tests

```bash
cd indexer
go test ./internal/... -v
```

---

## Neovim Integration

Add to `~/.config/nvim/lua/initial.lua` (or equivalent):

```lua
-- Second Brain: track opened files
vim.api.nvim_create_autocmd("BufRead", {
  pattern = "*",
  callback = function()
    local filepath = vim.fn.expand("%:p")
    if filepath == "" or vim.fn.filereadable(filepath) == 0 then
      return
    end
    local dir = vim.fn.expand("~/.second-brain")
    if vim.fn.isdirectory(dir) == 0 then
      vim.fn.mkdir(dir, "p")
    end
    local logfile = dir .. "/neovim-opened-files.log"
    local timestamp = os.date("%Y-%m-%dT%H:%M:%S")
    local f = io.open(logfile, "a")
    if f then
      f:write(timestamp .. " " .. filepath .. "\n")
      f:close()
    end
  end,
})
```

After opening files in Neovim, run `./sb sync` to index them.
