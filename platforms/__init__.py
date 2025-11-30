"""
External platform fetchers registry.

This module provides a registry pattern for external platform fetchers,
allowing new platforms to be added without modifying the main codebase.
"""

from typing import Dict, List, Optional, Type

from .base import BasePlatformFetcher

# Registry of available external platform fetchers
PLATFORM_REGISTRY: Dict[str, Type[BasePlatformFetcher]] = {}


def register_platform(platform_id: str):
    """
    Decorator to register a platform fetcher class.

    Usage:
        @register_platform("reddit")
        class RedditFetcher(BasePlatformFetcher):
            ...
    """

    def decorator(cls: Type[BasePlatformFetcher]):
        PLATFORM_REGISTRY[platform_id] = cls
        return cls

    return decorator


def get_platform_fetcher(
    platform_id: str, config: Dict, proxy_url: Optional[str] = None
) -> Optional[BasePlatformFetcher]:
    """Get an instance of a platform fetcher by ID."""
    if platform_id in PLATFORM_REGISTRY:
        platform_config = config.get(platform_id, {})
        return PLATFORM_REGISTRY[platform_id](platform_config, proxy_url)
    return None


def get_all_enabled_fetchers(
    config: Dict, proxy_url: Optional[str] = None
) -> List[BasePlatformFetcher]:
    """
    Get instances of all enabled external platform fetchers.

    Args:
        config: The external_platforms config dict from config.yaml
        proxy_url: Optional proxy URL for requests

    Returns:
        List of enabled BasePlatformFetcher instances
    """
    fetchers = []
    for platform_id, fetcher_class in PLATFORM_REGISTRY.items():
        platform_config = config.get(platform_id, {})
        if platform_config.get("enabled", False):
            try:
                fetcher = fetcher_class(platform_config, proxy_url)
                fetchers.append(fetcher)
            except Exception as e:
                print(f"Failed to initialize {platform_id} fetcher: {e}")
    return fetchers


# Import platform modules to trigger registration
# Each platform module should use @register_platform decorator
from . import reddit  # noqa: E402, F401
