import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


class AuditService:
    """Single write-path for all audit trail entries. Never skip this for
    tool calls, high-risk actions, safety actions, or admin changes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        request_id: str,
        action: str,
        decision: str,
        user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        tool_name: str | None = None,
        model_version: str | None = None,
        prompt_version: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            action=action,
            tool_name=tool_name,
            decision=decision,
            model_version=model_version,
            prompt_version=prompt_version,
            details=details or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
