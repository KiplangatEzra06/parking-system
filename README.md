# Parking Management System

A small Python and SQLite parking system with O(1) availability checks, a min-heap for the lowest free slot, and a plate-number index for active sessions.

## Steps

1. **Data structures and headers:** `parking/models.py` defines `VehicleType`, `ParkingSlot`, `Session`, and `Receipt`; `parking/pricing.py` isolates `calculate_fee`.
2. **Core logic:** `parking/system.py` owns the `heapq` free-slot heap, active-session dictionary, and entry/exit algorithms.
3. **SQLite persistence:** `parking/database.py` creates the slots, sessions, rates, and index tables and reloads active state on startup.
4. **CLI:** `main.py` supports `entry`, `exit`, `status`, and `quit`.
5. **Tests:** `tests/test_parking.py` covers a full lot, tiered pricing, double exit, and restart recovery.

## Run

```text
python -m unittest discover -s tests -v
python main.py --database parking.db --slots 10
```

Vehicle types are `Motorcycle`, `Car`, and `Truck`. Default rates are KSh 200 / KSh 100, KSh 500 / KSh 200, and KSh 1,000 / KSh 400 respectively (first hour / each started additional hour).
