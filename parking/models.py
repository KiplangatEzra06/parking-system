"""Core data structures for the parking system."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParkingSlot:
    id: int
    status: str = "Available"


@dataclass(frozen=True)
class ParkingRecord:
    record_id: int | None
    registration_number: str
    slot_no: int
    entry_time: datetime
    exit_time: datetime | None = None
    amount_paid: float | None = None


@dataclass(frozen=True)
class Receipt:
    plate: str
    slot_id: int
    entry_time: datetime
    exit_time: datetime
    duration_seconds: int
    amount_paid: float
