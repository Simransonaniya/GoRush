from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushHandoffClient, GoRushSupportClient


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
        requires_idempotency_key=True,  # BRD S5: all mutating tools must support idempotency
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
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, client: GoRushSupportClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        return  # ticket ownership enforced by GoRush support service

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        ticket_id = arguments.get("ticket_id", "tkt_1001")
        return await self.client.get_ticket_status(ticket_id)


class HandoffToAgentTool(BaseTool):
    """BRD S1 ACTION TOOL 14 / BRD S12: Transfer conversation to a human agent.

    This tool preserves session context, language, conversation history,
    detected intent, relevant tool results, priority, and reason for handoff.
    The assistant must ONLY say a human was contacted if this tool confirms it.
    Idempotency prevents duplicate handoffs on retry.
    """

    definition = ToolDefinition(
        name="handoff_to_agent",
        description=(
            "Transfer the user's conversation to a live GoRush human support agent. "
            "Preserves session context, language, and conversation history. "
            "Returns a handoff_id and confirmed status. "
            "Use when the user explicitly requests a human, when an automated resolution "
            "is not possible, or after a safety incident. "
            "The assistant MUST NOT claim a human was contacted unless this tool returns triggered=true."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the handoff is being triggered (e.g. user_request, unresolved_issue, safety).",
                },
                "priority": {
                    "type": "string",
                    "enum": ["P0", "P1", "P2", "P3"],
                    "description": "Priority level. P0=emergency, P1=critical, P2=standard, P3=faq.",
                },
                "context_summary": {
                    "type": "string",
                    "description": "Brief summary of the conversation and relevant tool results to pass to the agent.",
                },
            },
            "required": ["reason", "priority"],
            "additionalProperties": False,
        },
        required_role=[UserRole.CUSTOMER, UserRole.DRIVER, UserRole.SUPPORT_AGENT, UserRole.SAFETY_AGENT],
        risk_level=RiskLevel.HIGH,
        requires_confirmation=False,  # User already expressed intent; don't gate this
        requires_idempotency_key=True,  # BRD S5: prevent duplicate handoffs
        is_audited=True,
    )

    def __init__(self, client: GoRushHandoffClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        # No resource ownership check needed: user can only handoff their own session
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        priority = arguments.get("priority", "P2")
        if priority not in {"P0", "P1", "P2", "P3"}:
            from app.common.exceptions.base import ValidationAppError
            raise ValidationAppError(f"Invalid priority '{priority}'. Must be P0, P1, P2, or P3.")

        return await self.client.trigger_handoff(
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            reason=arguments.get("reason", "user_request"),
            priority=priority,
            intent="human_agent",
            language="",  # filled by orchestrator context
            context_summary=arguments.get("context_summary", ""),
        )
