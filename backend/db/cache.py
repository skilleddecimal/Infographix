"""Redis caching and session management."""

import json
import os
from datetime import timedelta
from typing import Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheConfig:
    """Cache configuration."""

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = 3600,
        prefix: str = "infographix:",
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        self.prefix = prefix


class InMemoryCache:
    """Simple in-memory cache fallback when Redis is not available."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: dict[str, tuple[Any, float | None]] = {}
        self._prefix = config.prefix

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        import time
        full_key = self._full_key(key)
        if full_key not in self._cache:
            return None

        value, expires_at = self._cache[full_key]
        if expires_at and time.time() > expires_at:
            del self._cache[full_key]
            return None

        return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache."""
        import time
        full_key = self._full_key(key)
        ttl = ttl or self.config.default_ttl
        expires_at = time.time() + ttl if ttl else None
        self._cache[full_key] = (value, expires_at)
        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        full_key = self._full_key(key)
        if full_key in self._cache:
            del self._cache[full_key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        full_key = self._full_key(key)
        value = self.get(key) or 0
        new_value = int(value) + amount
        self.set(key, new_value)
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        return self.incr(key, -amount)

    def clear(self) -> bool:
        """Clear all cache entries."""
        self._cache.clear()
        return True


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, config: CacheConfig):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not installed")

        self.config = config
        self._client = redis.from_url(
            config.redis_url,
            decode_responses=True,
        )
        self._prefix = config.prefix

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        full_key = self._full_key(key)
        value = self._client.get(full_key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache."""
        full_key = self._full_key(key)
        ttl = ttl or self.config.default_ttl

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        return self._client.setex(full_key, ttl, value)

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        full_key = self._full_key(key)
        return bool(self._client.delete(full_key))

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        full_key = self._full_key(key)
        return bool(self._client.exists(full_key))

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        full_key = self._full_key(key)
        return self._client.incrby(full_key, amount)

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        full_key = self._full_key(key)
        return self._client.decrby(full_key, amount)

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        full_key = self._full_key(key)
        return bool(self._client.expire(full_key, ttl))

    def clear(self) -> bool:
        """Clear all cache entries with prefix."""
        pattern = f"{self._prefix}*"
        keys = self._client.keys(pattern)
        if keys:
            self._client.delete(*keys)
        return True

    # Session management methods
    def set_session(
        self,
        session_id: str,
        data: dict,
        ttl: int = 86400,
    ) -> bool:
        """Store session data."""
        return self.set(f"session:{session_id}", data, ttl)

    def get_session(self, session_id: str) -> dict | None:
        """Get session data."""
        return self.get(f"session:{session_id}")

    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        return self.delete(f"session:{session_id}")

    # Rate limiting methods
    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int]:
        """Check rate limit using sliding window.

        Args:
            key: Rate limit key.
            limit: Maximum requests in window.
            window: Window size in seconds.

        Returns:
            Tuple of (allowed, remaining).
        """
        full_key = f"ratelimit:{key}"

        # Use Redis pipeline for atomicity
        pipe = self._client.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window)
        results = pipe.execute()

        count = results[0]
        remaining = max(0, limit - count)

        return count <= limit, remaining


def get_cache(config: CacheConfig | None = None) -> InMemoryCache | RedisCache:
    """Get cache instance.

    Returns Redis cache if available, otherwise in-memory cache.
    """
    config = config or CacheConfig()

    if REDIS_AVAILABLE:
        try:
            cache = RedisCache(config)
            # Test connection
            cache._client.ping()
            return cache
        except Exception:
            pass

    # Fall back to in-memory cache
    return InMemoryCache(config)


# Global cache instance (lazy initialized)
_cache_instance: InMemoryCache | RedisCache | None = None


def get_default_cache() -> InMemoryCache | RedisCache:
    """Get default cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = get_cache()
    return _cache_instance
