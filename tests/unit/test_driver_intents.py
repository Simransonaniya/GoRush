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
