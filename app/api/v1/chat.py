import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import CreateSessionResponse, MessageResponse, SendMessageRequest, SessionDetailResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ChatService(db)
    session = await service.create_session(user)
    return session


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ChatService(db)
    return await service.get_session(session_id, user)


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ChatService(db)
    return await service.send_message(req.session_id, req.content, user)
