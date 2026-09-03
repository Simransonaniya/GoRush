"""
Redis connection.

Why this exists:
Redis will later back: session state, rate limiting, idempotency keys,
tool-result caching, and distributed locks (spec section 26/27). For
Phase 1 we just need a shared, reusable async client -- one connection
pool for the whole app, not one connection per request.
"""

import redis.asyncio as redis

from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


def get_redis() -> redis.Redis:
    """FastAPI dependency: `r: redis.Redis = Depends(get_redis)`."""
    return redis.Redis(connection_pool=redis_pool)
