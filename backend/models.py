"""Domain models for the mock travel system.

These are plain data containers (dataclasses). Persistence lives in database.py;
business rules live in services.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


BookingType = Literal["flight", "hotel"]
BookingStatus = Literal["confirmed", "cancelled"]


@dataclass(frozen=True)
class Flight:
    id: str
    origin: str
    destination: str
    departure_date: str  # YYYY-MM-DD
    airline: str
    price: float
    seats_available: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Hotel:
    id: str
    city: str
    name: str
    stars: int
    price_per_night: float
    rooms_available: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Booking:
    id: str
    booking_type: BookingType
    item_id: str
    item_label: str
    user_name: str
    status: BookingStatus
    total_price: float
    nights: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
