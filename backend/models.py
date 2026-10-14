"""Domain models for the mock travel system.

FlightOffer / HotelOffer = searchable offers
Booking                  = a real persisted reservation with structured details

PendingAction / Conversation are deferred to later phases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


BookingType = Literal["flight", "hotel"]
BookingStatus = Literal["confirmed", "cancelled"]


@dataclass(frozen=True)
class FlightOffer:
    id: str
    origin: str
    destination: str
    departure_date: str  # YYYY-MM-DD
    departure_time: str  # HH:MM
    arrival_time: str  # HH:MM
    duration_minutes: int
    airline: str
    flight_number: str
    price: float
    seats_available: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HotelOffer:
    """A hotel option for a specific stay request (dates + rooms)."""

    id: str
    name: str
    city: str
    stars: int
    check_in: str  # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    nights: int
    rooms: int  # rooms requested for this offer
    price_per_night: float
    total_price: float  # price_per_night * nights * rooms
    rooms_available: int  # remaining inventory in catalog

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Booking:
    id: str
    booking_type: BookingType
    item_id: str
    user_name: str
    status: BookingStatus
    total_price: float
    created_at: str
    # Structured snapshot of what was booked (flight or hotel fields).
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
