from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushSupportClient


class CreateSupportTicketTool(BaseTool):
    definition = ToolDefinition(
        name="create_support_ticket",
        description="Open a support ticket for an unresolved issue.",
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["category", "description"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushSupportClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.create_ticket(ctx.user_id, arguments["category"], arguments["description"])


class GetTicketStatusTool(BaseTool):
    definition = ToolDefinition(
        name="get_ticket_status",
        description="Check the status of an existing support ticket.",
        input_schema={
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushSupportClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return  # ticket ownership enforced by GoRush support service

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_ticket_status(arguments["ticket_id"])
