"""State management for tracking indexed items across data sources."""

import json
import logging
from pathlib import Path
from typing import Dict, Set

logger = logging.getLogger(__name__)

def as_global_id(source_type: str, item_id: str) -> str:
    return f"{source_type}:{item_id}"

class IndexedState:
    global_ids: set[str]

    def load(path: Path) -> IndexedState:
        state = IndexedState()
        state.global_ids = set()

        if not path.exists():
            return state

        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    state.global_ids = set(data)

            return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading state file: {e}")
            return state

    def add(self, source_type: str, item_id: str):
        self.global_ids.add(as_global_id(source_type, item_id))

    def save(self, path: Path):
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
                json.dump(sorted(list(self.global_ids)), f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save indexed items state: {e}")


    def is_indexed(self, source_type: str, item_id: str) -> bool:
        return as_global_id(source_type, item_id) in self.global_ids

    def total_size(self) -> int:
        return len(self.global_ids)
