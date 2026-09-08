from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def get_redis():
    """Returns a real redis.asyncio.Redis client by default. Set
    USE_FAKE_REDIS=true in .env to use an in-memory fakeredis instance
    instead -- lets you run/test the app locally without a real Redis
    server (e.g. no Docker available). Not for production use."""
    settings = get_settings()

    if settings.use_fake_redis:
        from fakeredis.aioredis import FakeRedis

        return FakeRedis(decode_responses=True)

    from redis.asyncio import Redis

    return Redis.from_url(settings.redis_url, decode_responses=True)