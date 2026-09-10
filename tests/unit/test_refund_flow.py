"""
Unit tests for the guided refund conversation flow:
UNDERSTAND -> VERIFY -> GUIDE -> CONFIRM -> ACT -> EXPLAIN -> ESCALATE

Test Cases:
 1. Refund intent detection ("Meri last ride ka refund chahiye.")
 2. Refund verification (ride, payment, refund status queried)
 3. Eligible refund (assistant asks for confirmation)
 4. Confirmation ("Haan kar do" calls request_refund)
 5. Successful refund (assistant reports actual tool result)
 6. Not eligible refund (assistant explains backend-provided reason)
 7. Already refunded (assistant shows actual refund status)
 8. Tool failure (no hallucination + helpful fallback/handoff)
 9. Unauthorized ride (request rejected with ForbiddenError)
10. Duplicate refund request (idempotency prevents duplicate refund)
11. Hinglish confirmation ("Haan", "Ha kar do", "Yes kar do", "Please kar do")
12. Hindi confirmation ("हाँ, कर दीजिए")
13. English confirmation ("Yes, please submit it.")
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.intent.detector import intent_detector
from app.ai.orchestrator.orchestrator import ChatOrchestrator
from app.ai.orchestrator.schema import OrchestrationResult
from app.chat.models import ChatMessage as ChatMessageModel
from app.common.enums.chat import Intent, MessageRole, UserRole
from app.common.exceptions.base import ForbiddenError
from app.tools.payment.tools import GetPaymentStatusTool, GetRefundStatusTool, RequestRefundTool
from app.tools.registry.registry import ToolRegistry
from app.tools.registry.tool_spec import ToolContext
from app.tools.ride.gorush_clients import MockGoRushPaymentClient, MockGoRushRideClient
from app.tools.ride.tools import GetActiveRideTool


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    store = {}

    async def get_mock(key):
        return store.get(key)

    async def set_mock(key, val, ex=None):
        store[key] = val

    redis.get = AsyncMock(side_effect=get_mock)
    redis.set = AsyncMock(side_effect=set_mock)
    return redis


@pytest.fixture
def test_registry():
    ride_client = MockGoRushRideClient()
    payment_client = MockGoRushPaymentClient()
    registry = ToolRegistry()
    registry.register(GetActiveRideTool(ride_client))
    registry.register(GetPaymentStatusTool(payment_client, ride_client))
    registry.register(GetRefundStatusTool(payment_client, ride_client))
    registry.register(RequestRefundTool(payment_client, ride_client))
    return registry, ride_client, payment_client


class TestGuidedRefundFlow:

    # 1. Refund intent detection
    def test_1_refund_intent_detection(self):
        """Input: 'Meri last ride ka refund chahiye.' -> Intent.REFUND, Hinglish, requires_tool=True."""
        text = "Meri last ride ka refund chahiye."
        res = intent_detector.detect(text)
        assert res.intent == Intent.REFUND
        assert res.language.value == "hi-en"  # Hinglish
        assert res.requires_tool is True

    # 2. Refund verification
    @pytest.mark.asyncio
    async def test_2_refund_verification_flow(self, mock_db, mock_redis, test_registry):
        """Verify that get_active_ride, get_payment_status, and get_refund_status are all invoked."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-verify",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Meri last ride ka refund chahiye.",
            )

            assert "get_active_ride" in res.actions
            assert "get_payment_status" in res.actions
            assert "get_refund_status" in res.actions

    # 3. Eligible refund (asks for confirmation)
    @pytest.mark.asyncio
    async def test_3_eligible_refund_asks_confirmation(self, mock_db, mock_redis, test_registry):
        """When ride exists, payment is captured, and refund is not_requested, ask for confirmation."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-eligible",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Meri last ride ka refund chahiye.",
            )

            # Assistant should guide and ask for confirmation
            assert "eligible" in res.message.lower() or "submit" in res.message.lower() or "chahte hain" in res.message.lower()
            assert "request_refund" not in res.actions

            # Verify saved session state
            cached_state = await orchestrator._get_session_state(session_id)
            assert cached_state is not None
            assert cached_state["refund_eligible"] is True
            assert cached_state["confirmation_required"] is True
            assert cached_state["confirmation_received"] is False

    # 4. Confirmation ("Haan kar do" calls request_refund)
    @pytest.mark.asyncio
    async def test_4_confirmation_executes_request_refund(self, mock_db, mock_redis, test_registry):
        """User confirms with 'Haan kar do', request_refund is called."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Pre-seed session state with eligible refund
        prior_state = {
            "intent": "refund",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "selected_ride": "ride_123",
            "ride_verified": True,
            "payment_verified": True,
            "refund_status": "not_requested",
            "refund_eligible": True,
            "confirmation_required": True,
            "confirmation_received": False,
            "amount": 148.0,
        }
        await orchestrator._save_session_state(session_id, prior_state)

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Ye ride refund ke liye eligible hai. Kya aap refund request submit karna chahte hain?",
            intent="refund",
            metadata_json={"pending_intent": "refund", "requires_confirmation": True, "refund_state": prior_state},
        )

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-confirm",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Haan kar do",
            )

            assert "request_refund" in res.actions
            assert res.intent == Intent.REFUND

    # 5. Successful refund reports actual backend tool result
    @pytest.mark.asyncio
    async def test_5_successful_refund_reports_actual_tool_result(self, mock_db, mock_redis, test_registry):
        """Assistant reports success and includes actual backend refund ID (ref_ride_123)."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prior_state = {
            "intent": "refund",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "selected_ride": "ride_123",
            "ride_verified": True,
            "payment_verified": True,
            "refund_status": "not_requested",
            "refund_eligible": True,
            "confirmation_required": True,
            "confirmation_received": False,
            "amount": 148.0,
        }
        await orchestrator._save_session_state(session_id, prior_state)

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Ye ride refund ke liye eligible hai. Kya aap refund request submit karna chahte hain?",
            intent="refund",
            metadata_json={"pending_intent": "refund", "requires_confirmation": True, "refund_state": prior_state},
        )

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-success",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Haan kar do",
            )

            assert "successfully submit" in res.message or "ref_ride_123" in res.message
            assert "ref_ride_123" in res.message

    # 6. Not eligible refund explains backend reason
    @pytest.mark.asyncio
    async def test_6_not_eligible_refund_explains_backend_reason(self, mock_db, mock_redis, test_registry):
        """When payment status is 'failed', explain actual backend reason."""
        registry, ride_client, payment_client = test_registry
        payment_client.set_payment_status("ride_123", "failed")
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-ineligible",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Meri last ride ka refund chahiye.",
            )

            assert "eligible nahi hai" in res.message or "not eligible" in res.message
            assert "failed" in res.message  # Contains actual backend reason

    # 7. Already refunded shows actual refund status
    @pytest.mark.asyncio
    async def test_7_already_refunded_shows_actual_status(self, mock_db, mock_redis, test_registry):
        """When get_refund_status returns 'refund_initiated', explain that refund already exists."""
        registry, ride_client, payment_client = test_registry
        payment_client.set_refund_status("ride_123", "refund_initiated")
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-already",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Meri last ride ka refund chahiye.",
            )

            assert "pehle hi submit" in res.message or "already been submitted" in res.message
            assert "refund_initiated" in res.message

    # 8. Tool failure handles gracefully without hallucination
    @pytest.mark.asyncio
    async def test_8_tool_failure_handles_gracefully(self, mock_db, mock_redis, test_registry):
        """When tool invocation raises an unexpected exception, handle gracefully without hallucination."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.tool_router, "invoke", side_effect=Exception("Database connection timed out")), \
             patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[])):

            res = await orchestrator.handle_message(
                request_id="req-failure",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Meri last ride ka refund chahiye.",
            )

            assert "verify nahi kar paa raha" in res.message or "unable to verify" in res.message
            assert "support" in res.message

    # 9. Unauthorized ride request rejected
    @pytest.mark.asyncio
    async def test_9_unauthorized_ride_request_rejected(self, test_registry):
        """User cannot access or refund another user's ride."""
        registry, ride_client, payment_client = test_registry
        refund_tool = RequestRefundTool(payment_client, ride_client)
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        # User A owns ride_123
        ride_client.set_active_ride(user_a, {"ride_id": "ride_123", "status": "completed"})
        # User B has no ride or a different ride
        ride_client.set_active_ride(user_b, {"ride_id": "ride_999", "status": "completed"})

        ctx_b = ToolContext(user_id=user_b, role=UserRole.CUSTOMER, session_id="s1", request_id="r1")

        # User B tries to refund User A's ride_123
        with pytest.raises(ForbiddenError):
            await refund_tool.authorize_ownership(ctx_b, {"ride_id": "ride_123", "reason": "refund"})

    # 10. Duplicate refund request / idempotency
    @pytest.mark.asyncio
    async def test_10_duplicate_refund_prevented(self, mock_db, mock_redis, test_registry):
        """Subsequent confirmation on already-confirmed refund does not re-submit refund."""
        registry, ride_client, payment_client = test_registry
        orchestrator = ChatOrchestrator(mock_db, mock_redis, registry=registry)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # State where refund was ALREADY submitted (confirmation_received=True)
        prior_state = {
            "intent": "refund",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "selected_ride": "ride_123",
            "ride_verified": True,
            "payment_verified": True,
            "refund_status": "refund_initiated",
            "refund_eligible": True,
            "confirmation_required": True,
            "confirmation_received": True,
            "amount": 148.0,
        }
        await orchestrator._save_session_state(session_id, prior_state)

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Done. Aapki refund request successfully submit ho gayi hai.",
            intent="refund",
            metadata_json={"pending_intent": "refund", "requires_confirmation": False, "refund_state": prior_state},
        )

        with patch.object(orchestrator.conversations, "add_message", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_session", new=AsyncMock()), \
             patch.object(orchestrator.conversations, "get_recent_messages", new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, "maybe_summarize", new=AsyncMock()):

            res = await orchestrator.handle_message(
                request_id="req-dup",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Haan kar do",
            )

            # request_refund tool should NOT be called again
            assert "request_refund" not in res.actions

    # 11. Hinglish confirmation detection
    def test_11_hinglish_confirmations(self):
        """Natural Hinglish affirmations must be recognized."""
        samples = ["Haan", "Ha kar do", "Haan kar do", "Yes kar do", "Please kar do", "kar do", "bilkul kar do"]
        for sample in samples:
            assert ChatOrchestrator._is_confirmation_text(sample) is True, f"Failed on Hinglish: {sample}"

    # 12. Hindi confirmation detection
    def test_12_hindi_confirmations(self):
        """Natural Hindi affirmations must be recognized."""
        samples = ["हाँ", "हाँ, कर दीजिए", "हाँ कर दीजिए", "कर दो", "कर दीजिए", "हाँ जी"]
        for sample in samples:
            assert ChatOrchestrator._is_confirmation_text(sample) is True, f"Failed on Hindi: {sample}"

    # 13. English confirmation detection
    def test_13_english_confirmations(self):
        """Natural English affirmations must be recognized."""
        samples = ["Yes", "Yes, please submit it.", "Yes submit it", "Please submit it", "Yes, please", "Confirm"]
        for sample in samples:
            assert ChatOrchestrator._is_confirmation_text(sample) is True, f"Failed on English: {sample}"
