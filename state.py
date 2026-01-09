"""State management for tracking indexed URLs."""

import json
from pathlib import Path
from typing import Set


def load_indexed_urls(path: Path) -> Set[str]:
    """
    Load set of indexed URLs from disk.

    Args:
        path: Path to the JSON state file

    Returns:
        Set of indexed URL strings
    """
    if not path.exists():
        return set()

    try:
        with open(path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            return set()
    except (json.JSONDecodeError, IOError):
        # If file is corrupted, start fresh
        return set()


def save_indexed_urls(urls: Set[str], path: Path) -> None:
    """
    Persist indexed URLs to disk.

    Args:
        urls: Set of indexed URL strings
        path: Path to the JSON state file
    """
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(sorted(list(urls)), f, indent=2)
    except IOError as e:
        # Log error but don't crash the application
        print(f"Warning: Failed to save indexed URLs state: {e}")
