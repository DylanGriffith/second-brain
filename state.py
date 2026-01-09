"""State management for tracking indexed items across data sources."""

import json
import logging
from pathlib import Path
from typing import Dict, Set

logger = logging.getLogger(__name__)


def make_composite_key(source_type: str, item_id: str) -> str:
    """
    Create a composite key for tracking indexed items.

    Args:
        source_type: Type of data source (e.g., "chrome_history")
        item_id: Unique identifier within the source (e.g., URL)

    Returns:
        Composite key in format "source_type:item_id"
    """
    return f"{source_type}:{item_id}"


def parse_composite_key(composite_key: str) -> tuple[str, str]:
    """
    Parse a composite key into source type and item ID.

    Args:
        composite_key: Key in format "source_type:item_id"

    Returns:
        Tuple of (source_type, item_id)
    """
    parts = composite_key.split(":", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    # Backwards compatibility: treat plain URLs as chrome_history
    return "chrome_history", composite_key


def get_indexed_ids_for_source(
    all_indexed: Set[str],
    source_type: str
) -> Set[str]:
    """
    Get all indexed item IDs for a specific source.

    Args:
        all_indexed: Set of all composite keys
        source_type: Source type to filter by

    Returns:
        Set of item IDs (without source prefix) for the given source
    """
    ids = set()
    prefix = f"{source_type}:"
    for key in all_indexed:
        if key.startswith(prefix):
            ids.add(key[len(prefix):])
        elif ":" not in key:
            # Backwards compatibility: plain URLs are chrome_history
            if source_type == "chrome_history":
                ids.add(key)
    return ids


def load_indexed_items(path: Path) -> Set[str]:
    """
    Load set of indexed items from disk.

    Items are stored as composite keys in format "source_type:item_id"
    (e.g., "chrome_history:https://google.com")

    Args:
        path: Path to the JSON state file

    Returns:
        Set of composite key strings
    """
    if not path.exists():
        return set()

    try:
        with open(path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                items = set(data)
                # Migrate old format: plain URLs -> chrome_history:url
                migrated = set()
                needs_migration = False
                for item in items:
                    if ":" not in item:
                        # Old format: plain URL
                        migrated.add(make_composite_key("chrome_history", item))
                        needs_migration = True
                    else:
                        migrated.add(item)

                if needs_migration:
                    logger.info("Migrated old state format to composite keys")
                    save_indexed_items(migrated, path)

                return migrated
            return set()
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading state file: {e}")
        # If file is corrupted, start fresh
        return set()


def save_indexed_items(items: Set[str], path: Path) -> None:
    """
    Persist indexed items to disk.

    Args:
        items: Set of composite key strings (format: "source_type:item_id")
        path: Path to the JSON state file
    """
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(sorted(list(items)), f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save indexed items state: {e}")


# Backwards compatibility aliases
load_indexed_urls = load_indexed_items
save_indexed_urls = save_indexed_items
