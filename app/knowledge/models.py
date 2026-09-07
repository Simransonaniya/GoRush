from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.config import get_settings
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.database.session import Base

# Must match app/knowledge/embeddings/provider.py's EMBEDDING_MODEL output
# dimension (e.g. 384 for sentence-transformers/all-MiniLM-L6-v2). Changing
# EMBEDDING_MODEL to a different-dimension model requires a migration that
# alters this column and a full re-ingestion via reingest_all_active().
EMBEDDING_DIM = get_settings().embedding_dim


class KnowledgeArticle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_articles"

    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|active|archived
    approval_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    effective_from: Mapped[datetime | None] = mapped_column(nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(nullable=True)


class KnowledgeChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_articles.id"), index=True
    )
    chunk_index: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))