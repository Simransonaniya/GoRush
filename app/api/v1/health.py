from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.redis_client.client import get_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/deep")
async def deep_health(
    db: AsyncSession = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    """Checks real connectivity to Postgres and Redis, not just the process."""
    checks = {"postgres": "ok", "redis": "ok"}

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    try:
        await r.ping()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
