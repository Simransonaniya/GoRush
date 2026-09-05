import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.database.session import Base


class Handoff(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "handoffs"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    priority: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(default=False)


class SupportTicket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "support_tickets"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="open")
    description: Mapped[str] = mapped_column(Text)
