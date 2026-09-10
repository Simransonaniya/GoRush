from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.common.exceptions.base import ForbiddenError
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushPaymentClient, GoRushRideClient


class GetPaymentStatusTool(BaseTool):
    definition = ToolDefinition(
        name="get_payment_status",
        description="Check the payment status for a ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushPaymentClient, ride_client: GoRushRideClient | None = None):
        self.client = client
        self.ride_client = ride_client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride_id = arguments.get("ride_id")
        if ride_id and self.ride_client:
            ride = await self.ride_client.get_active_ride(ctx.user_id)
            if not ride or ride.get("ride_id") != ride_id:
                raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        ride_id = arguments.get("ride_id", "ride_123")
        return await self.client.get_payment_status(ride_id)


class GetRefundStatusTool(BaseTool):
    definition = ToolDefinition(
        name="get_refund_status",
        description="Check the status of a refund for a ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushPaymentClient, ride_client: GoRushRideClient | None = None):
        self.client = client
        self.ride_client = ride_client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride_id = arguments.get("ride_id")
        if ride_id and self.ride_client:
            ride = await self.ride_client.get_active_ride(ctx.user_id)
            if not ride or ride.get("ride_id") != ride_id:
                raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        ride_id = arguments.get("ride_id", "ride_123")
        return await self.client.get_refund_status(ride_id)


class RequestRefundTool(BaseTool):
    definition = ToolDefinition(
        name="request_refund",
        description="Submit a refund request. High risk: requires explicit user confirmation.",
        input_schema={
            "type": "object",
            "properties": {
                "ride_id": {"type": "string", "description": "The ride ID to refund"},
                "amount": {"type": "number", "description": "Refund amount in the user's currency"},
                "reason": {"type": "string", "description": "Reason for the refund request"},
            },
            "required": ["ride_id", "amount", "reason"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.HIGH,
        requires_confirmation=True,
        requires_idempotency_key=True,
    )

    def __init__(self, client: GoRushPaymentClient, ride_client: GoRushRideClient | None = None):
        self.client = client
        self.ride_client = ride_client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride_id = arguments.get("ride_id")
        if ride_id and self.ride_client:
            ride = await self.ride_client.get_active_ride(ctx.user_id)
            if not ride or ride.get("ride_id") != ride_id:
                raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        ride_id = arguments.get("ride_id", "ride_123")
        reason = arguments.get("reason", "Refund requested by customer")
        amount = arguments.get("amount")
        return await self.client.request_refund(
            ride_id=ride_id,
            reason=reason,
            amount=amount,
        )
