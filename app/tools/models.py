import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.chat import ToolExecutionStatus
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.database.session import Base


class ToolCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tool_calls"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    risk_level: Mapped[str] = mapped_column(String(16))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[ToolExecutionStatus] = mapped_column(String(32), default=ToolExecutionStatus.PENDING)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)


class IdempotencyKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    response_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
