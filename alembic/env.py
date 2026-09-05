import asyncio
<<<<<<< HEAD
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
=======
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make `app.*` importable when alembic is run from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registers all models on Base.metadata)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the app's own settings instead of the static alembic.ini URL,
# so dev/staging/prod all read from the same env vars as the app.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
<<<<<<< HEAD
=======

>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
    with context.begin_transaction():
        context.run_migrations()


<<<<<<< HEAD
def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
=======
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
    with context.begin_transaction():
        context.run_migrations()


<<<<<<< HEAD
async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
=======
async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
