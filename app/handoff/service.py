import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatSession
from app.common.enums.chat import Priority, SessionStatus
from app.conversations.service import ConversationService
from app.guardrails.pii.redactor import pii_redactor
from app.handoff.models import Handoff


class HandoffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversations = ConversationService(db)

    async def escalate(
        self,
        *,
        session: ChatSession,
        user_id: uuid.UUID,
        priority: Priority,
        reason: str,
        intent: str,
        language: str,
        tool_calls_summary: list[str],
        ride_id: str | None = None,
    ) -> Handoff:
        recent = await self.conversations.get_recent_messages(session.id, limit=10)
        issue_summary = self._build_summary(
            intent=intent, language=language, tool_calls_summary=tool_calls_summary, ride_id=ride_id
        )

        handoff = Handoff(
            session_id=session.id,
            user_id=user_id,
            priority=priority.value,
            reason=reason,
            summary=issue_summary,
            context_snapshot={
                "ride_id": ride_id,
                "intent": intent,
                "language": language,
                "recent_messages": [
                    {"role": m.role, "content": pii_redactor.redact(m.content)} for m in recent
                ],
                "tool_calls": tool_calls_summary,
            },
        )
        self.db.add(handoff)
        session.status = SessionStatus.HANDED_OFF
        session.priority = priority.value
        await self.db.flush()
        return handoff

    @staticmethod
    def _build_summary(*, intent: str, language: str, tool_calls_summary: list[str], ride_id: str | None) -> str:
        parts = [f"Customer issue classified as '{intent}'."]
        if ride_id:
            parts.append(f"Related ride: {ride_id}.")
        if tool_calls_summary:
            parts.append("Actions attempted: " + ", ".join(tool_calls_summary) + ".")
        parts.append(f"Customer is communicating in {language}.")
        return " ".join(parts)
