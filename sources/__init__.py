"""
Data source registry.

To add a new data source:
1. Create a new file in sources/ (e.g., bash_history.py)
2. Implement a class inheriting from DataSource
3. Import and register it in get_active_sources() below
"""

import logging
from typing import List

from config import CHROME_HISTORY_PATH, BASH_HISTORY_PATH
from sources.base import DataSource
from sources.chrome_history import ChromeHistorySource
from sources.bash_history import BashHistorySource

logger = logging.getLogger(__name__)


def get_active_sources() -> List[DataSource]:
    sources = [
        ChromeHistorySource(CHROME_HISTORY_PATH),
         BashHistorySource(BASH_HISTORY_PATH),
        # PSQLHistorySource(PSQL_HISTORY_PATH),
        # NeovimFilesSource(NEOVIM_FILES_PATH),
    ]

    # Filter to only available sources
    active = [s for s in sources if s.is_available()]

    logger.info(f"Active data sources: {[s.display_name for s in active]}")

    return active


# Export base class and registry function
__all__ = ["DataSource", "get_active_sources"]
