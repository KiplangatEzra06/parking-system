"""SQLite persistence for slots, rates, and parking sessions."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import ParkingSlot, Session, VehicleType


def _to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _from_db(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


class ParkingDatabase:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS slots (
                slot_id INTEGER PRIMARY KEY,
                floor INTEGER NOT NULL,
                type TEXT,
                is_occupied BOOLEAN NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS parking_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                slot_id INTEGER NOT NULL,
                vehicle_type TEXT NOT NULL,
                entry_time DATETIME NOT NULL,
                exit_time DATETIME,
                amount_paid DECIMAL,
                status TEXT CHECK(status IN ('active','closed')) DEFAULT 'active',
                FOREIGN KEY (slot_id) REFERENCES slots(slot_id)
            );
            CREATE TABLE IF NOT EXISTS rates (
                vehicle_type TEXT PRIMARY KEY,
                first_hour_rate DECIMAL NOT NULL,
                hourly_rate DECIMAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_plate_status
                ON parking_sessions(plate_number, status);
            """
        )
        self.connection.commit()

    def seed(self, slots: list[ParkingSlot], rates: dict[VehicleType, tuple[float, float]]) -> None:
        if self.connection.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 0:
            self.connection.executemany(
                "INSERT INTO slots(slot_id, floor, type, is_occupied) VALUES (?, ?, ?, ?)",
                [(slot.id, slot.floor, None, int(slot.occupied))
                 for slot in slots],
            )
        self.connection.executemany(
            "INSERT OR REPLACE INTO rates(vehicle_type, first_hour_rate, hourly_rate) VALUES (?, ?, ?)",
            [(kind.value, first, hourly)
             for kind, (first, hourly) in rates.items()],
        )
        self.connection.commit()

    def load_slots(self) -> list[ParkingSlot]:
        rows = self.connection.execute(
            "SELECT * FROM slots ORDER BY slot_id").fetchall()
        return [ParkingSlot(row["slot_id"], row["floor"],
                            VehicleType.parse(
                                row["type"]) if row["type"] else None,
                            bool(row["is_occupied"])) for row in rows]

    def load_active_sessions(self) -> list[Session]:
        rows = self.connection.execute(
            "SELECT plate_number, slot_id, vehicle_type, entry_time "
            "FROM parking_sessions WHERE status = 'active'"
        ).fetchall()
        return [Session(row["plate_number"], row["slot_id"],
                        VehicleType.parse(row["vehicle_type"]), _from_db(row["entry_time"]))
                for row in rows]

    def load_rates(self) -> dict[VehicleType, tuple[float, float]]:
        rows = self.connection.execute(
            "SELECT vehicle_type, first_hour_rate, hourly_rate FROM rates"
        ).fetchall()
        return {
            VehicleType.parse(row["vehicle_type"]):
            (float(row["first_hour_rate"]), float(row["hourly_rate"]))
            for row in rows
        }

    def save_entry(self, session: Session) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE slots SET type = ?, is_occupied = 1 WHERE slot_id = ?",
                (session.vehicle_type.value, session.slot_id),
            )
            self.connection.execute(
                "INSERT INTO parking_sessions(plate_number, slot_id, vehicle_type, entry_time, status) "
                "VALUES (?, ?, ?, ?, 'active')",
                (session.plate, session.slot_id,
                 session.vehicle_type.value, _to_db(session.entry_time)),
            )

    def save_exit(self, session: Session, exit_time: datetime, amount: float) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE parking_sessions SET exit_time = ?, amount_paid = ?, status = 'closed' "
                "WHERE plate_number = ? AND status = 'active'",
                (_to_db(exit_time), amount, session.plate),
            )
            self.connection.execute(
                "UPDATE slots SET type = NULL, is_occupied = 0 WHERE slot_id = ?",
                (session.slot_id,),
            )

    def close(self) -> None:
        self.connection.close()
