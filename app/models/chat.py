"""
Chat session & message models.

Spec ref: section 6 (message pipeline), section 34 (DB design).

A ChatSession is one ongoing conversation (like a Slack thread).
Each ChatMessage belongs to a session and records who sent it (user or
assistant), the detected language/intent, and -- importantly -- fields
we'll need in later phases (tool calls, risk level) without having to
migrate the schema again.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), default=SessionStatus.ACTIVE)
    language: Mapped[str] = mapped_column(String(10), default="en")
    # free-form context blob: current ride id, unresolved issue, etc.
    context: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    content: Mapped[str] = mapped_column(Text)

    # populated in later phases by the intent/language engines
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
