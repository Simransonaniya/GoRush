import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.database.session import Base

# Import all models so they register on Base.metadata
from app.users.models import User  # noqa: F401
from app.chat.models import ChatSession, ChatMessage, ConversationSummary, Feedback  # noqa: F401
from app.tools.models import ToolCall, IdempotencyKey  # noqa: F401
from app.knowledge.models import KnowledgeArticle, KnowledgeChunk  # noqa: F401
from app.handoff.models import Handoff, SupportTicket  # noqa: F401
from app.audit.models import AuditLog  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
