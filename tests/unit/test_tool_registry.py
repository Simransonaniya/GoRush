"""
BRD S17-A: Tool Registration Tests
Verifies all 14 BRD-required tools are registered, schemas are valid,
and unregistered tools are correctly denied.
"""
import pytest
from app.tools.registry.registry import build_default_registry
from app.common.exceptions.base import ToolDeniedError


ALL_BRD_TOOLS = [
    # READ TOOLS (8)
    "get_active_ride",
    "get_driver_eta",
    "get_ride_fare_breakdown",
    "get_payment_status",
    "get_refund_status",
    "get_ticket_status",
    "get_driver_earnings",
    "get_document_status",
    # ACTION TOOLS (6)
    "request_refund",
    "cancel_ride",
    "start_rematch",
    "create_support_ticket",
    "create_safety_incident",
    "handoff_to_agent",
]

READ_TOOLS = {
    "get_active_ride", "get_driver_eta", "get_ride_fare_breakdown",
    "get_payment_status", "get_refund_status", "get_ticket_status",
    "get_driver_earnings", "get_document_status",
}

ACTION_TOOLS = {
    "request_refund", "cancel_ride", "start_rematch",
    "create_support_ticket", "create_safety_incident", "handoff_to_agent",
}

IDEMPOTENCY_REQUIRED = {
    "request_refund", "cancel_ride", "start_rematch",
    "create_support_ticket", "create_safety_incident", "handoff_to_agent",
}


@pytest.fixture(scope="module")
def registry():
    return build_default_registry()


class TestToolRegistration:

    def test_all_14_tools_registered(self, registry):
        """All 14 BRD-required tools must be registered."""
        specs = {s["name"] for s in registry.list_specs_for_llm()}
        assert specs == set(ALL_BRD_TOOLS), (
            f"Missing: {set(ALL_BRD_TOOLS) - specs}\n"
            f"Extra: {specs - set(ALL_BRD_TOOLS)}"
        )

    @pytest.mark.parametrize("tool_name", ALL_BRD_TOOLS)
    def test_tool_schema_has_required_fields(self, registry, tool_name):
        """Every tool spec exposed to the LLM must have name, description, input_schema."""
        tool = registry.get(tool_name)
        assert tool.definition.name == tool_name
        assert isinstance(tool.definition.description, str) and len(tool.definition.description) > 10
        assert isinstance(tool.definition.input_schema, dict)
        assert "type" in tool.definition.input_schema

    def test_unregistered_tool_raises_tool_denied(self, registry):
        """The tool allowlist must reject any name not in the registry."""
        with pytest.raises(ToolDeniedError):
            registry.get("drop_all_tables")

    def test_sql_injection_tool_name_denied(self, registry):
        with pytest.raises(ToolDeniedError):
            registry.get("'; DROP TABLE users; --")

    def test_arbitrary_admin_tool_denied(self, registry):
        with pytest.raises(ToolDeniedError):
            registry.get("give_admin_access")

    @pytest.mark.parametrize("tool_name", READ_TOOLS)
    def test_read_tools_have_low_or_medium_risk(self, registry, tool_name):
        """Read tools should never be HIGH or CRITICAL risk."""
        tool = registry.get(tool_name)
        assert tool.definition.risk_level.value in {"low", "medium"}

    @pytest.mark.parametrize("tool_name", IDEMPOTENCY_REQUIRED)
    def test_action_tools_require_idempotency_key(self, registry, tool_name):
        """All BRD S5 action tools must have requires_idempotency_key=True."""
        tool = registry.get(tool_name)
        assert tool.definition.requires_idempotency_key is True, (
            f"'{tool_name}' must have requires_idempotency_key=True (BRD S5)"
        )

    def test_safety_tool_never_requires_confirmation(self, registry):
        """create_safety_incident must bypass all confirmation gates (BRD S11)."""
        tool = registry.get("create_safety_incident")
        assert tool.definition.requires_confirmation is False

    def test_safety_tool_is_critical_risk(self, registry):
        tool = registry.get("create_safety_incident")
        assert tool.definition.risk_level.value == "critical"

    def test_cancel_ride_requires_confirmation(self, registry):
        tool = registry.get("cancel_ride")
        assert tool.definition.requires_confirmation is True

    def test_request_refund_requires_confirmation(self, registry):
        tool = registry.get("request_refund")
        assert tool.definition.requires_confirmation is True

    def test_list_specs_for_llm_count(self, registry):
        specs = registry.list_specs_for_llm()
        assert len(specs) == 14

    def test_specs_for_llm_have_no_extra_keys(self, registry):
        """The LLM-facing spec must only expose name, description, input_schema.
        Internal fields like required_role must never be in the LLM spec."""
        for spec in registry.list_specs_for_llm():
            assert set(spec.keys()) == {"name", "description", "input_schema"}
