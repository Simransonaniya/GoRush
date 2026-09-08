"""
Tests for intent detector changes made in this session.

Covers:
  - Tamil (and other regional-language) refund keyword detection
  - DRIVER_NOT_MOVING keyword pattern (previously unreachable)
  - Broadened CANCELLATION pattern
  - WALLET aliases (balance, top-up, add money, transaction history)
  - REFERRAL keyword pattern (previously dead-code)
  - ACCOUNT keyword pattern (previously dead-code)
  - _requires_tool: LOST_ITEM and WALLET now return True
  - _risk_level: ACCOUNT -> HIGH, WALLET/LOST_ITEM -> MEDIUM
  - Language-lock reminder string rendered correctly by orchestrator prompt
"""

import pytest

from app.ai.intent.detector import intent_detector
from app.ai.prompts.registry import get_prompt
from app.common.enums.chat import Intent, Language, RiskLevel, Priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect(text: str):
    return intent_detector.detect(text)


# ---------------------------------------------------------------------------
# 1. Refund — Tamil (the exact message from the bug report)
# ---------------------------------------------------------------------------

class TestRefundRegionalLanguages:
    def test_tamil_refund_exact_bug_message(self):
        """Original failing message: 'I haven't received my money back' in Tamil."""
        result = detect("என் பணத்தைத் திரும்பப் பெறவில்லை")
        assert result.intent == Intent.REFUND
        assert result.language == Language.TAMIL

    def test_tamil_refund_shorter_phrase(self):
        result = detect("பணம் திரும்ப வேண்டும்")
        assert result.intent == Intent.REFUND

    def test_telugu_refund(self):
        result = detect("నా డబ్బు తిరిగి ఇవ్వండి")
        assert result.intent == Intent.REFUND

    def test_kannada_refund(self):
        result = detect("ಹಣ ಮರಳಿ ಕೊಡಿ")
        assert result.intent == Intent.REFUND

    def test_malayalam_refund(self):
        result = detect("റീഫണ്ട് ആകണം")
        assert result.intent == Intent.REFUND

    def test_marathi_refund(self):
        result = detect("पैसे परत द्या")
        assert result.intent == Intent.REFUND

    def test_gujarati_refund(self):
        result = detect("પૈસા પાછા જોઈએ")
        assert result.intent == Intent.REFUND

    def test_bengali_refund(self):
        result = detect("টাকা ফেরত দিন")
        assert result.intent == Intent.REFUND

    def test_punjabi_refund(self):
        result = detect("ਪੈਸੇ ਵਾਪਸ ਕਰੋ")
        assert result.intent == Intent.REFUND

    def test_english_refund_still_works(self):
        result = detect("I want a refund for my last ride")
        assert result.intent == Intent.REFUND

    def test_hindi_refund_still_works(self):
        result = detect("paisa wapas karo")
        assert result.intent == Intent.REFUND


# ---------------------------------------------------------------------------
# 2. DRIVER_NOT_MOVING — was previously unreachable
# ---------------------------------------------------------------------------

class TestDriverNotMoving:
    def test_english_not_moving(self):
        result = detect("My driver is not moving at all")
        assert result.intent == Intent.DRIVER_NOT_MOVING

    def test_english_stuck(self):
        result = detect("The driver is stuck and hasn't moved for 10 minutes")
        assert result.intent == Intent.DRIVER_NOT_MOVING

    def test_hindi_ruk_gaya(self):
        result = detect("driver ruk gaya hai, move nahi kar raha")
        assert result.intent == Intent.DRIVER_NOT_MOVING

    def test_hindi_khada_hai(self):
        result = detect("driver kaafi der se khada hai")
        assert result.intent == Intent.DRIVER_NOT_MOVING

    def test_requires_tool(self):
        """DRIVER_NOT_MOVING should trigger a tool call (live GPS check)."""
        result = detect("driver is not moving")
        assert result.requires_tool is True


# ---------------------------------------------------------------------------
# 3. CANCELLATION — broadened pattern
# ---------------------------------------------------------------------------

class TestCancellation:
    def test_original_pattern_still_works(self):
        result = detect("I want to cancel my ride")
        assert result.intent == Intent.CANCELLATION

    def test_cancel_karna_still_works(self):
        result = detect("ride cancel karna hai")
        assert result.intent == Intent.CANCELLATION

    def test_trip_cancel(self):
        result = detect("Please trip cancel kar do")
        assert result.intent == Intent.CANCELLATION

    def test_cancel_without_my(self):
        result = detect("can you cancel ride for me?")
        assert result.intent == Intent.CANCELLATION

    def test_ride_cancel_phrase(self):
        result = detect("ride cancel kar do abhi")
        assert result.intent == Intent.CANCELLATION


# ---------------------------------------------------------------------------
# 4. WALLET aliases
# ---------------------------------------------------------------------------

class TestWallet:
    def test_wallet_keyword_still_works(self):
        result = detect("How do I use my wallet?")
        assert result.intent == Intent.WALLET

    def test_balance_check(self):
        result = detect("What is my current balance?")
        assert result.intent == Intent.WALLET

    def test_add_money(self):
        result = detect("add money to my account")
        assert result.intent == Intent.WALLET

    def test_top_up(self):
        result = detect("how to top up my wallet?")
        assert result.intent == Intent.WALLET

    def test_transaction_history(self):
        result = detect("show my transaction history")
        assert result.intent == Intent.WALLET

    def test_requires_tool(self):
        """WALLET now requires a tool per spec: 'Balance and transaction help'."""
        result = detect("show my wallet balance")
        assert result.requires_tool is True

    def test_risk_level_medium(self):
        result = detect("show my wallet balance")
        assert result.risk_level == RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# 5. REFERRAL — was dead-code (no keyword pattern)
# ---------------------------------------------------------------------------

class TestReferral:
    def test_referral_keyword(self):
        result = detect("How does the referral program work?")
        assert result.intent == Intent.REFERRAL

    def test_refer_a_friend(self):
        result = detect("I want to refer my friend and earn cashback")
        assert result.intent == Intent.REFERRAL

    def test_share_code(self):
        result = detect("How do I share my referral code?")
        assert result.intent == Intent.REFERRAL

    def test_invite_friend(self):
        result = detect("invite friend and get discount")
        assert result.intent == Intent.REFERRAL


# ---------------------------------------------------------------------------
# 6. ACCOUNT — was dead-code (no keyword pattern)
# ---------------------------------------------------------------------------

class TestAccount:
    def test_account_keyword(self):
        result = detect("I can't access my account")
        assert result.intent == Intent.ACCOUNT

    def test_profile(self):
        result = detect("how do I update my profile?")
        assert result.intent == Intent.ACCOUNT

    def test_login(self):
        result = detect("I'm having trouble with login")
        assert result.intent == Intent.ACCOUNT

    def test_password(self):
        result = detect("I forgot my password")
        assert result.intent == Intent.ACCOUNT

    def test_delete_account(self):
        result = detect("I want to delete my account and all data")
        assert result.intent == Intent.ACCOUNT

    def test_change_email(self):
        result = detect("how do I change my email?")
        assert result.intent == Intent.ACCOUNT

    def test_privacy(self):
        result = detect("I have a privacy concern about my data")
        assert result.intent == Intent.ACCOUNT

    def test_risk_level_is_high(self):
        """Account changes (especially delete) are high-risk operations."""
        result = detect("delete my account")
        assert result.risk_level == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# 7. Tool / risk routing corrections
# ---------------------------------------------------------------------------

class TestToolAndRiskRouting:
    def test_lost_item_requires_tool(self):
        """Spec: 'Create lost-item workflow' — must route to a tool."""
        result = detect("I left my phone in the car")
        assert result.intent == Intent.LOST_ITEM
        assert result.requires_tool is True

    def test_lost_item_risk_medium(self):
        result = detect("I left my bag in the cab")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_refund_requires_tool(self):
        result = detect("I need a refund")
        assert result.requires_tool is True

    def test_refund_risk_high(self):
        result = detect("I need a refund")
        assert result.risk_level == RiskLevel.HIGH

    def test_cancellation_risk_high(self):
        result = detect("cancel my ride")
        assert result.risk_level == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# 8. Orchestrator language-lock prompt rendering
# ---------------------------------------------------------------------------

class TestOrchestratorLanguageLock:
    """Validates that get_prompt().render() produces the correct language name
    that the orchestrator embeds in its language-lock reminder message."""

    @pytest.mark.parametrize("lang_code,expected_name", [
        ("ta", "Tamil"),
        ("hi", "Hindi"),
        ("mr", "Marathi"),
        ("te", "Telugu"),
        ("kn", "Kannada"),
        ("ml", "Malayalam"),
        ("gu", "Gujarati"),
        ("bn", "Bengali"),
        ("pa", "Punjabi"),
        ("en", "English"),
    ])
    def test_render_injects_correct_language(self, lang_code, expected_name):
        prompt = get_prompt("customer_support_system")
        rendered = prompt.render(lang_code)
        assert f"communicating in {expected_name}" in rendered
        assert f"reply ONLY in {expected_name}" in rendered

    def test_tamil_does_not_contain_marathi(self):
        """Core regression: Tamil prompt must NOT mention Marathi."""
        prompt = get_prompt("customer_support_system")
        rendered = prompt.render("ta")
        assert "Marathi" not in rendered
        assert "Tamil" in rendered
