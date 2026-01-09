"""Chrome history indexing module."""

import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger(__name__)


def load_new_urls_from_chrome(
    chrome_history_path: Path,
    indexed_urls: Set[str]
) -> List[Tuple[str, Dict[str, str]]]:
    """
    Load URLs from Chrome history that haven't been indexed yet.

    Args:
        chrome_history_path: Path to Chrome's History database
        indexed_urls: Set of already indexed URLs

    Returns:
        List of (url, document_data) tuples for new URLs
    """
    documents = []

    if not chrome_history_path.exists():
        logger.error(f"Chrome history file not found: {chrome_history_path}")
        return documents

    try:
        # Copy to temp file to avoid database locking issues
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_history = Path(tmp_dir) / "History"
            shutil.copy(chrome_history_path, tmp_history)

            conn = sqlite3.connect(tmp_history)
            cursor = conn.cursor()

            cursor.execute("SELECT url, title, last_visit_time FROM urls")
            rows = cursor.fetchall()

            for row in rows:
                url, title, last_visit_time = row

                # Skip if already indexed
                if url in indexed_urls:
                    continue

                # Extract domain from URL
                try:
                    domain = urlparse(url).netloc
                except Exception:
                    domain = ""

                # TODO: Load actual page content instead of placeholder
                content = f"Visited on {last_visit_time}"

                doc_data = {
                    "url": url,
                    "title": title or "",
                    "domain": domain,
                    "content": content,
                }

                documents.append((url, doc_data))

            conn.close()

    except sqlite3.Error as e:
        logger.error(f"SQLite error reading Chrome history: {e}")
    except Exception as e:
        logger.error(f"Error loading Chrome history: {e}")

    return documents


async def index_document(vespa_url: str, url: str, doc_data: Dict[str, str]) -> None:
    """
    Index a single document to Vespa.

    Args:
        vespa_url: Base URL of Vespa API
        url: Document URL (used as document ID)
        doc_data: Document fields (url, title, domain, content)

    Raises:
        httpx.HTTPError: If indexing fails
    """
    # URL-encode the URL to use as document ID
    doc_id = quote(url, safe='')

    endpoint = f"{vespa_url}/document/v1/docs/websites/docid/{doc_id}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"fields": doc_data},
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        response.raise_for_status()


async def sync_chrome_history(
    chrome_history_path: Path,
    vespa_url: str,
    indexed_urls: Set[str],
    state_file: Path
) -> Dict[str, int]:
    """
    Main sync function: loads Chrome history and indexes new URLs to Vespa.

    Args:
        chrome_history_path: Path to Chrome's History database
        vespa_url: Base URL of Vespa API
        indexed_urls: Set of already indexed URLs (will be modified in-place)
        state_file: Path to state file for persistence

    Returns:
        Stats dict with keys: new_urls, errors, urls_processed
    """
    stats = {
        "new_urls": 0,
        "errors": 0,
        "urls_processed": 0,
    }

    # Check Vespa health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{vespa_url}/state/v1/health",
                timeout=5.0
            )
            if response.status_code != 200:
                logger.error("Vespa health check failed")
                return stats
    except Exception as e:
        logger.error(f"Cannot connect to Vespa: {e}")
        return stats

    # Load new URLs from Chrome
    logger.info("Loading new URLs from Chrome history...")
    new_urls = load_new_urls_from_chrome(chrome_history_path, indexed_urls)
    stats["urls_processed"] = len(new_urls)

    if not new_urls:
        logger.info("No new URLs to index")
        return stats

    logger.info(f"Found {len(new_urls)} new URLs to index")

    # Index each document
    from state import save_indexed_urls

    for url, doc_data in new_urls:
        try:
            await index_document(vespa_url, url, doc_data)
            indexed_urls.add(url)
            stats["new_urls"] += 1

            # Periodically save state to avoid losing progress
            if stats["new_urls"] % 100 == 0:
                save_indexed_urls(indexed_urls, state_file)
                logger.info(f"Progress: indexed {stats['new_urls']} URLs")

        except Exception as e:
            logger.error(f"Failed to index {url}: {e}")
            stats["errors"] += 1

    # Final state save
    save_indexed_urls(indexed_urls, state_file)

    logger.info(
        f"Sync complete: {stats['new_urls']} indexed, "
        f"{stats['errors']} errors, "
        f"{stats['urls_processed']} processed"
    )

    return stats
