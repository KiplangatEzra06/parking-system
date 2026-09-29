"""ParkingSystem orchestration and validation logic."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable

from .database import ParkingDatabase, _from_db
from .pricing import calculate_fee


class ParkingSystem:
    def __init__(self, database: ParkingDatabase, clock: Callable[[], datetime] | None = None):
        self.database = database
        self._now = clock or (lambda: datetime.now(timezone.utc))
        self.available_slots = self._count_available()

    @classmethod
    def create(cls, path: str, slot_count: int = 10) -> "ParkingSystem":
        database = ParkingDatabase(path)
        database.seed(slot_count)
        return cls(database)

    def _count_available(self) -> int:
        return self.database.connection.execute(
            "SELECT COUNT(*) FROM ParkingSlots WHERE Status = 'Available'"
        ).fetchone()[0]

    def entry(self, registration_number: str) -> dict:
        registration_number = registration_number.strip().upper()
        if not registration_number or not re.fullmatch(r"[A-Z]{3} \d{3} [A-Z]", registration_number):
            raise ValueError(
                "Registration number is invalid. Use ABC 123 A format.")
        if self.database.get_active_record(registration_number) is not None:
            raise ValueError("Vehicle already has an active parking record.")

        slot_id = self.database.get_available_slot()
        if slot_id is None:
            raise RuntimeError("No parking spaces available.")

        entry_time = self._now()
        self.database.set_slot_status(slot_id, "Occupied")
        self.database.add_entry(registration_number, slot_id, entry_time)
        self.available_slots = self._count_available()
        return {
            "registration_number": registration_number,
            "slot_id": slot_id,
            "entry_time": entry_time.isoformat(),
        }

    def exit(self, registration_number: str) -> dict:
        registration_number = registration_number.strip().upper()
        record = self.database.get_active_record(registration_number)
        if record is None:
            raise ValueError("No active parking record for this vehicle.")

        exit_time = self._now()
        entry_time = _from_db(record["EntryTime"])
        duration = exit_time - entry_time
        amount_paid = calculate_fee(duration)

        self.database.save_exit(record["RecordID"], exit_time, amount_paid)
        self.database.set_slot_status(record["SlotNo"], "Available")
        self.available_slots = self._count_available()

        return {
            "plate": registration_number,
            "slot_id": record["SlotNo"],
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "duration_seconds": int(max(0, duration.total_seconds())),
            "amount_paid": round(amount_paid, 2),
        }

    def status(self) -> list[dict]:
        return [
            {"slot_id": slot.id, "status": slot.status}
            for slot in self.database.get_all_slots()
        ]

    def active_records(self) -> list[dict]:
        rows = self.database.get_all_active_records()
        return [
            {
                "record_id": row["RecordID"],
                "registration_number": row["RegistrationNumber"],
                "slot_no": row["SlotNo"],
                "entry_time": _from_db(row["EntryTime"]).isoformat(),
            }
            for row in rows
        ]

    def completed_records(self) -> list[dict]:
        records = []
        for row in self.database.connection.execute(
            "SELECT * FROM ParkingRecords WHERE ExitTime IS NOT NULL ORDER BY RecordID DESC"
        ).fetchall():
            records.append(
                {
                    "record_id": row["RecordID"],
                    "registration_number": row["RegistrationNumber"],
                    "slot_no": row["SlotNo"],
                    "entry_time": _from_db(row["EntryTime"]).isoformat(),
                    "exit_time": _from_db(row["ExitTime"]).isoformat(),
                    "amount_paid": float(row["AmountPaid"]),
                }
            )
        return records
