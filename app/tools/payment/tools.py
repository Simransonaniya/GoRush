from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushPaymentClient


class GetPaymentStatusTool(BaseTool):
    definition = ToolDefinition(
        name="get_payment_status",
        description="Check the payment status for a ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
            "required": ["ride_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushPaymentClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return  # ownership enforced upstream by GoRush payment service using ctx.user_id

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_payment_status(arguments["ride_id"])


class GetRefundStatusTool(BaseTool):
    definition = ToolDefinition(
        name="get_refund_status",
        description="Check the status of a refund for a ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
            "required": ["ride_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushPaymentClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_refund_status(arguments["ride_id"])


class RequestRefundTool(BaseTool):
    definition = ToolDefinition(
        name="request_refund",
        description="Submit a refund request. High risk: requires explicit user confirmation.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["ride_id", "reason"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.HIGH,
        requires_confirmation=True,
        requires_idempotency_key=True,
    )

    def __init__(self, client: GoRushPaymentClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.request_refund(arguments["ride_id"], arguments["reason"])
