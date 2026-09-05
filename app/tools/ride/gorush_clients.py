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
    async def request_refund(self, ride_id: str, reason: str) -> dict[str, Any]: ...


class GoRushSupportClient(ABC):
    @abstractmethod
    async def create_ticket(self, user_id: str, category: str, description: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_ticket_status(self, ticket_id: str) -> dict[str, Any]: ...


class GoRushSafetyClient(ABC):
    @abstractmethod
    async def create_incident(self, user_id: str, ride_id: str | None, details: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# MOCK ADAPTERS -- clearly marked. Replace with real HTTP clients calling
# GORUSH_*_API_BASE_URL once those internal APIs are available.
# ---------------------------------------------------------------------------

class MockGoRushRideClient(GoRushRideClient):
    _rides = {
        "ride_123": {
            "ride_id": "ride_123",
            "status": "driver_assigned",
            "driver_id": "drv_9",
            "eta_minutes": 6,
            "fare_estimate": 148.0,
        }
    }

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
        self._rides[ride_id]["status"] = "cancelled"
        return {"ride_id": ride_id, "status": "cancelled", "cancellation_fee": 0.0}

    async def start_rematch(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "rematch_status": "searching", "eligible": True}


class MockGoRushPaymentClient(GoRushPaymentClient):
    async def get_payment_status(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "status": "captured", "amount": 148.0}

    async def get_refund_status(self, ride_id: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "status": "not_requested"}

    async def request_refund(self, ride_id: str, reason: str) -> dict[str, Any]:
        return {"ride_id": ride_id, "status": "refund_initiated", "reason": reason}


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
