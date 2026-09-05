from redis.asyncio import Redis

from app.common.exceptions.base import RateLimitExceededError


class RateLimiter:
    """Fixed-window rate limiter backed by Redis INCR + TTL.
    Used per-user, per-IP, per-session and per-tool."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window_seconds)
        if current > limit:
            raise RateLimitExceededError(f"Rate limit exceeded for {key}")
