"""Core data structures for the parking system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class VehicleType(str, Enum):
    MOTORCYCLE = "Motorcycle"
    CAR = "Car"
    TRUCK = "Truck"

    @classmethod
    def parse(cls, value: str) -> "VehicleType":
        normalized = value.strip().lower()
        for vehicle_type in cls:
            if vehicle_type.value.lower() == normalized:
                return vehicle_type
        valid = ", ".join(item.value for item in cls)
        raise ValueError(f"Unknown vehicle type '{value}'. Expected: {valid}")


@dataclass(frozen=True)
class ParkingSlot:
    id: int
    floor: int
    vehicle_type: VehicleType | None = None
    occupied: bool = False


@dataclass(frozen=True)
class Session:
    plate: str
    slot_id: int
    vehicle_type: VehicleType
    entry_time: datetime


@dataclass(frozen=True)
class Receipt:
    plate: str
    slot_id: int
    vehicle_type: VehicleType
    entry_time: datetime
    exit_time: datetime
    duration_seconds: int
    amount_paid: float