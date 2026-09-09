from typing import Any

from app.common.enums.chat import RiskLevel, UserRole
from app.tools.registry.tool_spec import BaseTool, ToolContext, ToolDefinition
from app.tools.ride.gorush_clients import GoRushDriverClient


class GetDriverEarningsTool(BaseTool):
    """BRD S1 READ TOOL 7: Read driver earnings.

    The LLM must never invent earnings numbers. Only actual GoRush service
    data returned by this tool may appear in the assistant response.
    """

    definition = ToolDefinition(
        name="get_driver_earnings",
        description=(
            "Fetch the authenticated driver's earnings summary for a specified period "
            "(today | week | month). Returns gross earnings, net earnings, trip count, "
            "and currency. Driver-only -- customers and non-driver roles are denied."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "description": "The earnings period to fetch. Must be one of: today, week, month.",
                },
            },
            "required": ["period"],
            "additionalProperties": False,
        },
        required_role=[UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
        requires_confirmation=False,
        requires_idempotency_key=False,
        is_audited=True,
    )

    def __init__(self, client: GoRushDriverClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        # Ownership is implicit: the service returns data only for ctx.user_id.
        # No external resource ID is accepted -- the LLM cannot request another
        # driver's earnings by passing a different user_id here.
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        period = arguments.get("period", "today")
        if period not in {"today", "week", "month"}:
            from app.common.exceptions.base import ValidationAppError
            raise ValidationAppError(
                f"Invalid period '{period}'. Must be one of: today, week, month."
            )
        return await self.client.get_earnings(ctx.user_id, period)


class GetDocumentStatusTool(BaseTool):
    """BRD S1 READ TOOL 8: Read driver document status.

    Returns per-document approval/rejection status, expiry dates, and an
    overall 'can_drive' flag. The LLM must never fabricate document status.
    """

    definition = ToolDefinition(
        name="get_document_status",
        description=(
            "Fetch the authenticated driver's document verification status "
            "(driving license, RC, insurance, PUC, Aadhaar, PAN, etc.). "
            "Returns approval state, expiry dates, and whether the driver is "
            "currently eligible to drive. Driver-only read operation."
        ),
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        required_role=[UserRole.DRIVER, UserRole.SUPPORT_AGENT],
        risk_level=RiskLevel.LOW,
        requires_confirmation=False,
        requires_idempotency_key=False,
        is_audited=True,
    )

    def __init__(self, client: GoRushDriverClient):
        self.client = client

    async def authorize_ownership(self, ctx: ToolContext, arguments: dict[str, Any]) -> None:
        # Ownership implicit via ctx.user_id -- no external ID to validate.
        return

    async def execute(self, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.client.get_document_status(ctx.user_id)
