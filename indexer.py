"""Generic indexing module for all data sources."""

import logging
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import quote

import httpx

from sources import get_active_sources
from sources.base import Document
from state import (
    get_indexed_ids_for_source,
    make_composite_key,
    save_indexed_items,
)

logger = logging.getLogger(__name__)


async def index_document(
    vespa_url: str,
    doc_id: str,
    doc_data: Document
) -> None:
    """
    Index a single document to Vespa.

    Args:
        vespa_url: Base URL of Vespa API
        doc_id: Document ID for Vespa (should be URL-encoded)
        doc_data: Document fields (global_id, title, domain, snippet, last_seen, url, content)

    Raises:
        httpx.HTTPError: If indexing fails
    """
    endpoint = f"{vespa_url}/document/v1/docs/items/docid/{doc_id}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"fields": doc_data},
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        response.raise_for_status()


async def sync_all_sources(
    vespa_url: str,
    indexed_items: Set[str],
    state_file: Path
) -> Dict[str, int]:
    """
    Main sync function: loads items from all active sources and indexes to Vespa.

    Args:
        vespa_url: Base URL of Vespa API
        indexed_items: Set of already indexed composite keys (will be modified in-place)
        state_file: Path to state file for persistence

    Returns:
        Stats dict with keys: new_items, errors, items_processed, sources_synced
    """
    stats = {
        "new_items": 0,
        "errors": 0,
        "items_processed": 0,
        "sources_synced": 0,
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

    # Get active sources
    sources = get_active_sources()

    if not sources:
        logger.warning("No active data sources found")
        return stats

    # Sync each source
    for source in sources:
        try:
            logger.info(f"Syncing {source.display_name}...")

            # Get already indexed IDs for this source
            indexed_ids = get_indexed_ids_for_source(
                indexed_items,
                source.source_type
            )

            # Load new items from source
            new_items = await source.load_new_items(indexed_ids)
            stats["items_processed"] += len(new_items)

            if not new_items:
                logger.info(f"No new items from {source.display_name}")
                continue

            logger.info(f"Found {len(new_items)} new items from {source.display_name}")

            # Index each item
            for item_id, doc_data in new_items:
                try:
                    # Set global_id (composite key)
                    composite_key = make_composite_key(source.source_type, item_id)
                    doc_data["global_id"] = composite_key

                    # Create Vespa document ID (URL-encoded composite key)
                    vespa_doc_id = quote(composite_key, safe='')

                    # Index to Vespa
                    await index_document(vespa_url, vespa_doc_id, doc_data)

                    # Add to indexed set
                    indexed_items.add(composite_key)

                    stats["new_items"] += 1

                    # Periodically save state to avoid losing progress
                    if stats["new_items"] % 100 == 0:
                        save_indexed_items(indexed_items, state_file)
                        logger.info(f"Progress: indexed {stats['new_items']} items")

                except Exception as e:
                    logger.error(f"Failed to index {item_id} from {source.source_type}: {e}")
                    stats["errors"] += 1

            stats["sources_synced"] += 1
            logger.info(f"Completed sync of {source.display_name}")

        except Exception as e:
            logger.error(f"Error syncing {source.display_name}: {e}", exc_info=True)
            stats["errors"] += 1

    # Final state save
    save_indexed_items(indexed_items, state_file)

    logger.info(
        f"Sync complete: {stats['new_items']} new items indexed, "
        f"{stats['errors']} errors, "
        f"{stats['sources_synced']}/{len(sources)} sources synced"
    )

    return stats
