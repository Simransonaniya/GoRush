"""
Database session management.

Why this exists:
In NestJS, TypeORM gives you a DataSource + injectable Repositories.
Here, SQLAlchemy's `async_sessionmaker` plays the same role: it hands
out a fresh, isolated DB session per request. We expose `get_db()` as
a FastAPI dependency (the Python equivalent of NestJS's @InjectRepository
or constructor injection) so every route/service gets a session without
managing connections manually.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # detects dead connections before using them
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: `db: AsyncSession = Depends(get_db)`.
    Guarantees the session is closed (and rolled back on error) after
    each request -- same guarantee NestJS request-scoped providers give you.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
