from app.common.exceptions.base import ToolDeniedError
from app.tools.registry.tool_spec import BaseTool


class ToolRegistry:
    """The single allowlist of tools the LLM is permitted to invoke.
    The LLM never gets raw DB/API access -- only what's registered here."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.definition.name] = tool

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolDeniedError(f"Tool '{name}' is not registered / not allowlisted")
        return tool

    def list_specs_for_llm(self) -> list[dict]:
        """Tool specs exposed to the LLM as callable functions."""
        return [
            {
                "name": t.definition.name,
                "description": t.definition.description,
                "input_schema": t.definition.input_schema,
            }
            for t in self._tools.values()
        ]


def build_default_registry() -> ToolRegistry:
    from app.tools.payment.tools import (
        GetPaymentStatusTool,
        GetRefundStatusTool,
        RequestRefundTool,
    )
    from app.tools.ride.gorush_clients import (
        MockGoRushPaymentClient,
        MockGoRushRideClient,
        MockGoRushSafetyClient,
        MockGoRushSupportClient,
    )
    from app.tools.ride.tools import (
        CancelRideTool,
        GetActiveRideTool,
        GetDriverEtaTool,
        GetFareBreakdownTool,
        StartRematchTool,
    )
    from app.tools.safety.tools import CreateSafetyIncidentTool
    from app.tools.support.tools import CreateSupportTicketTool, GetTicketStatusTool

    ride_client = MockGoRushRideClient()
    payment_client = MockGoRushPaymentClient()
    support_client = MockGoRushSupportClient()
    safety_client = MockGoRushSafetyClient()

    registry = ToolRegistry()
    registry.register(GetActiveRideTool(ride_client))
    registry.register(GetDriverEtaTool(ride_client))
    registry.register(GetFareBreakdownTool(ride_client))
    registry.register(CancelRideTool(ride_client))
    registry.register(StartRematchTool(ride_client))
    registry.register(GetPaymentStatusTool(payment_client))
    registry.register(GetRefundStatusTool(payment_client))
    registry.register(RequestRefundTool(payment_client))
    registry.register(CreateSupportTicketTool(support_client))
    registry.register(GetTicketStatusTool(support_client))
    registry.register(CreateSafetyIncidentTool(safety_client))
    return registry


default_tool_registry = build_default_registry()
