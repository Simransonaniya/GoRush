from enum import Enum
from typing import Any


class UserRole(str, Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    SUPPORT_AGENT = "support_agent"
    SAFETY_AGENT = "safety_agent"
    ADMIN = "admin"


class Language(str, Enum):
    # Full launch support
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hi-en"
    MIXED = "mixed"

    # Regional languages
    MARATHI = "mr"
    GUJARATI = "gu"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    ODIA = "or"
    ASSAMESE = "as"
    URDU = "ur"
    RAJASTHANI = "raj"

    UNKNOWN = "unknown"

    @classmethod
    def normalize(cls, val: Any) -> "Language":
        if isinstance(val, cls):
            return val
        if not val:
            return cls.UNKNOWN
        if hasattr(val, "value"):
            val = val.value
        val_str = str(val).lower().strip()
        if val_str in ("hinglish", "hi-en", "hi_en"):
            return cls.HINGLISH
        if val_str in ("rajasthani", "raj"):
            return cls.RAJASTHANI
        try:
            return cls(val_str)
        except ValueError:
            return cls.UNKNOWN


class Priority(str, Enum):
    P0_EMERGENCY = "P0"
    P1_CRITICAL = "P1"
    P2_STANDARD = "P2"
    P3_FAQ = "P3"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    HANDED_OFF = "handed_off"
    CLOSED = "closed"


class ToolExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"


class Intent(str, Enum):
    # Customer
    RIDE_STATUS = "ride_status"
    DRIVER_LATE = "driver_late"
    DRIVER_NOT_MOVING = "driver_not_moving"
    DRIVER_CANCELLED = "driver_cancelled"
    NO_DRIVER = "no_driver"
    FARE = "fare"
    CANCELLATION = "cancellation"
    PAYMENT_FAILED = "payment_failed"
    REFUND = "refund"
    LOST_ITEM = "lost_item"
    PROMO = "promo"
    REFERRAL = "referral"
    WALLET = "wallet"
    RATING = "rating"
    ACCOUNT = "account"
    PRIVACY = "privacy"
    SAFETY = "safety"
    FAQ = "faq"
    HUMAN_AGENT = "human_agent"
    # Driver
    RIDE_OFFER = "ride_offer"
    ACCEPTANCE = "acceptance"
    CUSTOMER_NOT_FOUND = "customer_not_found"
    CUSTOMER_CANCELLED = "customer_cancelled"
    NAVIGATION = "navigation"
    APP_TROUBLESHOOTING = "app_troubleshooting"
    EARNINGS = "earnings"
    PAYOUT = "payout"
    INCENTIVE = "incentive"
    DOCUMENT_STATUS = "document_status"
    VEHICLE_DOCUMENT = "vehicle_document"
    CASH_PAYMENT = "cash_payment"
    # Fallback
    UNKNOWN = "unknown"
