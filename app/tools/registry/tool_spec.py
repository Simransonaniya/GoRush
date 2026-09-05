from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.common.enums.chat import RiskLevel, UserRole


class ToolContext(BaseModel):
    """Everything a tool needs about the caller, validated *before* the
    tool body ever runs. Tools must never trust IDs in their own arguments
    without cross-checking against this context."""

    user_id: str
    role: UserRole
    session_id: str
    request_id: str


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    required_role: list[UserRole]
    risk_level: RiskLevel
    requires_confirmation: bool = False
    requires_idempotency_key: bool = False
    is_audited: bool = True


class BaseTool(ABC):
    definition: ToolDefinition

    @abstractmethod
    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        """Raise ForbiddenError if the resource in `arguments` (e.g. rideId)
        does not belong to ctx.user_id. This is separate from role-based
        authorization, which the router checks generically."""
        ...

    @abstractmethod
    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]: ...
