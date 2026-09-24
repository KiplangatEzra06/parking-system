import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from parking import ParkingSystem, VehicleType, calculate_fee


class ParkingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.current_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.system = ParkingSystem.create(
            self.temp_dir.name + "/parking.sqlite", slot_count=1)
        self.system._now = lambda: self.current_time

    def tearDown(self):
        self.system.database.close()
        self.temp_dir.cleanup()

    def test_rejects_entry_when_lot_is_full(self):
        self.system.entry("ABC123", VehicleType.CAR)
        with self.assertRaisesRegex(RuntimeError, "full"):
            self.system.entry("XYZ789", VehicleType.MOTORCYCLE)

    def test_fee_tiering_rounds_partial_hours_up(self):
        self.assertEqual(calculate_fee(
            timedelta(hours=1), VehicleType.CAR), 500.0)
        self.assertEqual(calculate_fee(
            timedelta(hours=1, seconds=1), VehicleType.CAR), 700.0)
        self.assertEqual(calculate_fee(
            timedelta(hours=3, minutes=1), VehicleType.CAR), 1100.0)

    def test_exit_uses_rates_persisted_in_database(self):
        self.system.database.connection.execute(
            "UPDATE rates SET first_hour_rate = 900, hourly_rate = 300 "
            "WHERE vehicle_type = 'Car'"
        )
        self.system.database.connection.commit()
        restored = ParkingSystem(self.system.database,
                                 clock=lambda: self.current_time)
        restored.entry("ABC123", VehicleType.CAR)
        self.current_time += timedelta(hours=1, seconds=1)

        receipt = restored.exit("ABC123")

        self.assertEqual(receipt.amount_paid, 1200.0)

    def test_double_exit_is_rejected(self):
        self.system.entry("ABC123", VehicleType.CAR)
        self.current_time += timedelta(minutes=30)
        self.system.exit("ABC123")
        with self.assertRaisesRegex(KeyError, "No active session"):
            self.system.exit("ABC123")

    def test_state_is_reloaded_from_sqlite(self):
        self.system.entry("ABC123", VehicleType.TRUCK)
        self.system.database.close()
        restored = ParkingSystem.create(
            self.temp_dir.name + "/parking.sqlite", slot_count=1)
        self.assertEqual(restored.available_slots, 0)
        self.assertEqual(restored.status()[0].vehicle_type, VehicleType.TRUCK)
        restored.database.close()


if __name__ == "__main__":
    unittest.main()
