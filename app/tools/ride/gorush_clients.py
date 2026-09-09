"""
Interfaces for GoRush upstream services. Concrete real implementations
should be added under a `live/` adapter once GoRush's internal APIs are
reachable; until then `MockGoRushRideClient` etc. below are wired in via
GORUSH_USE_MOCKS=true. Clearly marked as mocks -- do not treat their data
as production data.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.common.exceptions.base import RideNotFoundError


class GoRushRideClient(ABC):
    @abstractmethod
    async def get_active_ride(self, user_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def get_driver_eta(self, ride_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_fare_breakdown(self, ride_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def cancel_ride(self, ride_id: str, reason: str) -> dict[str, Any]: ...

    @abstractmethod
    async def start_rematch(self, ride_id: str) -> dict[str, Any]: ...


class GoRushPaymentClient(ABC):
    @abstractmethod
    async def get_payment_status(self, ride_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_refund_status(self, ride_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def request_refund(self, ride_id: str, reason: str, amount: float | None = None) -> dict[str, Any]: ...


class GoRushSupportClient(ABC):
    @abstractmethod
    async def create_ticket(self, user_id: str, category: str, description: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_ticket_status(self, ticket_id: str) -> dict[str, Any]: ...


class GoRushSafetyClient(ABC):
    @abstractmethod
    async def create_incident(self, user_id: str, ride_id: str | None, details: str) -> dict[str, Any]: ...


class GoRushDriverClient(ABC):
    """Read-only client for driver-specific data (earnings, documents)."""

    @abstractmethod
    async def get_earnings(self, user_id: str, period: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_document_status(self, user_id: str) -> dict[str, Any]: ...


class GoRushHandoffClient(ABC):
    """Triggers a live-agent handoff in the GoRush support platform."""

    @abstractmethod
    async def trigger_handoff(
        self,
        user_id: str,
        session_id: str,
        reason: str,
        priority: str,
        intent: str,
        language: str,
        context_summary: str,
    ) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# MOCK ADAPTERS -- clearly marked. Replace with real HTTP clients calling
# GORUSH_*_API_BASE_URL once those internal APIs are available.
# ---------------------------------------------------------------------------

class MockGoRushRideClient(GoRushRideClient):
    _DEFAULT_RIDES = {
        "ride_123": {
            "ride_id": "ride_123",
            "status": "driver_assigned",
            "driver_id": "drv_9",
            "eta_minutes": 6,
            "fare_estimate": 148.0,
        }
    }

    def __init__(self):
        import copy
        self._rides = copy.deepcopy(self._DEFAULT_RIDES)

    async def get_active_ride(self, user_id: str) -> dict[str, Any] | None:
        return self._rides.get("ride_123")

    async def get_driver_eta(self, ride_id: str) -> dict[str, Any]:
        ride = self._rides.get(ride_id)
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")
        return {"ride_id": ride_id, "eta_minutes": ride["eta_minutes"]}

    async def get_fare_breakdown(self, ride_id: str) -> dict[str, Any]:
        ride = self._rides.get(ride_id)
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")
        return {
            "ride_id": ride_id,
            "base_fare": 60.0,
            "distance_fare": 70.0,
            "surge_multiplier": 1.0,
            "total": ride["fare_estimate"],
        }

    async def cancel_ride(self, ride_id: str, reason: str) -> dict[str, Any]:
        if ride_id not in self._rides:
            raise RideNotFoundError(f"Ride {ride_id} not found")
        # NOTE: Mock intentionally does not persist status change in _rides.
        # Real service enforces state machine; here we just return deterministic result.
        return {"ride_id": ride_id, "status": "cancelled", "cancellation_fee": 0.0}

    async def start_rematch(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "rematch_status": "searching", "eligible": True}


class MockGoRushPaymentClient(GoRushPaymentClient):
    async def get_payment_status(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "status": "captured", "amount": 148.0}

    async def get_refund_status(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "status": "not_requested"}

    async def request_refund(self, ride_id: str, reason: str, amount: float | None = None) -> dict[str, Any]:
        return {
            "ride_id": ride_id,
            "status": "refund_initiated",
            "reason": reason,
            "amount": amount,
        }


class MockGoRushSupportClient(GoRushSupportClient):
    _counter = 1000

    async def create_ticket(self, user_id: str, category: str, description: str) -> dict[str, Any]:
        MockGoRushSupportClient._counter += 1
        return {"ticket_id": f"tkt_{self._counter}", "status": "open", "category": category}

    async def get_ticket_status(self, ticket_id: str) -> dict[str, Any]:
        return {"ticket_id": ticket_id, "status": "in_progress"}


class MockGoRushSafetyClient(GoRushSafetyClient):
    _counter = 5000

    async def create_incident(self, user_id: str, ride_id: str | None, details: str) -> dict[str, Any]:
        MockGoRushSafetyClient._counter += 1
        return {"incident_id": f"inc_{self._counter}", "status": "escalated_to_safety_team"}


class MockGoRushDriverClient(GoRushDriverClient):
    """Mock driver data client. Not production data."""

    async def get_earnings(self, user_id: str, period: str) -> dict[str, Any]:
        period_data = {
            "today": {"period": "today", "trips": 8, "gross_earnings": 742.50, "net_earnings": 668.25, "currency": "INR"},
            "week": {"period": "week", "trips": 42, "gross_earnings": 4180.00, "net_earnings": 3762.00, "currency": "INR"},
            "month": {"period": "month", "trips": 168, "gross_earnings": 16720.00, "net_earnings": 15048.00, "currency": "INR"},
        }
        return period_data.get(period, period_data["today"])

    async def get_document_status(self, user_id: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "documents": [
                {"type": "driving_license", "status": "approved", "expiry": "2027-06-30"},
                {"type": "vehicle_rc", "status": "approved", "expiry": "2028-01-15"},
                {"type": "insurance", "status": "approved", "expiry": "2027-03-31"},
                {"type": "puc", "status": "approved", "expiry": "2026-12-31"},
                {"type": "profile_photo", "status": "approved"},
                {"type": "aadhaar", "status": "approved"},
                {"type": "pan", "status": "approved"},
            ],
            "overall_status": "all_approved",
            "can_drive": True,
        }


class MockGoRushHandoffClient(GoRushHandoffClient):
    """Mock handoff client. Not production data."""
    _counter = 9000

    async def trigger_handoff(
        self,
        user_id: str,
        session_id: str,
        reason: str,
        priority: str,
        intent: str,
        language: str,
        context_summary: str,
    ) -> dict[str, Any]:
        MockGoRushHandoffClient._counter += 1
        return {
            "triggered": True,
            "handoff_id": f"handoff_{self._counter}",
            "status": "agent_assigned",
            "priority": priority,
            "estimated_wait_seconds": 120,
        }
