import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.chat import MessageRole, SessionStatus
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.database.session import Base


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[SessionStatus] = mapped_column(String(32), default=SessionStatus.ACTIVE)
    language: Mapped[str] = mapped_column(String(16), default="en")
    current_ride_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(8), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", lazy="selectin")


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class ConversationSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversation_summaries"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Feedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feedback"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    rating: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
