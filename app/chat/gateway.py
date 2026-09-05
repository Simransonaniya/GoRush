import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth.security import decode_access_token
from app.common.exceptions.base import UnauthorizedError
from app.database.session import AsyncSessionLocal
from app.redis_cache.client import get_redis
from app.users.models import User

router = APIRouter()


async def _authenticate_ws(token: str) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedError("User not found")
        return user


# Streams: chat.message.started, chat.message.token, chat.tool.started,
# chat.tool.completed, chat.message.completed, chat.handoff, chat.error.
# Internal tool implementation details are never exposed -- only tool
# *name* and a sanitized status.
@router.websocket("/v1/chat/ws")
async def chat_websocket(websocket: WebSocket, token: str):
    try:
        user = await _authenticate_ws(token)
    except UnauthorizedError:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            session_id = payload.get("session_id")
            text = payload.get("message", "")

            await websocket.send_json({"event": "chat.message.started", "session_id": session_id})

            async with AsyncSessionLocal() as db:
                from app.ai.orchestrator.orchestrator import ChatOrchestrator
                from app.common.enums.chat import UserRole

                orchestrator = ChatOrchestrator(db, get_redis())
                try:
                    result = await orchestrator.handle_message(
                        request_id=str(uuid.uuid4()),
                        session_id=uuid.UUID(session_id),
                        user_id=user.id,
                        role=UserRole(user.role),
                        text=text,
                    )
                    await db.commit()
                except Exception:
                    await websocket.send_json({"event": "chat.error", "message": "Something went wrong."})
                    continue

            for tool_name in result.actions:
                await websocket.send_json({"event": "chat.tool.started", "tool": tool_name})
                await websocket.send_json({"event": "chat.tool.completed", "tool": tool_name})

            # A production build would stream token-by-token via
            # llm_gateway.primary.stream(...); simplified here to one frame.
            await websocket.send_json({"event": "chat.message.token", "token": result.message})
            await websocket.send_json(
                {
                    "event": "chat.message.completed",
                    "message": result.message,
                    "intent": result.intent.value,
                    "language": result.language.value,
                }
            )

            if result.handoff.triggered:
                await websocket.send_json(
                    {
                        "event": "chat.handoff",
                        "priority": result.handoff.priority.value if result.handoff.priority else None,
                        "handoff_id": result.handoff.handoff_id,
                    }
                )

    except WebSocketDisconnect:
        return
