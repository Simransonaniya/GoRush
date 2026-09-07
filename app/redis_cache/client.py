from functools import lru_cache
import fakeredis.aioredis
from redis.asyncio import Redis
import socket

from app.core.config import get_settings

_fake_redis = None

@lru_cache
def get_redis() -> Redis:
    global _fake_redis
    settings = get_settings()
    # Check if host/port is reachable
    try:
        url = settings.redis_url
        if "://" in url:
            host_port = url.split("://")[1].split("/")[0]
            if "@" in host_port:
                host_port = host_port.split("@")[1]
            if ":" in host_port:
                host, port = host_port.split(":")
                port = int(port)
            else:
                host, port = host_port, 6379
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        pass

    if _fake_redis is None:
        _fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return _fake_redis

