"""
Reddit platform fetcher for TrendRadar.

Fetches trending posts from configured subreddits using Reddit's public JSON API.
Supports both "hot" and "top" endpoints with deduplication and rate limiting.
"""

import random
import time
from typing import Dict, List, Optional, Tuple

import requests

from . import register_platform
from .base import BasePlatformFetcher


@register_platform("reddit")
class RedditFetcher(BasePlatformFetcher):
    """
    Reddit data fetcher using public JSON API.

    Fetches both "hot" and "top" posts from configured subreddits,
    merges them with deduplication, and transforms to TrendRadar format.
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self, config: Dict, proxy_url: Optional[str] = None):
        super().__init__(config, proxy_url)
        self.subreddits = config.get("subreddits", [])
        # Validate and cap posts_limit to 1-100 range
        self.posts_limit = min(max(1, int(config.get("posts_limit", 100))), 100)
        self.top_time_filter = config.get("top_time_filter", "day")
        # Ensure request_interval is an integer (milliseconds)
        self.request_interval = int(config.get("request_interval", 2000))
        self.user_agent = config.get("user_agent", "TrendRadar/1.0")

        # OAuth configuration for future implementation
        # Note: OAuth is not yet implemented - credentials are stored for future use
        oauth_config = config.get("oauth", {})
        self.oauth_enabled = oauth_config.get("enabled", False)
        self.client_id = oauth_config.get("client_id", "")
        self.client_secret = oauth_config.get("client_secret", "")

    @property
    def platform_id(self) -> str:
        return "reddit"

    @property
    def platform_name(self) -> str:
        return self.config.get("name", "Reddit")

    def is_enabled(self) -> bool:
        return self.config.get("enabled", False) and len(self.subreddits) > 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with appropriate User-Agent."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def _fetch_subreddit_posts(
        self, subreddit: str, endpoint: str, max_retries: int = 3
    ) -> List[Dict]:
        """
        Fetch posts from a subreddit endpoint (hot or top).

        Args:
            subreddit: Subreddit name (without r/)
            endpoint: 'hot' or 'top'
            max_retries: Maximum retry attempts

        Returns:
            List of post data dicts with keys: id, title, upvotes, permalink, created_utc
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{endpoint}.json"

        params = {"limit": self.posts_limit, "raw_json": 1}
        if endpoint == "top":
            params["t"] = self.top_time_filter

        rate_limit_retries = 0
        max_rate_limit_retries = 2

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    proxies=self._get_proxies(),
                    timeout=15,
                )

                # Handle rate limiting (with separate counter to prevent infinite loop)
                if response.status_code == 429:
                    rate_limit_retries += 1
                    if rate_limit_retries > max_rate_limit_retries:
                        print(f"Reddit rate limit exceeded max retries for r/{subreddit}")
                        return []
                    retry_after = min(int(response.headers.get("Retry-After", 60)), 120)
                    print(
                        f"Reddit rate limited, waiting {retry_after}s for r/{subreddit} "
                        f"(attempt {rate_limit_retries}/{max_rate_limit_retries})"
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                data = response.json()
                posts = []

                for child in data.get("data", {}).get("children", []):
                    post_data = child.get("data", {})

                    # Skip stickied posts (usually mod announcements)
                    if post_data.get("stickied", False):
                        continue

                    title = post_data.get("title", "").strip()
                    if not title:
                        continue

                    posts.append(
                        {
                            "id": post_data.get("id", ""),
                            "title": title,
                            "upvotes": post_data.get("ups", 0),
                            "permalink": post_data.get("permalink", ""),
                            "created_utc": post_data.get("created_utc", 0),
                            "subreddit": subreddit,
                        }
                    )

                return posts

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt + random.uniform(0, 1)
                    print(
                        f"Reddit request failed for r/{subreddit}/{endpoint}: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    print(f"Reddit request failed for r/{subreddit}/{endpoint}: {e}")
                    return []

        return []

    def _merge_and_deduplicate(
        self, hot_posts: List[Dict], top_posts: List[Dict]
    ) -> List[Dict]:
        """
        Merge hot and top posts, deduplicate by post ID.

        When a post appears in both lists, keep the one with higher upvotes.

        Args:
            hot_posts: List of posts from /hot endpoint
            top_posts: List of posts from /top endpoint

        Returns:
            Combined list of unique posts
        """
        seen: Dict[str, Dict] = {}

        for post in hot_posts + top_posts:
            post_id = post["id"]
            if post_id not in seen or post["upvotes"] > seen[post_id]["upvotes"]:
                seen[post_id] = post

        return list(seen.values())

    def _transform_to_trendradar_format(self, posts: List[Dict]) -> Dict:
        """
        Transform Reddit posts to TrendRadar format.

        Posts are sorted by upvotes descending, then assigned rank positions.
        This normalizes Reddit's upvote scale to match other platforms' ranking.

        Args:
            posts: List of post dicts with title, upvotes, permalink

        Returns:
            Dict[title, {ranks: List[int], url: str, mobileUrl: str}]
        """
        # Sort by upvotes descending
        sorted_posts = sorted(posts, key=lambda p: p["upvotes"], reverse=True)

        result: Dict[str, Dict] = {}
        for rank, post in enumerate(sorted_posts, 1):
            title = post["title"]

            # Validate permalink to avoid malformed URLs
            permalink = post.get("permalink", "").strip()
            if permalink and permalink.startswith("/"):
                url = f"https://reddit.com{permalink}"
            else:
                # Fallback to subreddit URL if permalink is missing or invalid
                subreddit = post.get("subreddit", "all")
                url = f"https://reddit.com/r/{subreddit}"

            if title in result:
                # Same title from different subreddits, append rank
                result[title]["ranks"].append(rank)
            else:
                result[title] = {
                    "ranks": [rank],
                    "url": url,
                    "mobileUrl": url,
                }

        return result

    def _fetch_subreddit(self, subreddit: str) -> List[Dict]:
        """
        Fetch and merge hot + top posts for a single subreddit.

        Args:
            subreddit: Subreddit name

        Returns:
            Merged and deduplicated list of posts
        """
        print(f"Fetching Reddit r/{subreddit}...")

        hot_posts = self._fetch_subreddit_posts(subreddit, "hot")

        # Add delay between requests
        time.sleep(self.request_interval / 1000)

        top_posts = self._fetch_subreddit_posts(subreddit, "top")

        merged = self._merge_and_deduplicate(hot_posts, top_posts)
        print(
            f"  r/{subreddit}: {len(hot_posts)} hot + {len(top_posts)} top = {len(merged)} unique"
        )

        return merged

    def fetch_all(self) -> Tuple[Dict, Dict, List]:
        """
        Fetch all configured subreddits.

        Returns:
            Tuple of (results, id_to_name, failed_ids) matching TrendRadar format
        """
        if not self.is_enabled():
            return {}, {}, []

        all_posts: List[Dict] = []
        failed_subreddits: List[str] = []

        for i, subreddit in enumerate(self.subreddits):
            try:
                posts = self._fetch_subreddit(subreddit)
                all_posts.extend(posts)
            except Exception as e:
                print(f"Failed to fetch r/{subreddit}: {e}")
                failed_subreddits.append(subreddit)

            # Add delay between subreddits (except after last one)
            if i < len(self.subreddits) - 1:
                time.sleep(self.request_interval / 1000)

        if not all_posts:
            return {}, {}, [self.platform_id]

        # Transform all posts to TrendRadar format
        results = {self.platform_id: self._transform_to_trendradar_format(all_posts)}
        id_to_name = {self.platform_id: self.platform_name}
        failed_ids = [self.platform_id] if failed_subreddits else []

        post_count = len(results.get(self.platform_id, {}))
        print(f"Reddit fetch complete: {post_count} unique posts from {len(self.subreddits)} subreddits")

        return results, id_to_name, failed_ids
