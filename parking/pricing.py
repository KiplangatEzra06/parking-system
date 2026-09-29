"""Fee calculation for the parking system."""

from __future__ import annotations

from datetime import timedelta


HOURLY_RATE = 50.0


def calculate_fee(duration: timedelta | float) -> float:
    """Return the parking fee using the fixed KSh 50 per hour rate."""
    if isinstance(duration, timedelta):
        seconds = duration.total_seconds()
    else:
        seconds = float(duration)
    if seconds < 0:
        raise ValueError("Parking duration cannot be negative")
    return round((seconds / 3600.0) * HOURLY_RATE, 2)
