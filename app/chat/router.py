import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator.orchestrator import ChatOrchestrator
from app.auth.dependencies import AuthContext, get_current_user
from app.chat.dto import (
    ChatMessageResponse,
    ChatMessageResponseData,
    CreateSessionRequest,
    FeedbackRequest,
    HandoffDTO,
    ResponseMeta,
    SendMessageRequest,
)
from app.chat.models import Feedback
from app.conversations.service import ConversationService
from app.core.config import get_settings
from app.database.session import get_db
from app.redis_cache.client import get_redis
from app.redis_cache.rate_limiter import RateLimiter

router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/sessions")
async def create_session(
    payload: CreateSessionRequest,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = ConversationService(db)
    session = await conversations.create_session(ctx.user_id, language=payload.language)
    await db.commit()
    return {
        "success": True,
        "data": {"session_id": str(session.id), "status": session.status, "language": session.language},
        "meta": {"request_id": request.state.request_id, "timestamp": _now_iso()},
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = ConversationService(db)
    session = await conversations.get_session(session_id, ctx.user_id)
    messages = await conversations.get_recent_messages(session_id, limit=50)
    return {
        "success": True,
        "data": {
            "session_id": str(session.id),
            "status": session.status,
            "language": session.language,
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in messages
            ],
        },
        "meta": {"request_id": request.state.request_id, "timestamp": _now_iso()},
    }


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    payload: SendMessageRequest,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ChatMessageResponse:
    settings = get_settings()
    limiter = RateLimiter(redis)
    await limiter.check(f"ratelimit:user:{ctx.user_id}", settings.rate_limit_per_user_per_min)
    client_ip = request.client.host if request.client else "unknown"
    await limiter.check(f"ratelimit:ip:{client_ip}", settings.rate_limit_per_ip_per_min)

    conversations = ConversationService(db)
    await conversations.get_session(payload.session_id, ctx.user_id)  # authorization: session must belong to user

    orchestrator = ChatOrchestrator(db, redis)
    result = await orchestrator.handle_message(
        request_id=request.state.request_id,
        session_id=payload.session_id,
        user_id=ctx.user_id,
        role=ctx.role,
        text=payload.message,
    )
    await db.commit()

    return ChatMessageResponse(
        data=ChatMessageResponseData(
            message_id=str(uuid.uuid4()),
            session_id=str(payload.session_id),
            message=result.message,
            language=result.language,
            intent=result.intent.value,
            actions=result.actions,
            handoff=HandoffDTO(**result.handoff.model_dump()),
        ),
        meta=ResponseMeta(request_id=request.state.request_id, timestamp=_now_iso()),
    )


@router.post("/sessions/{session_id}/handoff")
async def request_handoff(
    session_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.common.enums.chat import Intent, Priority
    from app.handoff.service import HandoffService

    conversations = ConversationService(db)
    session = await conversations.get_session(session_id, ctx.user_id)
    handoffs = HandoffService(db)
    handoff = await handoffs.escalate(
        session=session, user_id=ctx.user_id, priority=Priority.P2_STANDARD,
        reason="explicit_user_request", intent=Intent.HUMAN_AGENT.value,
        language=session.language, tool_calls_summary=[],
    )
    await db.commit()
    return {
        "success": True,
        "data": {"handoff_id": str(handoff.id), "priority": handoff.priority},
        "meta": {"request_id": request.state.request_id, "timestamp": _now_iso()},
    }


@router.post("/sessions/{session_id}/feedback")
async def submit_feedback(
    session_id: uuid.UUID,
    payload: FeedbackRequest,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback = Feedback(session_id=session_id, user_id=ctx.user_id, rating=payload.rating, comment=payload.comment)
    db.add(feedback)
    await db.commit()
    return {
        "success": True,
        "data": {"feedback_id": str(feedback.id)},
        "meta": {"request_id": request.state.request_id, "timestamp": _now_iso()},
    }


@router.get("/quick-actions")
async def quick_actions(ctx: AuthContext = Depends(get_current_user)):
    from app.common.enums.chat import UserRole

    if ctx.role == UserRole.DRIVER:
        return {"success": True, "data": {"actions": ["earnings", "document_status", "app_troubleshooting"]}}
    return {"success": True, "data": {"actions": ["ride_status", "fare", "cancellation", "refund", "human_agent"]}}
