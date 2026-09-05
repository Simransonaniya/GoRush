import pytest

from app.common.enums.chat import UserRole
from app.common.exceptions.base import ConfirmationRequiredError, ForbiddenError, ToolDeniedError
from app.tools.registry.tool_spec import ToolContext
from app.tools.registry.registry import build_default_registry


@pytest.fixture
def ctx_customer():
    return ToolContext(user_id="11111111-1111-1111-1111-111111111111", role=UserRole.CUSTOMER,
                        session_id="22222222-2222-2222-2222-222222222222", request_id="req-1")


def test_unregistered_tool_is_denied():
    registry = build_default_registry()
    with pytest.raises(ToolDeniedError):
        registry.get("drop_all_tables")


@pytest.mark.asyncio
async def test_driver_cannot_call_customer_only_tool(ctx_customer):
    from app.tools.router.tool_router import ToolRouter
    # Simulated: role check happens in the router; here we assert the tool
    # definition itself denies non-permitted roles.
    registry = build_default_registry()
    tool = registry.get("cancel_ride")
    assert UserRole.DRIVER not in tool.definition.required_role


@pytest.mark.asyncio
async def test_cancel_ride_requires_confirmation():
    registry = build_default_registry()
    tool = registry.get("cancel_ride")
    assert tool.definition.requires_confirmation is True


@pytest.mark.asyncio
async def test_ownership_check_rejects_foreign_ride_id(ctx_customer):
    registry = build_default_registry()
    tool = registry.get("get_driver_eta")
    with pytest.raises(ForbiddenError):
        await tool.authorize_ownership(ctx_customer, {"ride_id": "someone_elses_ride"})


def test_safety_tool_never_requires_confirmation():
    registry = build_default_registry()
    tool = registry.get("create_safety_incident")
    assert tool.definition.requires_confirmation is False
