import logging
import shutil
import sqlite3
import tempfile
import requests
import hashlib
import os

import httpx

from pathlib import Path
from typing import List, Set, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from sources.base import DataSource, Document

logger = logging.getLogger(__name__)


class BashHistorySource(DataSource):
    def __init__(self, history_path: Path):
        self.history_path = history_path

    @property
    def source_type(self) -> str:
        return "bash_history"

    @property
    def display_name(self) -> str:
        return "Bash Command History"

    def is_available(self) -> bool:
        return self.history_path.exists()

    async def load_new_items(
        self,
        state: IndexedState
    ) -> List[Tuple[str, Document]]:
        documents = []

        if not self.is_available():
            logger.error(f"Bash history file not found: {self.history_path}")
            return documents

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_history = Path(tmp_dir) / "bash_history"
            shutil.copy(self.history_path, tmp_history)

            with open(tmp_history, 'r', encoding='utf-8', errors='ignore') as f:
                last_seen = int(Path(tmp_history).stat().st_mtime * 1000)
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    item_id = hashlib.sha256(line.encode('utf-8')).hexdigest()[:16]

                    if state.is_indexed(self.source_type, item_id):
                        continue

                    hostname = os.uname().nodename

                    doc: Document = Document({
                        "global_id": "",  # Will be set by indexer
                        "title": line[:50],
                        "domain": hostname,
                        "snippet": line,
                        "last_seen": str(last_seen),
                    })

                    documents.append((item_id, doc))


        logger.info(f"Loaded {len(documents)} new URLs from Bash history")
        return documents
