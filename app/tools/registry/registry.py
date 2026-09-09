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
    from app.tools.driver.tools import (
        GetDocumentStatusTool,
        GetDriverEarningsTool,
    )
    from app.tools.payment.tools import (
        GetPaymentStatusTool,
        GetRefundStatusTool,
        RequestRefundTool,
    )
    from app.tools.ride.gorush_clients import (
        MockGoRushDriverClient,
        MockGoRushHandoffClient,
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
    from app.tools.support.tools import CreateSupportTicketTool, GetTicketStatusTool, HandoffToAgentTool

    ride_client = MockGoRushRideClient()
    payment_client = MockGoRushPaymentClient()
    support_client = MockGoRushSupportClient()
    safety_client = MockGoRushSafetyClient()
    driver_client = MockGoRushDriverClient()
    handoff_client = MockGoRushHandoffClient()

    registry = ToolRegistry()
    # --- READ TOOLS (8) ---
    registry.register(GetActiveRideTool(ride_client))           # 1
    registry.register(GetDriverEtaTool(ride_client))            # 2
    registry.register(GetFareBreakdownTool(ride_client))        # 3
    registry.register(GetPaymentStatusTool(payment_client))     # 4
    registry.register(GetRefundStatusTool(payment_client))      # 5
    registry.register(GetTicketStatusTool(support_client))      # 6
    registry.register(GetDriverEarningsTool(driver_client))     # 7
    registry.register(GetDocumentStatusTool(driver_client))     # 8
    # --- ACTION TOOLS (6) ---
    registry.register(RequestRefundTool(payment_client))        # 9
    registry.register(CancelRideTool(ride_client))              # 10
    registry.register(StartRematchTool(ride_client))            # 11
    registry.register(CreateSupportTicketTool(support_client))  # 12
    registry.register(CreateSafetyIncidentTool(safety_client))  # 13
    registry.register(HandoffToAgentTool(handoff_client))       # 14
    return registry


default_tool_registry = build_default_registry()
