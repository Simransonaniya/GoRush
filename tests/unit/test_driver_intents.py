"""
Unit tests for all 12 Driver Chatbot Intents (Spec Section 6).

Verifies that intent classification, urgency, tool routing requirements,
and risk level assignments work accurately across English, Hinglish,
and regional language inputs for driver queries.
"""
import pytest
from app.ai.intent.detector import intent_detector
from app.common.enums.chat import Intent, Priority, RiskLevel


class TestDriverIntents:
    """Coverage for Section 6: Driver Chatbot Intents."""

    # 1. Ride offer/acceptance help
    @pytest.mark.parametrize("phrase, expected_intent", [
        ("I am not receiving any ride offers", Intent.RIDE_OFFER),
        ("Booking offer nahi aa raha hai", Intent.RIDE_OFFER),
        ("Cannot accept ride request", Intent.ACCEPTANCE),
        ("Duty accept nahi ho rahi", Intent.ACCEPTANCE),
    ])
    def test_ride_offer_and_acceptance(self, phrase: str, expected_intent: Intent):
        res = intent_detector.detect(phrase)
        assert res.intent == expected_intent
        assert res.requires_tool is True

    # 2. Customer not found
    @pytest.mark.parametrize("phrase", [
        "Customer is not at the pickup location",
        "Pickup spot par rider missing hai, call nahi utha raha",
        "Customer unreachable at pickup spot",
    ])
    def test_customer_not_found(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.CUSTOMER_NOT_FOUND
        assert res.requires_tool is True
        assert res.urgency == Priority.P1_CRITICAL

    # 3. Customer cancellation
    @pytest.mark.parametrize("phrase", [
        "Customer cancelled the ride halfway",
        "Rider ne trip cancel kar diya",
        "Customer cancelled after 5 minutes waiting",
    ])
    def test_customer_cancellation(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.CUSTOMER_CANCELLED
        assert res.requires_tool is True

    # 4. Navigation/app troubleshooting
    @pytest.mark.parametrize("phrase, expected_intent", [
        ("GPS navigation is taking me to wrong route", Intent.NAVIGATION),
        ("App freeze ho raha hai while taking ride", Intent.APP_TROUBLESHOOTING),
        ("GoRush driver app crash in location update", Intent.APP_TROUBLESHOOTING),
    ])
    def test_navigation_and_app_troubleshooting(self, phrase: str, expected_intent: Intent):
        res = intent_detector.detect(phrase)
        assert res.intent == expected_intent

    # 5. Daily/weekly/monthly earnings
    @pytest.mark.parametrize("phrase", [
        "Show my daily earnings for today",
        "Haftewari kamai kitni hui hai?",
        "What is my monthly earning report?",
    ])
    def test_earnings(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.EARNINGS
        assert res.requires_tool is True

    # 6. Payout status
    @pytest.mark.parametrize("phrase", [
        "My weekly payout status is pending",
        "Bank transfer payout delay ho gaya hai",
        "Payout kab aayega account mein?",
    ])
    def test_payout_status(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.PAYOUT
        assert res.requires_tool is True
        assert res.risk_level == RiskLevel.MEDIUM

    # 7. Incentive status
    @pytest.mark.parametrize("phrase", [
        "Check my peak hour bonus incentive status",
        "Target bonus kab milega?",
        "Trip bonus incentive status for this week",
    ])
    def test_incentive_status(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.INCENTIVE
        assert res.requires_tool is True

    # 8. Document expiry/status
    @pytest.mark.parametrize("phrase", [
        "My driving license is near expiry",
        "Kagaz expire document verification status",
        "RC expiry approval status",
    ])
    def test_document_status(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.DOCUMENT_STATUS
        assert res.requires_tool is True

    # 9. Vehicle/document support
    @pytest.mark.parametrize("phrase", [
        "I want to change vehicle in my driver profile",
        "Update RC for new vehicle",
        "Gadi badalna hai vehicle support help",
    ])
    def test_vehicle_document_support(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.VEHICLE_DOCUMENT
        assert res.requires_tool is True
        assert res.risk_level == RiskLevel.MEDIUM

    # 10. Payment/cash help
    @pytest.mark.parametrize("phrase", [
        "Customer didn't pay cash for the trip",
        "Cash ride payment dispute",
        "Rider ne cash nahi diya bill amount",
        "ग्राहक ने भुगतान नहीं किया।",
        "कैश भुगतान नहीं मिला",
    ])
    def test_cash_payment_help(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.CASH_PAYMENT
        assert res.requires_tool is True
        assert res.urgency == Priority.P1_CRITICAL

    # 11. Account/profile help
    @pytest.mark.parametrize("phrase", [
        "Help me update my driver profile details",
        "Change my registered phone number in driver account",
    ])
    def test_account_profile_help(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.ACCOUNT
        assert res.risk_level == RiskLevel.HIGH

    # 12. Safety/SOS and escalation
    @pytest.mark.parametrize("phrase", [
        "Emergency SOS accident on the road",
        "Customer is threatening me call police",
    ])
    def test_safety_sos_escalation(self, phrase: str):
        res = intent_detector.detect(phrase)
        assert res.intent == Intent.SAFETY
        assert res.urgency == Priority.P0_EMERGENCY
        assert res.risk_level == RiskLevel.CRITICAL


import uuid
from unittest.mock import AsyncMock, MagicMock
from app.ai.orchestrator.orchestrator import ChatOrchestrator
from app.common.enums.chat import UserRole, Language


@pytest.fixture
def mock_db_driver():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def mock_redis_driver():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=None)
    return redis


class TestDriverIntentsRegression:
    """End-to-end integration and orchestrator regression tests for driver problematic cases."""

    @pytest.mark.asyncio
    async def test_driver_orchestrator_routing(self, mock_db_driver, mock_redis_driver):
        orchestrator = ChatOrchestrator(mock_db_driver, mock_redis_driver)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.user_id = user_id
        mock_session.language = "hi-en"
        orchestrator.conversations.get_session = AsyncMock(return_value=mock_session)

        # 1. Payout
        res1 = await orchestrator.handle_message(
            request_id="req_payout",
            session_id=session_id,
            user_id=user_id,
            role=UserRole.DRIVER,
            text="Meri payment kab aayegi?"
        )
        assert res1.intent == Intent.PAYOUT
        assert "get_driver_earnings" in res1.actions
        assert "payout" in res1.message.lower() or "earnings" in res1.message.lower() or "कमाई" in res1.message

        # 2. Customer not found
        res2 = await orchestrator.handle_message(
            request_id="req_cnf",
            session_id=session_id,
            user_id=user_id,
            role=UserRole.DRIVER,
            text="Mera passenger mujhe nahi mil raha."
        )
        assert res2.intent == Intent.CUSTOMER_NOT_FOUND
        assert "get_active_ride" in res2.actions
        assert "ride_123" in res2.message or "active" in res2.message.lower() or "passenger" in res2.message.lower() or "कॉल" in res2.message

        # 3. Document status / verification
        res3 = await orchestrator.handle_message(
            request_id="req_verif",
            session_id=session_id,
            user_id=user_id,
            role=UserRole.DRIVER,
            text="Mera driver verification pending hai."
        )
        assert res3.intent == Intent.DOCUMENT_STATUS
        assert "get_document_status" in res3.actions
        assert "approved" in res3.message.lower() or "status" in res3.message.lower() or "दस्तावेज़" in res3.message

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_lang,expected_intent,expected_action,expected_handoff", [
        # Baseline working case
        ("Aaj meri total earning kitni hai?", Language.HINGLISH, Intent.EARNINGS, "get_driver_earnings", False),
        # Case 1
        ("The passenger damaged my vehicle.", Language.ENGLISH, Intent.SAFETY, "create_safety_incident", True),
        # Case 2
        ("When will my payment arrive?", Language.ENGLISH, Intent.PAYOUT, "get_driver_earnings", False),
        # Case 3
        ("Payment abhi tak nahi aayi hai.", Language.HINGLISH, Intent.PAYOUT, "get_driver_earnings", False),
        # Case 4
        ("Mera passenger mujhe nahi mil raha.", Language.HINGLISH, Intent.CUSTOMER_NOT_FOUND, "get_active_ride", False),
        # Case 5
        ("Mera driver verification pending hai.", Language.HINGLISH, Intent.DOCUMENT_STATUS, "get_document_status", False),
        # Case 6
        ("Passenger ne ride cancel kar di, mujhe cancellation fee milegi?", Language.HINGLISH, Intent.CUSTOMER_CANCELLED, "get_active_ride", False),
        # Case 7
        ("Mera incentive abhi tak nahi mila.", Language.HINGLISH, Intent.INCENTIVE, "get_driver_earnings", False),
        # Case 8
        ("Mujhe driver support agent se baat karni hai.", Language.HINGLISH, Intent.HUMAN_AGENT, "handoff_to_agent", True),
        # Case 9
        ("Passenger mujhe threaten kar raha hai.", Language.HINGLISH, Intent.SAFETY, "create_safety_incident", True),
        # Case 10
        ("I don't feel safe with this passenger.", Language.ENGLISH, Intent.SAFETY, "create_safety_incident", True),
    ])
    async def test_all_10_problematic_cases_and_baseline(
        self, mock_db_driver, mock_redis_driver, query, expected_lang, expected_intent, expected_action, expected_handoff
    ):
        orchestrator = ChatOrchestrator(mock_db_driver, mock_redis_driver)
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.user_id = user_id
        mock_session.language = expected_lang.value
        orchestrator.conversations.get_session = AsyncMock(return_value=mock_session)

        res = await orchestrator.handle_message(
            request_id=f"req_{expected_intent.value}",
            session_id=session_id,
            user_id=user_id,
            role=UserRole.DRIVER,
            text=query
        )

        assert res.language == expected_lang, f"Language mismatch for '{query}': expected {expected_lang}, got {res.language}"
        assert res.intent == expected_intent, f"Intent mismatch for '{query}': expected {expected_intent}, got {res.intent}"
        assert expected_action in res.actions, f"Action {expected_action} not found in actions {res.actions} for '{query}'"
        assert res.handoff.triggered == expected_handoff, f"Handoff mismatch for '{query}': expected {expected_handoff}, got {res.handoff.triggered}"
        assert res.intent != Intent.UNKNOWN, f"Intent fell back to UNKNOWN for '{query}'"


