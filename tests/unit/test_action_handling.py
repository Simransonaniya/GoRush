"""
Tests for action-handling behavior, pending intent preservation, and confirmation flows.

Covers:
  1. Confirmation after cash_payment (preserves intent=cash_payment, executes create_support_ticket)
  2. Confirmation after ride cancellation (preserves intent=cancellation, executes cancel_ride)
  3. English confirmation ("Yes, do it.")
  4. Hindi confirmation ("हाँ, शुरू कर दो।")
  5. Hinglish confirmation ("Haan, start kar do.")
  6. Gujarati confirmation ("હા, શરૂ કરો.")
  7. Bengali confirmation ("হ্যাঁ, শুরু করুন।")
  8. Rajasthani confirmation ("हौ, शुरू कर दो")
  9. Confirmation with no pending action (remains unknown, no action)
 10. Duplicate confirmation / idempotency (uses cached result)
 11. Unauthorized confirmation / action (denies action for role)
 12. Expired / stale pending action (ignores old prompt if intervening message occurred)
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.ai.orchestrator.orchestrator import ChatOrchestrator
from app.ai.orchestrator.schema import OrchestrationResult
from app.chat.models import ChatMessage as ChatMessageModel
from app.common.enums.chat import Intent, Language, MessageRole, UserRole
from app.ai.llm.provider import ChatMessage
from app.tools.registry.tool_spec import ToolContext
from app.tools.router.tool_router import ToolRouter


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
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


class TestPendingIntentActionHandling:

    @pytest.mark.asyncio
    async def test_1_confirmation_after_cash_payment(self, mock_db, mock_redis):
        """1. Confirmation after cash_payment preserves intent=cash_payment."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock previous assistant message with pending cash_payment intent
        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Payment dispute start karne ke liye confirmation chahiye...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-1",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="Haan, start kar do.",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]
            assert "Payment dispute ticket" in res.message

    @pytest.mark.asyncio
    async def test_2_confirmation_after_ride_cancellation(self, mock_db, mock_redis):
        """2. Confirmation after ride cancellation preserves intent=cancellation."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Confirmation is required to cancel your ride...",
            intent="cancellation",
            metadata_json={"pending_intent": "cancellation", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-2",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Yes, cancel it.",
            )

            assert res.intent == Intent.CANCELLATION
            assert res.actions == ["cancel_ride"]

    @pytest.mark.asyncio
    async def test_3_english_confirmation(self, mock_db, mock_redis):
        """3. English confirmation ('Yes, do it.')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Confirmation is required to process your refund request...",
            intent="refund",
            metadata_json={"pending_intent": "refund", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-3",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.CUSTOMER,
                text="Yes, do it.",
            )

            assert res.intent == Intent.REFUND
            assert res.actions == ["request_refund"]

    @pytest.mark.asyncio
    async def test_4_hindi_confirmation(self, mock_db, mock_redis):
        """4. Hindi confirmation ('हाँ, शुरू कर दो।')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="पेमेंट विवाद शुरू करने के लिए पुष्टि की आवश्यकता है...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-4",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="हाँ, शुरू कर दो।",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]

    @pytest.mark.asyncio
    async def test_5_hinglish_confirmation(self, mock_db, mock_redis):
        """5. Hinglish confirmation ('Bilkul, kar do.')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Payment dispute start karne ke liye confirmation chahiye...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-5",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="Bilkul, kar do.",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]

    @pytest.mark.asyncio
    async def test_6_gujarati_confirmation(self, mock_db, mock_redis):
        """6. Gujarati confirmation ('હા, શરૂ કરો.')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="ચુકવણી વિવાદ શરૂ કરવા માટે પુષ્ટિ જરૂરી છે...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-6",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="હા, શરૂ કરો.",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]

    @pytest.mark.asyncio
    async def test_7_bengali_confirmation(self, mock_db, mock_redis):
        """7. Bengali confirmation ('হ্যাঁ, শুরু করুন।')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="পেমেন্ট বিরোধ শুরু করার জন্য নিশ্চিতকরণ প্রয়োজন...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-7",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="হ্যাঁ, শুরু করুন।",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]

    @pytest.mark.asyncio
    async def test_8_rajasthani_confirmation(self, mock_db, mock_redis):
        """8. Rajasthani confirmation ('हौ, शुरू कर दो')."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="पेमेंट विवाद शुरू करवा खातर पुष्टि री आवश्यकता है...",
            intent="cash_payment",
            metadata_json={"pending_intent": "cash_payment", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-8",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="हौ, शुरू कर दो",
            )

            assert res.intent == Intent.CASH_PAYMENT
            assert res.actions == ["create_support_ticket"]

    @pytest.mark.asyncio
    async def test_9_confirmation_with_no_pending_action(self, mock_db, mock_redis):
        """9. Confirmation with no pending action remains unknown, triggers no tools."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-9",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="Haan",
            )

            assert res.intent == Intent.UNKNOWN
            assert res.actions == []

    @pytest.mark.asyncio
    async def test_10_duplicate_confirmation_idempotency(self, mock_db, mock_redis):
        """10. Duplicate confirmation request uses cached idempotency result from Redis."""
        router = ToolRouter(orchestrator_registry(), mock_db, mock_redis)
        ctx = ToolContext(
            user_id="11111111-1111-1111-1111-111111111111",
            role=UserRole.CUSTOMER,
            session_id="22222222-2222-2222-2222-222222222222",
            request_id="req-10",
        )

        cached_data = {"status": "cancelled", "ride_id": "ride-123", "idempotent": True}
        tool = router.registry.get("cancel_ride")
        with patch.object(router.idempotency, 'get_cached_result', new=AsyncMock(return_value=cached_data)), \
             patch.object(tool, 'authorize_ownership', new=AsyncMock(return_value=None)):
            res = await router.invoke(
                ctx=ctx,
                tool_name="cancel_ride",
                arguments={"ride_id": "ride-123", "reason": "user confirmation"},
                user_confirmed=True,
                idempotency_key="idempotency-key-dup-001",
            )
            assert res == cached_data
            assert res.get("idempotent") is True

    @pytest.mark.asyncio
    async def test_11_unauthorized_confirmation_action(self, mock_db, mock_redis):
        """11. Driver confirming a customer-only action is denied authorization."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        prev_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="Confirmation is required to cancel your ride...",
            intent="cancellation",
            metadata_json={"pending_intent": "cancellation", "requires_confirmation": True}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[prev_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[ChatMessage(role="assistant", content=prev_asst_msg.content)])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-11",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,  # Driver role is not permitted for cancel_ride
                text="Yes, cancel it.",
            )

            assert res.actions == []
            assert "not have authorization" in res.message or "permission nahi hai" in res.message

    @pytest.mark.asyncio
    async def test_12_expired_stale_pending_action(self, mock_db, mock_redis):
        """12. Expired/stale pending action: if an intervening turn occurred, pending action is ignored."""
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # History has an intervening assistant turn that was NOT asking for confirmation
        intervening_asst_msg = ChatMessageModel(
            session_id=session_id,
            role=MessageRole.ASSISTANT.value,
            content="The weather today is clear and pleasant.",
            intent="faq",
            metadata_json={"actions": [], "requires_confirmation": False}
        )

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[intervening_asst_msg])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-12",
                session_id=session_id,
                user_id=user_id,
                role=UserRole.DRIVER,
                text="Haan",
            )

            assert res.intent == Intent.UNKNOWN
            assert res.actions == []


class TestIntentToolMappingDispatch:
    """Verifies that intent detection dispatches the corresponding tool and returns real tool result."""

    @pytest.mark.asyncio
    async def test_1_where_is_my_active_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-ride-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="Where is my active ride?",
            )

            assert res.intent == Intent.RIDE_STATUS
            assert res.actions == ["get_active_ride"]
            assert "ride_123" in res.message or "active ride" in res.message.lower()

    @pytest.mark.asyncio
    async def test_2_what_is_my_eta(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-eta-1", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="What is my ETA?",
            )

            assert res.actions == ["get_driver_eta"]

    @pytest.mark.asyncio
    async def test_3_how_much_was_the_fare(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-fare-1", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="How much was the fare?",
            )

            assert res.actions == ["get_ride_fare_breakdown"]

    @pytest.mark.asyncio
    async def test_4_what_is_my_payment_status(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-pay-1", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="What is my payment status?",
            )

            assert res.actions == ["get_payment_status"]

    @pytest.mark.asyncio
    async def test_5_how_much_did_i_earn(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-earn-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="How much did I earn?",
            )

            assert res.actions == ["get_driver_earnings"]

    @pytest.mark.asyncio
    async def test_6_hindi_active_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-hi-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="मेरी एक्टिव राइड कहाँ है?",
            )

            assert res.language == Language.HINDI
            assert res.intent == Intent.RIDE_STATUS
            assert res.actions == ["get_active_ride"]

    @pytest.mark.asyncio
    async def test_7_hinglish_active_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-hien-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="Meri active ride kahan hai?",
            )

            assert res.language == Language.HINGLISH
            assert res.intent == Intent.RIDE_STATUS
            assert res.actions == ["get_active_ride"]

    @pytest.mark.asyncio
    async def test_8_gujarati_active_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-gu-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="મારી એક્ટિવ રાઇડ ક્યાં છે?",
            )

            assert res.language == Language.GUJARATI
            assert res.intent == Intent.RIDE_STATUS
            assert res.actions == ["get_active_ride"]

    @pytest.mark.asyncio
    async def test_9_bengali_active_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-bn-1", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="আমার সক্রিয় রাইড কোথায়?",
            )

            assert res.language == Language.BENGALI
            assert res.intent == Intent.RIDE_STATUS
            assert res.actions == ["get_active_ride"]


def orchestrator_registry():
    from app.tools.registry.registry import build_default_registry
    return build_default_registry()

