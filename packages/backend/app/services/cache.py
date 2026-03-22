"""Redis cache layer for DNSBL scan results."""

from __future__ import annotations

import json
import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis


class RedisCache:
    """Simple cache for DNSBL results."""

    def __init__(self, ttl_hours: int | None = None):
        self.ttl_seconds = (ttl_hours or settings.scan_cache_ttl_hours) * 3600

    def get(self, key: str) -> dict | None:
        """Get cached value. Returns None on miss or error."""
        try:
            r = get_redis()
            data = r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("Redis GET failed for %s: %s", key, e)
        return None

    def set(self, key: str, value: dict, ttl_hours: int | None = None) -> None:
        """Set cached value with TTL."""
        try:
            r = get_redis()
            ttl = (ttl_hours * 3600) if ttl_hours else self.ttl_seconds
            r.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning("Redis SET failed for %s: %s", key, e)

    def delete(self, key: str) -> None:
        """Delete a cached key."""
        try:
            r = get_redis()
            r.delete(key)
        except Exception as e:
            logger.warning("Redis DELETE failed for %s: %s", key, e)

    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count deleted."""
        try:
            r = get_redis()
            keys = list(r.scan_iter(match=pattern, count=1000))
            if keys:
                return r.delete(*keys)
        except Exception as e:
            logger.warning("Redis flush failed for %s: %s", pattern, e)
        return 0
