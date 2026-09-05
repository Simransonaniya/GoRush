import json

from redis.asyncio import Redis

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


class IdempotencyService:
    """Prevents duplicate execution of high-risk tools (refund, cancel, etc.)
    when a client retries a request with the same idempotency key."""

    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, tool_name: str, idempotency_key: str) -> str:
        return f"idem:{tool_name}:{idempotency_key}"

    async def get_cached_result(self, tool_name: str, idempotency_key: str) -> dict | None:
        raw = await self.redis.get(self._key(tool_name, idempotency_key))
        return json.loads(raw) if raw else None

    async def store_result(self, tool_name: str, idempotency_key: str, result: dict) -> None:
        await self.redis.set(
            self._key(tool_name, idempotency_key), json.dumps(result), ex=IDEMPOTENCY_TTL_SECONDS
        )
