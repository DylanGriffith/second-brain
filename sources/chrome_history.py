"""Chrome browsing history data source."""

import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Set, Tuple
from urllib.parse import urlparse

from sources.base import DataSource, Document

logger = logging.getLogger(__name__)


class ChromeHistorySource(DataSource):
    """
    Chrome browsing history data source.

    Indexes URLs, titles, and visit timestamps from Chrome's History database.
    """

    def __init__(self, history_path: Path):
        """
        Initialize Chrome history source.

        Args:
            history_path: Path to Chrome's History SQLite database
        """
        self.history_path = history_path

    @property
    def source_type(self) -> str:
        return "chrome_history"

    @property
    def display_name(self) -> str:
        return "Chrome Browsing History"

    def is_available(self) -> bool:
        """Check if Chrome history database exists."""
        return self.history_path.exists()

    async def load_new_items(
        self,
        state: IndexedState
    ) -> List[Tuple[str, Document]]:
        """
        Load URLs from Chrome history that haven't been indexed yet.

        Args:
            state: used to check already indexed items

        Returns:
            List of (url, document) tuples for new URLs
        """
        documents = []

        if not self.is_available():
            logger.error(f"Chrome history file not found: {self.history_path}")
            return documents

        try:
            # Copy to temp file to avoid database locking issues
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_history = Path(tmp_dir) / "History"
                shutil.copy(self.history_path, tmp_history)

                conn = sqlite3.connect(tmp_history)
                cursor = conn.cursor()

                cursor.execute("SELECT url, title, last_visit_time FROM urls")
                rows = cursor.fetchall()

                for row in rows:
                    url, title, last_visit_time = row
                    item_id = url

                    if state.is_indexed(self.source_type, item_id):
                        continue

                    # Extract domain from URL
                    try:
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = "unknown"

                    # Convert Chrome's last_visit_time to unix timestamp in milliseconds
                    # Chrome uses microseconds since 1601-01-01, convert to milliseconds since epoch
                    # Chrome epoch: January 1, 1601; Unix epoch: January 1, 1970
                    # Difference: 11644473600 seconds
                    chrome_epoch_offset = 11644473600
                    last_seen = int((last_visit_time / 1000000) - chrome_epoch_offset) * 1000

                    # TODO: Load actual page content instead of empty string
                    doc: Document = Document({
                        "global_id": "",  # Will be set by indexer
                        "url": url,
                        "title": title or url,
                        "domain": domain,
                        "snippet": f"{title or url}",
                        "content": "",  # TODO: Fetch full page content
                        "last_seen": str(last_seen),
                    })

                    documents.append((item_id, doc))

                conn.close()

        except sqlite3.Error as e:
            logger.error(f"SQLite error reading Chrome history: {e}")
        except Exception as e:
            logger.error(f"Error loading Chrome history: {e}")

        logger.info(f"Loaded {len(documents)} new URLs from Chrome history")
        return documents
