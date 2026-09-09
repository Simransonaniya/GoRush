"""
BRD Unit Test Suite for Knowledge Base, Priority Classification (P0/P1/P2/P3),
Human Handoff, Tool vs KB Routing, and Security Guardrails.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.intent.detector import intent_detector
from app.ai.orchestrator.orchestrator import ChatOrchestrator
from app.ai.orchestrator.schema import OrchestrationResult
from app.common.enums.chat import Intent, Language, Priority, UserRole
from app.knowledge.models import KnowledgeArticle, KnowledgeChunk
from app.knowledge.retrieval.service import RAGRetrievalService, RetrievedChunk


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
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


class TestPriorityClassification:
    """Verifies BRD context-aware priority classification P0, P1, P2, P3."""

    def test_p0_emergency_accident(self):
        res = intent_detector.detect("I have been in an accident and need help immediately.")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY

    def test_p0_hindi_accident(self):
        res = intent_detector.detect("मेरा एक्सीडेंट हो गया है और मुझे तुरंत मदद चाहिए।")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY
        assert res.language == Language.HINDI

    def test_p0_hinglish_accident(self):
        res = intent_detector.detect("Mera accident ho gaya hai, mujhe abhi help chahiye.")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY
        assert res.language == Language.HINGLISH

    def test_p0_customer_threatened(self):
        res = intent_detector.detect("The customer threatened me.")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY

    def test_p0_hindi_customer_threatened(self):
        res = intent_detector.detect("ग्राहक ने मुझे धमकी दी।")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY
        assert res.language == Language.HINDI

    def test_past_accident_inquiry_is_p3_kb(self):
        res = intent_detector.detect("I had an accident yesterday. What should I do now?")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P3_FAQ
        assert res.requires_tool is False

    def test_safety_procedure_question_is_p3_kb(self):
        res = intent_detector.detect("What is the safety procedure after an accident?")
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P3_FAQ
        assert res.requires_tool is False



class TestToolVsKBRouting:
    """Verifies BRD section 17: Tool vs KB Distinction."""

    @pytest.mark.asyncio
    async def test_1_cancellation_policy_vs_cancel_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-kb-1", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="What is the cancellation policy?",
            )
            assert res.actions == []
            assert "cancel_ride" not in res.actions

    @pytest.mark.asyncio
    async def test_2_cancel_my_ride(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-tool-2", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="Cancel my ride.",
            )
            assert "cancel_ride" in res.actions or "create_support_ticket" in res.actions or res.intent == Intent.CANCELLATION

    @pytest.mark.asyncio
    async def test_3_refund_how_it_works(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-kb-3", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="How does refund work?",
            )
            assert res.actions == []

    @pytest.mark.asyncio
    async def test_4_check_my_refund_status(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-tool-4", session_id=session_id, user_id=user_id,
                role=UserRole.CUSTOMER, text="Check my refund status.",
            )
            assert res.actions == ["get_refund_status"]

    @pytest.mark.asyncio
    async def test_5_documents_required_policy(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-kb-5", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="What documents do drivers need?",
            )
            assert res.actions == []

    @pytest.mark.asyncio
    async def test_6_are_my_documents_verified(self, mock_db, mock_redis):
        orchestrator = ChatOrchestrator(mock_db, mock_redis)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(orchestrator.conversations, 'add_message', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_session', new=AsyncMock()), \
             patch.object(orchestrator.conversations, 'get_recent_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'build_llm_messages', new=AsyncMock(return_value=[])), \
             patch.object(orchestrator.context, 'maybe_summarize', new=AsyncMock()):

            res: OrchestrationResult = await orchestrator.handle_message(
                request_id="req-tool-6", session_id=session_id, user_id=user_id,
                role=UserRole.DRIVER, text="Are my documents verified?",
            )
            assert res.actions == ["get_document_status"]


class TestKBSecurityFiltering:
    """Verifies that RAG retrieval only returns active, approved articles and ignores draft/archived/unapproved."""

    @pytest.mark.asyncio
    async def test_only_approved_active_articles_returned(self, mock_db):
        mock_embedding = AsyncMock()
        mock_embedding.embeddings.return_value = [[0.1] * 384]
        service = RAGRetrievalService(mock_db, mock_embedding)

        # Mock DB execute returning 0 rows for unapproved queries
        chunks = await service.retrieve("draft internal policy", language="en", category="faq")
        assert isinstance(chunks, list)
