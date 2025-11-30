"""
Abstract base class for external platform fetchers.

All external platform fetchers should inherit from BasePlatformFetcher
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class BasePlatformFetcher(ABC):
    """
    Abstract base class for external platform data fetchers.

    Subclasses must implement the abstract methods to provide
    platform-specific data fetching logic.
    """

    def __init__(self, config: Dict, proxy_url: Optional[str] = None):
        """
        Initialize the fetcher with configuration.

        Args:
            config: Platform-specific configuration dict
            proxy_url: Optional proxy URL for requests
        """
        self.config = config
        self.proxy_url = proxy_url

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """
        Unique platform identifier.

        Returns:
            String identifier (e.g., "reddit", "hackernews")
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Human-readable platform name for display.

        Returns:
            Display name (e.g., "Reddit", "Hacker News")
        """
        pass

    @abstractmethod
    def fetch_all(self) -> Tuple[Dict, Dict, List]:
        """
        Fetch all data from the platform.

        Returns:
            Tuple containing:
            - results: Dict[platform_id, Dict[title, {ranks: List[int], url: str, mobileUrl: str}]]
            - id_to_name: Dict[platform_id, platform_name]
            - failed_ids: List[platform_id] for any failures
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if this platform is enabled in configuration.

        Returns:
            True if the platform should be fetched, False otherwise
        """
        pass

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration for requests."""
        if self.proxy_url:
            return {"http": self.proxy_url, "https": self.proxy_url}
        return None
