"""Pure fee calculation functions."""

import math
from datetime import timedelta

from .models import VehicleType


RATES: dict[VehicleType, tuple[float, float]] = {
    VehicleType.MOTORCYCLE: (200.0, 100.0),
    VehicleType.CAR: (500.0, 200.0),
    VehicleType.TRUCK: (1000.0, 400.0),
}


def calculate_fee(
    duration: timedelta,
    vehicle_type: VehicleType,
    rates: dict[VehicleType, tuple[float, float]] | None = None,
) -> float:
    """Charge a flat first hour, then a rate for each started extra hour."""
    if duration.total_seconds() < 0:
        raise ValueError("Parking duration cannot be negative")
    first_hour_rate, hourly_rate = (rates or RATES)[vehicle_type]
    extra_hours = max(0, math.ceil((duration.total_seconds() - 3600) / 3600))
    return round(first_hour_rate + extra_hours * hourly_rate, 2)
