import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage, ChatSession
from app.common.enums.chat import MessageRole, SessionStatus
from app.common.exceptions.base import NotFoundError


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: uuid.UUID, language: str = "en") -> ChatSession:
        session = ChatSession(user_id=user_id, language=language, status=SessionStatus.ACTIVE)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError("Chat session not found")
        return session

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
        *,
        language: str | None = None,
        intent: str | None = None,
        sentiment: str | None = None,
        risk_level: str | None = None,
        metadata: dict | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            language=language,
            intent=intent,
            sentiment=sentiment,
            risk_level=risk_level,
            metadata_json=metadata or {},
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_recent_messages(self, session_id: uuid.UUID, limit: int = 20) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
