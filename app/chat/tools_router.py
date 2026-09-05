import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_current_user
from app.database.session import get_db
from app.redis_cache.client import get_redis
from app.tools.registry.registry import default_tool_registry
from app.tools.registry.tool_spec import ToolContext
from app.tools.router.tool_router import ToolRouter

router = APIRouter(prefix="/v1/chat/tools", tags=["chat-tools"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RefundRequestBody(BaseModel):
    session_id: uuid.UUID
    ride_id: str
    reason: str
    confirmed: bool = False


class RematchRequestBody(BaseModel):
    session_id: uuid.UUID
    ride_id: str


class SupportTicketBody(BaseModel):
    session_id: uuid.UUID
    category: str
    description: str


class SafetyRequestBody(BaseModel):
    session_id: uuid.UUID
    ride_id: str | None = None
    details: str


def _envelope(request: Request, data: dict) -> dict:
    return {"success": True, "data": data, "meta": {"request_id": request.state.request_id, "timestamp": _now_iso()}}


@router.post("/refund-request")
async def refund_request(
    body: RefundRequestBody,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    tool_router = ToolRouter(default_tool_registry, db, redis)
    tool_ctx = ToolContext(
        user_id=str(ctx.user_id), role=ctx.role, session_id=str(body.session_id), request_id=request.state.request_id
    )
    result = await tool_router.invoke(
        ctx=tool_ctx, tool_name="request_refund",
        arguments={"ride_id": body.ride_id, "reason": body.reason},
        user_confirmed=body.confirmed, idempotency_key=idempotency_key,
    )
    await db.commit()
    return _envelope(request, result)


@router.post("/rematch")
async def rematch(
    body: RematchRequestBody,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    tool_router = ToolRouter(default_tool_registry, db, redis)
    tool_ctx = ToolContext(
        user_id=str(ctx.user_id), role=ctx.role, session_id=str(body.session_id), request_id=request.state.request_id
    )
    result = await tool_router.invoke(
        ctx=tool_ctx, tool_name="start_rematch", arguments={"ride_id": body.ride_id},
        user_confirmed=True, idempotency_key=idempotency_key,
    )
    await db.commit()
    return _envelope(request, result)


@router.post("/support-ticket")
async def support_ticket(
    body: SupportTicketBody,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    tool_router = ToolRouter(default_tool_registry, db, redis)
    tool_ctx = ToolContext(
        user_id=str(ctx.user_id), role=ctx.role, session_id=str(body.session_id), request_id=request.state.request_id
    )
    result = await tool_router.invoke(
        ctx=tool_ctx, tool_name="create_support_ticket",
        arguments={"category": body.category, "description": body.description},
        user_confirmed=True,
    )
    await db.commit()
    return _envelope(request, result)


@router.post("/safety")
async def safety(
    body: SafetyRequestBody,
    request: Request,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Safety flow: never gated on confirmation, executes immediately."""
    tool_router = ToolRouter(default_tool_registry, db, redis)
    tool_ctx = ToolContext(
        user_id=str(ctx.user_id), role=ctx.role, session_id=str(body.session_id), request_id=request.state.request_id
    )
    result = await tool_router.invoke(
        ctx=tool_ctx, tool_name="create_safety_incident",
        arguments={"ride_id": body.ride_id, "details": body.details},
        user_confirmed=True,
    )
    await db.commit()
    return _envelope(request, result)
