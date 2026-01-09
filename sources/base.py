"""Base class for data sources."""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple


class Document(Dict[str, str]):
    """
    Document to be indexed in Vespa.

    Required fields:
    - global_id: Unique global identifier (composite key: source_type:item_id)
    - title: Display title for search results
    - domain: Category/source indicator (e.g., website domain, "bash", "psql")
    - snippet: Short searchable snippet/description
    - last_seen: Timestamp (unix epoch in milliseconds) when item was last seen

    Optional fields:
    - url: Web URL (for websites, can be omitted for non-web items)
    - content: Full text content (for websites: full page content, can be empty initially)
    """
    pass


class DataSource(ABC):
    """
    Abstract base class for data sources that can be indexed.

    To add a new data source:
    1. Create a new class inheriting from DataSource
    2. Implement all abstract methods
    3. Register it in sources/__init__.py
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        Unique identifier for this source type.
        Used as prefix in composite keys: "{source_type}:{item_id}"

        Examples: "chrome_history", "bash_history", "neovim_files"
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this source."""
        pass

    @abstractmethod
    async def load_new_items(
        self,
        indexed_ids: Set[str]
    ) -> List[Tuple[str, Document]]:
        """
        Load items from this source that haven't been indexed yet.

        Args:
            indexed_ids: Set of item IDs already indexed (without source prefix)

        Returns:
            List of (item_id, document) tuples where:
            - item_id: Unique identifier within this source (e.g., URL, command, file path)
            - document: Dict with required keys:
              - global_id: Will be set to "{source_type}:{item_id}"
              - title: Display title
              - domain: Category/source indicator
              - snippet: Short searchable content
              - last_seen: Unix timestamp in milliseconds
            - document: Optional keys:
              - url: Web URL (for websites)
              - content: Full text content

        The indexer will automatically:
        - Set global_id to composite key: "{source_type}:{item_id}"
        - Check if already indexed
        - Index to Vespa
        - Track in state
        """
        pass

    def is_available(self) -> bool:
        """
        Check if this source is available on the current system.

        Returns:
            True if source can be accessed, False otherwise

        Override this to check for required files/binaries.
        Default implementation returns True.
        """
        return True
