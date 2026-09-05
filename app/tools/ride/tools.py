from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.common.exceptions.base import ForbiddenError
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushRideClient


class GetActiveRideTool(BaseTool):
    definition = ToolDefinition(
        name="get_active_ride",
        description="Fetch the caller's current active or most recent ride.",
        input_schema={"type": "object", "properties": {}},
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushRideClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return  # no externally supplied ride id to validate

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        ride = await self.client.get_active_ride(ctx.user_id)
        return {"ride": ride}


class GetDriverEtaTool(BaseTool):
    definition = ToolDefinition(
        name="get_driver_eta",
        description="Get the verified ETA for the driver on a given ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
            "required": ["ride_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushRideClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride = await self.client.get_active_ride(ctx.user_id)
        if not ride or ride["ride_id"] != arguments.get("ride_id"):
            raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_driver_eta(arguments["ride_id"])


class GetFareBreakdownTool(BaseTool):
    definition = ToolDefinition(
        name="get_ride_fare_breakdown",
        description="Get the itemized fare breakdown for a ride.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
            "required": ["ride_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushRideClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride = await self.client.get_active_ride(ctx.user_id)
        if not ride or ride["ride_id"] != arguments.get("ride_id"):
            raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_fare_breakdown(arguments["ride_id"])


class CancelRideTool(BaseTool):
    definition = ToolDefinition(
        name="cancel_ride",
        description="Cancel the caller's active ride. High risk: requires explicit user confirmation.",
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

    def __init__(self, client: GoRushRideClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride = await self.client.get_active_ride(ctx.user_id)
        if not ride or ride["ride_id"] != arguments.get("ride_id"):
            raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.cancel_ride(arguments["ride_id"], arguments["reason"])


class StartRematchTool(BaseTool):
    definition = ToolDefinition(
        name="start_rematch",
        description="Attempt to find a new driver after a cancellation.",
        input_schema={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
            "required": ["ride_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.MEDIUM,
        requires_idempotency_key=True,
    )

    def __init__(self, client: GoRushRideClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        ride = await self.client.get_active_ride(ctx.user_id)
        if not ride or ride["ride_id"] != arguments.get("ride_id"):
            raise ForbiddenError("Ride does not belong to the requesting user")

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.start_rematch(arguments["ride_id"])
