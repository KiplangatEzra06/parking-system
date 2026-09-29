"""SQLite persistence for the parking system."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import ParkingSlot


def _to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _from_db(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


class ParkingDatabase:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ParkingSlots (
                SlotID INTEGER PRIMARY KEY,
                Status TEXT NOT NULL CHECK(Status IN ('Available', 'Occupied')) DEFAULT 'Available'
            );

            CREATE TABLE IF NOT EXISTS ParkingRecords (
                RecordID INTEGER PRIMARY KEY AUTOINCREMENT,
                RegistrationNumber TEXT NOT NULL,
                SlotNo INTEGER NOT NULL,
                EntryTime TEXT NOT NULL,
                ExitTime TEXT,
                AmountPaid REAL,
                FOREIGN KEY (SlotNo) REFERENCES ParkingSlots(SlotID)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_active_registration
                ON ParkingRecords(RegistrationNumber)
                WHERE ExitTime IS NULL;

            CREATE UNIQUE INDEX IF NOT EXISTS idx_active_slot
                ON ParkingRecords(SlotNo)
                WHERE ExitTime IS NULL;
            """
        )
        self.connection.commit()

    def seed(self, slot_count: int) -> None:
        if self.connection.execute("SELECT COUNT(*) FROM ParkingSlots").fetchone()[0] == 0:
            self.connection.executemany(
                "INSERT INTO ParkingSlots (SlotID, Status) VALUES (?, 'Available')",
                [(slot_id,) for slot_id in range(1, slot_count + 1)],
            )
            self.connection.commit()

    def get_all_slots(self) -> list[ParkingSlot]:
        rows = self.connection.execute(
            "SELECT SlotID, Status FROM ParkingSlots ORDER BY SlotID"
        ).fetchall()
        return [ParkingSlot(row["SlotID"], row["Status"]) for row in rows]

    def get_available_slot(self) -> int | None:
        row = self.connection.execute(
            "SELECT SlotID FROM ParkingSlots WHERE Status = 'Available' ORDER BY SlotID LIMIT 1"
        ).fetchone()
        return int(row["SlotID"]) if row else None

    def get_slot_status(self, slot_id: int) -> str | None:
        row = self.connection.execute(
            "SELECT Status FROM ParkingSlots WHERE SlotID = ?",
            (slot_id,),
        ).fetchone()
        return row["Status"] if row else None

    def set_slot_status(self, slot_id: int, status: str) -> None:
        self.connection.execute(
            "UPDATE ParkingSlots SET Status = ? WHERE SlotID = ?",
            (status, slot_id),
        )
        self.connection.commit()

    def get_active_record(self, registration_number: str) -> dict | None:
        row = self.connection.execute(
            "SELECT * FROM ParkingRecords WHERE RegistrationNumber = ? AND ExitTime IS NULL ORDER BY RecordID DESC LIMIT 1",
            (registration_number.strip().upper(),),
        ).fetchone()
        return dict(row) if row else None

    def get_completed_records(self, registration_number: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM ParkingRecords WHERE RegistrationNumber = ? AND ExitTime IS NOT NULL ORDER BY RecordID DESC",
            (registration_number.strip().upper(),),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_all_active_records(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM ParkingRecords WHERE ExitTime IS NULL ORDER BY RecordID ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def add_entry(self, registration_number: str, slot_no: int, entry_time: datetime) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO ParkingRecords (RegistrationNumber, SlotNo, EntryTime, ExitTime, AmountPaid) VALUES (?, ?, ?, NULL, NULL)",
                (registration_number.strip().upper(), slot_no, _to_db(entry_time)),
            )

    def save_exit(self, record_id: int, exit_time: datetime, amount_paid: float) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE ParkingRecords SET ExitTime = ?, AmountPaid = ? WHERE RecordID = ?",
                (_to_db(exit_time), amount_paid, record_id),
            )

    def close(self) -> None:
        self.connection.close()
