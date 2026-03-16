"""Disk-based cache for market data using diskcache.

GRD-OPS-003: All cached data must include a timestamp so staleness can be shown.
GRD-OPS-002: Application must work with stale/cached data when APIs are unavailable.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import diskcache

from finapp.config import settings

logger = logging.getLogger(__name__)


class MarketDataCache:
    """Thin wrapper around diskcache.Cache with domain-specific TTL helpers."""

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        path = Path(cache_dir or settings.cache_dir) / "market_data"
        path.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(path))

    # ------------------------------------------------------------------
    # Generic get/set with TTL
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve a cached value. Returns None on miss."""
        try:
            value = self._cache.get(key)
            if value is None:
                return None
            data: dict[str, Any] = json.loads(value)
            # Enrich with cache metadata
            cached_at = datetime.fromisoformat(data.get("_cached_at", datetime.utcnow().isoformat()))
            data["is_cached"] = True
            data["cache_age_seconds"] = int((datetime.utcnow() - cached_at).total_seconds())
            return data
        except Exception as exc:
            logger.warning("Cache read error for key %s: %s", key, exc)
            return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        """Store a value with a TTL. Adds a _cached_at timestamp."""
        try:
            value["_cached_at"] = datetime.utcnow().isoformat()
            self._cache.set(key, json.dumps(value, default=str), expire=ttl_seconds)
        except Exception as exc:
            logger.warning("Cache write error for key %s: %s", key, exc)

    def delete(self, key: str) -> None:
        """Remove a single key from the cache."""
        self._cache.delete(key)

    def clear(self) -> None:
        """Flush the entire cache."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Optional[dict[str, Any]]:
        return self.get(f"quote:{ticker.upper()}")

    def set_quote(self, ticker: str, data: dict[str, Any]) -> None:
        self.set(f"quote:{ticker.upper()}", data, settings.cache_ttl_quote_seconds)

    def get_historical(self, ticker: str, period: str, interval: str) -> Optional[dict[str, Any]]:
        return self.get(f"hist:{ticker.upper()}:{period}:{interval}")

    def set_historical(self, ticker: str, period: str, interval: str, data: dict[str, Any]) -> None:
        self.set(f"hist:{ticker.upper()}:{period}:{interval}", data, settings.cache_ttl_historical_seconds)

    def get_fundamentals(self, ticker: str) -> Optional[dict[str, Any]]:
        return self.get(f"fund:{ticker.upper()}")

    def set_fundamentals(self, ticker: str, data: dict[str, Any]) -> None:
        self.set(f"fund:{ticker.upper()}", data, settings.cache_ttl_fundamentals_seconds)

    def get_news(self, key: str) -> Optional[dict[str, Any]]:
        return self.get(f"news:{key}")

    def set_news(self, key: str, data: dict[str, Any]) -> None:
        self.set(f"news:{key}", data, settings.cache_ttl_news_seconds)

    def close(self) -> None:
        """Close the underlying cache handle."""
        self._cache.close()


# Module-level singleton — shared across MCP servers
_cache_instance: Optional[MarketDataCache] = None


def get_cache() -> MarketDataCache:
    """Return the module-level cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MarketDataCache()
    return _cache_instance
