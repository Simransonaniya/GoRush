from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushSafetyClient


class CreateSafetyIncidentTool(BaseTool):
    definition = ToolDefinition(
        name="create_safety_incident",
        description=(
            "Escalate an active safety concern (accident, danger, harassment, SOS) "
            "to the human safety team immediately. Must never be delayed by "
            "conversational confirmation steps."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "ride_id": {"type": ["string", "null"]},
                "details": {"type": "string"},
            },
            "required": ["details"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SAFETY_AGENT, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.CRITICAL,
        requires_confirmation=False,  # emergency flow: act first, never gate on "are you sure?"
        requires_idempotency_key=True,  # BRD S5: prevent duplicate incidents on network retry
    )

    def __init__(self, client: GoRushSafetyClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.create_incident(ctx.user_id, arguments.get("ride_id"), arguments["details"])
