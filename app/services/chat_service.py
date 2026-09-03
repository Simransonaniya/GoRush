"""
Chat service.

Spec ref: section 6 (message pipeline). Phase 1 only implements the
skeleton of that 24-step pipeline: persist the user's message, call the
LLM gateway, persist the assistant's reply. Steps like language
detection, intent detection, tool calling, guardrails, and RAG are
added in Phases 2-3 -- but notice the ChatMessage model already has
`detected_language` / `intent` / `risk_level` columns waiting for them.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.base import LLMMessage
from app.ai.llm.gateway import get_llm_provider
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.user import User

SYSTEM_PROMPT = (
    "You are GoRush Assistant, a helpful support agent for the GoRush ride "
    "platform. Never invent ride, payment, or safety information."
)


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user: User) -> ChatSession:
        session = ChatSession(user_id=user.id, language=user.preferred_language)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID, user: User) -> ChatSession:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
        if session.user_id != user.id:
            # ownership check -- never trust client-supplied IDs (spec section 8)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your session")
        await self.db.refresh(session, attribute_names=["messages"])
        return session

    async def send_message(self, session_id: uuid.UUID, content: str, user: User) -> ChatMessage:
        session = await self.get_session(session_id, user)

        user_message = ChatMessage(session_id=session.id, role=MessageRole.USER, content=content)
        self.db.add(user_message)
        await self.db.flush()  # get an id without committing yet

        # Phase 1: minimal context window (system prompt + latest user message).
        # Real contextual retrieval / summarization arrives in Phase 2.
        llm = get_llm_provider()
        llm_response = await llm.chat(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=content),
            ]
        )

        assistant_message = ChatMessage(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)
        return assistant_message
