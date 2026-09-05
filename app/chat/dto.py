import uuid

from pydantic import BaseModel, Field

from app.common.enums.chat import Language, Priority


class CreateSessionRequest(BaseModel):
    language: str = "en"


class SendMessageRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=4000)
    idempotency_key: str | None = None


class ChatActionDTO(BaseModel):
    tool: str


class HandoffDTO(BaseModel):
    triggered: bool
    priority: Priority | None = None
    handoff_id: str | None = None


class ChatMessageResponseData(BaseModel):
    message_id: str
    session_id: str
    message: str
    language: Language
    intent: str
    actions: list[str]
    handoff: HandoffDTO | None = None


class ResponseMeta(BaseModel):
    request_id: str
    timestamp: str


class ChatMessageResponse(BaseModel):
    success: bool = True
    data: ChatMessageResponseData
    meta: ResponseMeta


class FeedbackRequest(BaseModel):
    session_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
