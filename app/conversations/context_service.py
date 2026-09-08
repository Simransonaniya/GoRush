import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.provider import ChatMessage, LLMProvider
from app.chat.models import ChatMessage as ChatMessageModel
from app.chat.models import ConversationSummary
from app.conversations.service import ConversationService

SUMMARIZE_AFTER_N_MESSAGES = 20


class ContextService:
    """Builds the minimal context sent to the LLM: recent turns plus a
    compact structured summary of anything older, instead of replaying
    full history. Avoids unnecessary PII retention in long-term memory."""

    def __init__(self, db: AsyncSession, llm: LLMProvider):
        self.db = db
        self.llm = llm
        self.conversations = ConversationService(db)

    async def build_llm_messages(self, session_id: uuid.UUID) -> list[ChatMessage]:
        recent = await self.conversations.get_recent_messages(session_id, limit=SUMMARIZE_AFTER_N_MESSAGES)
        messages: list[ChatMessage] = []

        summary = await self._get_latest_summary(session_id)
        if summary:
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"[Conversation summary so far, for context only]\n{summary}",
                )
            )

        for m in recent:
            if m.role in ("user", "assistant"):
                messages.append(ChatMessage(role=m.role, content=m.content))

        return messages

    async def maybe_summarize(self, session_id: uuid.UUID) -> None:
        try:
            recent = await self.conversations.get_recent_messages(session_id, limit=SUMMARIZE_AFTER_N_MESSAGES + 1)
            if len(recent) <= SUMMARIZE_AFTER_N_MESSAGES:
                return

            transcript = "\n".join(f"{m.role}: {m.content}" for m in recent[:-5])
            schema = {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "ride_id": {"type": ["string", "null"]},
                    "previous_actions": {"type": "array", "items": {"type": "string"}},
                    "current_status": {"type": "string"},
                    "language": {"type": "string"},
                    "unresolved": {"type": "boolean"},
                },
                "required": ["issue", "current_status", "unresolved"],
            }
            summary_json = await self.llm.structured_output(
                [ChatMessage(role="user", content=f"Summarize this support conversation:\n{transcript}")],
                json_schema=schema,
            )
            self.db.add(ConversationSummary(session_id=session_id, summary_json=summary_json))
            await self.db.flush()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"Summarization skipped for session {session_id}: {exc}")

    async def _get_latest_summary(self, session_id: uuid.UUID) -> str | None:
        from sqlalchemy import select

        result = await self.db.execute(
            select(ConversationSummary)
            .where(ConversationSummary.session_id == session_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return str(row.summary_json) if row else None
