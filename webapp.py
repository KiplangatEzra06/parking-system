"""Compatibility wrapper for the older web app test interface."""

from __future__ import annotations

from parking import ParkingSystem


class ParkingWebApp:
    """Minimal web-API wrapper used by the legacy test suite."""

    def __init__(self, database_path: str, slot_count: int = 10):
        self.database_path = database_path
        self.slot_count = slot_count
        self.system = ParkingSystem.create(database_path, slot_count)
        self._slot_vehicle_types: dict[int, str | None] = {}

    def close(self) -> None:
        self.system.database.close()

    def status_payload(self) -> dict:
        payload = {"available_slots": self.system.available_slots, "slots": []}
        for slot in self.system.status():
            slot_id = slot["slot_id"]
            occupied = slot["status"] == "Occupied"
            payload["slots"].append(
                {
                    "slot_id": slot_id,
                    "occupied": occupied,
                    "vehicle_type": self._slot_vehicle_types.get(slot_id),
                }
            )
        return payload

    def handle_entry(self, registration_number: str, vehicle_type: str | None = None) -> dict:
        result = self.system.entry(registration_number)
        self._slot_vehicle_types[result["slot_id"]] = vehicle_type
        return {
            "plate": registration_number.upper(),
            "slot_id": result["slot_id"],
            "vehicle_type": vehicle_type,
        }

    def handle_exit(self, registration_number: str) -> dict:
        receipt = self.system.exit(registration_number)
        self._slot_vehicle_types.pop(receipt["slot_id"], None)
        return receipt
