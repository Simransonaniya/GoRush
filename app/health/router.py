from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.redis_cache.client import get_redis

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness():
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {"database": "unknown", "redis": "unknown"}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}
