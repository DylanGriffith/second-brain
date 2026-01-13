"""Configuration module for Second Brain application."""

import os
from pathlib import Path

# Vespa API base URL
VESPA_URL = os.getenv("VESPA_URL", "http://localhost:8080")

# Chrome history database path
CHROME_HISTORY_PATH = Path(
    os.getenv(
        "CHROME_HISTORY_PATH",
        str(Path.home() / "Library/Application Support/Google/Chrome/Default/History")
    )
)

BASH_HISTORY_PATH = Path(
    os.getenv(
        "BASH_HISTORY_PATH",
        str(Path.home() / ".bash_history")
    )
)

# Background sync interval in seconds (default: 5 minutes)
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))

# State file path for tracking indexed URLs
STATE_FILE_PATH = Path(
    os.getenv(
        "STATE_FILE_PATH",
        str(Path.cwd() / ".second-brain-indexed-urls.json")
    )
)

# Logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
