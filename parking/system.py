"""ParkingSystem orchestration and in-memory indexes."""

import heapq
from datetime import datetime, timezone
from typing import Callable

from .database import ParkingDatabase
from .models import ParkingSlot, Receipt, Session, VehicleType
from .pricing import RATES, calculate_fee


class ParkingSystem:
    def __init__(self, database: ParkingDatabase, clock: Callable[[], datetime] | None = None):
        self.database = database
        self._now = clock or (lambda: datetime.now(timezone.utc))
        slots = database.load_slots()
        active_sessions = database.load_active_sessions()
        occupied_ids = {session.slot_id for session in active_sessions}
        self._active_sessions = {
            session.plate: session for session in active_sessions}
        self._rates = database.load_rates()
        self._free_slots = [
            slot.id for slot in slots if slot.id not in occupied_ids and not slot.occupied]
        heapq.heapify(self._free_slots)
        self.available_slots = len(self._free_slots)

    @classmethod
    def create(cls, path: str, slot_count: int = 10, floors: int = 1) -> "ParkingSystem":
        database = ParkingDatabase(path)
        slots = [ParkingSlot(index, (index - 1) // max(1, slot_count // floors) + 1)
                 for index in range(1, slot_count + 1)]
        database.seed(slots, RATES)
        return cls(database)

    def entry(self, plate: str, vehicle_type: VehicleType) -> Session:
        plate = plate.strip().upper()
        if not plate:
            raise ValueError("Plate number cannot be empty")
        if plate in self._active_sessions:
            raise ValueError(f"Vehicle {plate} is already parked")
        if self.available_slots == 0:
            raise RuntimeError("Parking lot is full")
        session = Session(plate, heapq.heappop(
            self._free_slots), vehicle_type, self._now())
        self.database.save_entry(session)
        self._active_sessions[plate] = session
        self.available_slots -= 1
        return session

    def exit(self, plate: str) -> Receipt:
        plate = plate.strip().upper()
        session = self._active_sessions.get(plate)
        if session is None:
            raise KeyError(f"No active session found for {plate}")
        exit_time = self._now()
        duration = exit_time - session.entry_time
        amount = calculate_fee(duration, session.vehicle_type, self._rates)
        self.database.save_exit(session, exit_time, amount)
        heapq.heappush(self._free_slots, session.slot_id)
        del self._active_sessions[plate]
        self.available_slots += 1
        return Receipt(plate, session.slot_id, session.vehicle_type, session.entry_time,
                       exit_time, max(0, int(duration.total_seconds())), amount)

    def status(self) -> list[ParkingSlot]:
        occupied = {
            session.slot_id: session.vehicle_type for session in self._active_sessions.values()}
        return [ParkingSlot(slot.id, slot.floor, occupied.get(slot.id), slot.id in occupied)
                for slot in self.database.load_slots()]
