"""
BRD S17 B, C, D: Read Tools, Action Tools, and Idempotency Tests.

Tests the full ToolRouter pipeline:
  auth -> ownership -> confirmation gate -> idempotency -> execute -> audit
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.common.enums.chat import RiskLevel, UserRole
from app.common.exceptions.base import (
    ConfirmationRequiredError,
    ForbiddenError,
    ToolDeniedError,
    ValidationAppError,
)
from app.tools.registry.registry import build_default_registry
from app.tools.registry.tool_spec import ToolContext
from app.tools.router.tool_router import ToolRouter


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()  # synchronous add
    mock_result = MagicMock()
    mock_result.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def registry():
    return build_default_registry()


@pytest.fixture
def router(registry, mock_db, mock_redis):
    return ToolRouter(registry, mock_db, mock_redis)


def make_ctx(role: UserRole = UserRole.DRIVER) -> ToolContext:
    return ToolContext(
        user_id="11111111-1111-1111-1111-111111111111",
        role=role,
        session_id="22222222-2222-2222-2222-222222222222",
        request_id="req-test",
    )


# ------------------------------------------------------------------
# B: Read Tool Tests
# ------------------------------------------------------------------

class TestReadTools:

    @pytest.mark.asyncio
    async def test_get_active_ride_driver_authenticated(self, router):
        """Authenticated driver can call get_active_ride."""
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_active_ride", arguments={})
        assert "ride" in result

    @pytest.mark.asyncio
    async def test_get_active_ride_customer_authenticated(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        result = await router.invoke(ctx=ctx, tool_name="get_active_ride", arguments={})
        assert "ride" in result

    @pytest.mark.asyncio
    async def test_get_driver_earnings_driver_authenticated(self, router):
        """Driver can read their own earnings."""
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_driver_earnings", arguments={"period": "today"})
        assert "gross_earnings" in result
        assert result["period"] == "today"

    @pytest.mark.asyncio
    async def test_get_driver_earnings_week(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_driver_earnings", arguments={"period": "week"})
        assert result["period"] == "week"

    @pytest.mark.asyncio
    async def test_get_driver_earnings_month(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_driver_earnings", arguments={"period": "month"})
        assert result["period"] == "month"

    @pytest.mark.asyncio
    async def test_get_driver_earnings_customer_role_denied(self, router):
        """Customer must not access driver earnings."""
        ctx = make_ctx(UserRole.CUSTOMER)
        with pytest.raises(ToolDeniedError):
            await router.invoke(ctx=ctx, tool_name="get_driver_earnings", arguments={"period": "today"})

    @pytest.mark.asyncio
    async def test_get_document_status_driver_authenticated(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_document_status", arguments={})
        assert "documents" in result
        assert "can_drive" in result

    @pytest.mark.asyncio
    async def test_get_document_status_customer_role_denied(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        with pytest.raises(ToolDeniedError):
            await router.invoke(ctx=ctx, tool_name="get_document_status", arguments={})

    @pytest.mark.asyncio
    async def test_get_payment_status_valid(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        result = await router.invoke(ctx=ctx, tool_name="get_payment_status", arguments={"ride_id": "ride_123"})
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_refund_status_valid(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        result = await router.invoke(ctx=ctx, tool_name="get_refund_status", arguments={"ride_id": "ride_123"})
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_ticket_status_valid(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(ctx=ctx, tool_name="get_ticket_status", arguments={"ticket_id": "tkt_123"})
        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_unregistered_tool_raises_tool_denied(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        with pytest.raises(ToolDeniedError):
            await router.invoke(ctx=ctx, tool_name="exec_sql", arguments={})


# ------------------------------------------------------------------
# C: Action Tool Tests
# ------------------------------------------------------------------

class TestActionTools:

    @pytest.mark.asyncio
    async def test_cancel_ride_requires_confirmation(self, router):
        """cancel_ride must raise ConfirmationRequiredError without user_confirmed."""
        ctx = make_ctx(UserRole.CUSTOMER)
        tool = router.registry.get("cancel_ride")
        with patch.object(tool, "authorize_ownership", new=AsyncMock(return_value=None)):
            with pytest.raises(ConfirmationRequiredError):
                await router.invoke(
                    ctx=ctx, tool_name="cancel_ride",
                    arguments={"ride_id": "ride_123", "reason": "too long"},
                    user_confirmed=False,
                )

    @pytest.mark.asyncio
    async def test_cancel_ride_authorized_and_confirmed(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        tool = router.registry.get("cancel_ride")
        with patch.object(tool, "authorize_ownership", new=AsyncMock(return_value=None)):
            result = await router.invoke(
                ctx=ctx, tool_name="cancel_ride",
                arguments={"ride_id": "ride_123", "reason": "user request"},
                user_confirmed=True,
            )
            assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_ride_driver_role_denied(self, router):
        """Driver role must not be allowed to call cancel_ride."""
        ctx = make_ctx(UserRole.DRIVER)
        with pytest.raises(ToolDeniedError):
            await router.invoke(
                ctx=ctx, tool_name="cancel_ride",
                arguments={"ride_id": "ride_123", "reason": "test"},
                user_confirmed=True,
            )

    @pytest.mark.asyncio
    async def test_request_refund_requires_confirmation(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        with pytest.raises(ConfirmationRequiredError):
            await router.invoke(
                ctx=ctx, tool_name="request_refund",
                arguments={"ride_id": "ride_123", "amount": 50.0, "reason": "overcharge"},
                user_confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_request_refund_confirmed(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        result = await router.invoke(
            ctx=ctx, tool_name="request_refund",
            arguments={"ride_id": "ride_123", "amount": 50.0, "reason": "overcharge"},
            user_confirmed=True,
        )
        assert "status" in result

    @pytest.mark.asyncio
    async def test_create_support_ticket_driver(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(
            ctx=ctx, tool_name="create_support_ticket",
            arguments={"category": "payment_dispute", "description": "Customer didn't pay"},
            user_confirmed=True,
        )
        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_create_safety_incident_no_confirmation_needed(self, router):
        """Safety incident must execute immediately — never gate on confirmation."""
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(
            ctx=ctx, tool_name="create_safety_incident",
            arguments={"details": "Accident on highway"},
            user_confirmed=False,  # must still execute
        )
        assert "incident_id" in result

    @pytest.mark.asyncio
    async def test_create_safety_incident_customer(self, router):
        ctx = make_ctx(UserRole.CUSTOMER)
        result = await router.invoke(
            ctx=ctx, tool_name="create_safety_incident",
            arguments={"details": "Driver is threatening me"},
            user_confirmed=False,
        )
        assert "incident_id" in result

    @pytest.mark.asyncio
    async def test_handoff_to_agent_creates_handoff(self, router):
        ctx = make_ctx(UserRole.DRIVER)
        result = await router.invoke(
            ctx=ctx, tool_name="handoff_to_agent",
            arguments={"reason": "user_request", "priority": "P2"},
            user_confirmed=True,
        )
        assert result["triggered"] is True
        assert "handoff_id" in result

    @pytest.mark.asyncio
    async def test_handoff_to_agent_invalid_priority(self, router):
        """Invalid priority enum value must raise, not silently pass."""
        ctx = make_ctx(UserRole.DRIVER)
        with pytest.raises(ValidationAppError):
            await router.invoke(
                ctx=ctx, tool_name="handoff_to_agent",
                arguments={"reason": "test", "priority": "ULTRA_HIGH"},
                user_confirmed=True,
            )

    @pytest.mark.asyncio
    async def test_start_rematch_driver_denied(self, router):
        """start_rematch is for customers, drivers should be denied."""
        ctx = make_ctx(UserRole.DRIVER)
        tool = router.registry.get("start_rematch")
        # Verify role check
        assert UserRole.DRIVER not in tool.definition.required_role

    @pytest.mark.asyncio
    async def test_ownership_check_rejects_foreign_ride(self, router):
        """A customer cannot fetch ETA for another user's ride."""
        ctx = make_ctx(UserRole.CUSTOMER)
        with pytest.raises(ForbiddenError):
            await router.invoke(
                ctx=ctx, tool_name="get_driver_eta",
                arguments={"ride_id": "ride_999_belongs_to_someone_else"},
            )


# ------------------------------------------------------------------
# D: Idempotency Tests
# ------------------------------------------------------------------

class TestIdempotency:

    @pytest.mark.asyncio
    async def test_same_key_returns_cached_result(self, router):
        """Same idempotency key must return the cached result without re-executing."""
        cached = {"triggered": True, "handoff_id": "handoff_9999", "status": "agent_assigned", "priority": "P2", "estimated_wait_seconds": 120}
        ctx = make_ctx(UserRole.DRIVER)
        with patch.object(router.idempotency, "get_cached_result", new=AsyncMock(return_value=cached)):
            result = await router.invoke(
                ctx=ctx, tool_name="handoff_to_agent",
                arguments={"reason": "user_request", "priority": "P2"},
                user_confirmed=True,
                idempotency_key="idem-key-001",
            )
            assert result == cached

    @pytest.mark.asyncio
    async def test_different_key_executes_fresh(self, router):
        """Different idempotency key must not return the previous result."""
        ctx = make_ctx(UserRole.DRIVER)
        with patch.object(router.idempotency, "get_cached_result", new=AsyncMock(return_value=None)):
            result = await router.invoke(
                ctx=ctx, tool_name="handoff_to_agent",
                arguments={"reason": "user_request", "priority": "P1"},
                user_confirmed=True,
                idempotency_key="idem-key-002",
            )
            assert result["triggered"] is True

    @pytest.mark.asyncio
    async def test_no_duplicate_ticket_on_retry(self, router):
        """create_support_ticket with same key must not create two tickets."""
        cached = {"ticket_id": "tkt_9999", "status": "open", "category": "payment_dispute"}
        ctx = make_ctx(UserRole.DRIVER)
        execute_spy = AsyncMock(return_value={"ticket_id": "tkt_NEW", "status": "open", "category": "payment_dispute"})
        tool = router.registry.get("create_support_ticket")
        with patch.object(router.idempotency, "get_cached_result", new=AsyncMock(return_value=cached)), \
             patch.object(tool, "execute", new=execute_spy):
            result = await router.invoke(
                ctx=ctx, tool_name="create_support_ticket",
                arguments={"category": "payment_dispute", "description": "Cash not paid"},
                user_confirmed=True,
                idempotency_key="idem-ticket-dup",
            )
            assert result["ticket_id"] == "tkt_9999"
            execute_spy.assert_not_called()  # execute must NOT have been called

    @pytest.mark.asyncio
    async def test_no_duplicate_safety_incident_on_retry(self, router):
        """create_safety_incident with same key returns original, no second incident."""
        cached = {"incident_id": "inc_5555", "status": "escalated_to_safety_team"}
        ctx = make_ctx(UserRole.DRIVER)
        execute_spy = AsyncMock(return_value={"incident_id": "inc_NEW", "status": "escalated"})
        tool = router.registry.get("create_safety_incident")
        with patch.object(router.idempotency, "get_cached_result", new=AsyncMock(return_value=cached)), \
             patch.object(tool, "execute", new=execute_spy):
            result = await router.invoke(
                ctx=ctx, tool_name="create_safety_incident",
                arguments={"details": "Accident on highway"},
                idempotency_key="idem-safety-dup",
            )
            assert result["incident_id"] == "inc_5555"
            execute_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_duplicate_refund_on_retry(self, router):
        """request_refund with same key must not create two refunds."""
        cached = {"ride_id": "ride_123", "status": "refund_initiated", "reason": "overcharge", "amount": 50.0}
        ctx = make_ctx(UserRole.CUSTOMER)
        execute_spy = AsyncMock(return_value={"ride_id": "ride_123", "status": "refund_initiated_SECOND"})
        tool = router.registry.get("request_refund")
        with patch.object(router.idempotency, "get_cached_result", new=AsyncMock(return_value=cached)), \
             patch.object(tool, "execute", new=execute_spy):
            result = await router.invoke(
                ctx=ctx, tool_name="request_refund",
                arguments={"ride_id": "ride_123", "amount": 50.0, "reason": "overcharge"},
                user_confirmed=True,
                idempotency_key="idem-refund-dup",
            )
            assert result["status"] == "refund_initiated"
            execute_spy.assert_not_called()
