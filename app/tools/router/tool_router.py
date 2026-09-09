import uuid
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.common.enums.chat import ToolExecutionStatus
from app.common.exceptions.base import ConfirmationRequiredError, ToolDeniedError
from app.core.logging import get_logger
from app.tools.idempotency.service import IdempotencyService
from app.tools.models import ToolCall
from app.tools.registry.registry import ToolRegistry
from app.tools.registry.tool_spec import ToolContext

logger = get_logger(__name__)


class ToolRouter:
    """Enforces: registry lookup -> role authorization -> ownership check ->
    confirmation gate -> idempotency -> execute -> audit -> sanitized result.
    A tool is NEVER executed just because the LLM asked for it."""

    def __init__(self, registry: ToolRegistry, db: AsyncSession, redis: Redis):
        self.registry = registry
        self.db = db
        self.audit = AuditService(db)
        self.idempotency = IdempotencyService(redis)

    async def invoke(
        self,
        *,
        ctx: ToolContext,
        tool_name: str,
        arguments: dict[str, Any],
        user_confirmed: bool = False,
        idempotency_key: str | None = None,
        message_id=None,
    ) -> dict[str, Any]:
        tool = self.registry.get(tool_name)  # raises ToolDeniedError if not allowlisted
        definition = tool.definition

        # 1. Role authorization
        if ctx.role not in definition.required_role:
            await self._audit_and_raise(
                ctx, tool_name, arguments, "denied_role",
                ToolDeniedError(f"Role '{ctx.role.value}' cannot call '{tool_name}'"),
            )

        # 2. Ownership / resource authorization (tool-specific, e.g. ride belongs to user)
        await tool.authorize_ownership(ctx, arguments)

        # 3. Confirmation gate for high-risk actions
        needs_confirmation = (
            definition.requires_confirmation
            or (tool_name == "create_support_ticket" and arguments.get("category") == "payment_dispute")
        )
        if needs_confirmation and not user_confirmed:
            await self.audit.record(
                request_id=ctx.request_id, action="tool_confirmation_required",
                decision="pending", user_id=uuid.UUID(ctx.user_id), session_id=uuid.UUID(ctx.session_id),
                tool_name=tool_name, details={"arguments": arguments},
            )
            raise ConfirmationRequiredError(
                f"'{tool_name}' requires explicit user confirmation before executing"
            )

        # 4. Idempotency check for retry-sensitive actions
        if definition.requires_idempotency_key and idempotency_key:
            cached = await self.idempotency.get_cached_result(tool_name, idempotency_key)
            if cached is not None:
                logger.info("tool_idempotent_replay", tool=tool_name, key=idempotency_key)
                return cached

        # 5. Persist a pending tool_call row for audit before executing
        tool_call = ToolCall(
            session_id=uuid.UUID(ctx.session_id),
            message_id=message_id,
            user_id=uuid.UUID(ctx.user_id),
            tool_name=tool_name,
            risk_level=definition.risk_level.value,
            arguments=arguments,
            status=ToolExecutionStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        self.db.add(tool_call)
        await self.db.flush()

        # 6. Execute
        try:
            result = await tool.execute(ctx, arguments)
        except Exception as exc:
            tool_call.status = ToolExecutionStatus.FAILED
            tool_call.result = {"error": str(exc)}
            await self.audit.record(
                request_id=ctx.request_id, action="tool_execution_failed", decision="error",
                user_id=uuid.UUID(ctx.user_id), session_id=uuid.UUID(ctx.session_id), tool_name=tool_name,
                details={"arguments": arguments, "error": str(exc)},
            )
            raise

        # 7. Persist result + audit
        tool_call.status = ToolExecutionStatus.SUCCESS
        tool_call.result = result
        if definition.requires_idempotency_key and idempotency_key:
            await self.idempotency.store_result(tool_name, idempotency_key, result)

        await self.audit.record(
            request_id=ctx.request_id, action="tool_executed", decision="allowed",
            user_id=uuid.UUID(ctx.user_id), session_id=uuid.UUID(ctx.session_id), tool_name=tool_name,
            details={"arguments": arguments, "risk_level": definition.risk_level.value},
        )

        return result

    async def _audit_and_raise(self, ctx, tool_name, arguments, decision, exc):
        await self.audit.record(
            request_id=ctx.request_id, action="tool_denied", decision=decision,
            user_id=uuid.UUID(ctx.user_id), session_id=uuid.UUID(ctx.session_id), tool_name=tool_name,
            details={"arguments": arguments},
        )
        raise exc
