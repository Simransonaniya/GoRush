import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.chat import MessageRole, SessionStatus


class CreateSessionResponse(BaseModel):
    id: uuid.UUID
    status: SessionStatus
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    session_id: uuid.UUID
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    detected_language: str | None
    intent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    status: SessionStatus
    language: str
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


# --- Consistent API envelope (spec section 38) ---

class Meta(BaseModel):
    request_id: str
    timestamp: datetime


class ApiResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    meta: Meta
