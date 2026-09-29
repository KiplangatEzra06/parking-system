import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from app import create_app
from parking import ParkingSystem, calculate_fee


class ParkingSystemTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = self.temp_dir.name + "/parking.sqlite"
        self.system = ParkingSystem.create(self.db_path, slot_count=2)
        self.current_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.system._now = lambda: self.current_time

    def tearDown(self):
        self.system.database.close()
        self.temp_dir.cleanup()

    def test_default_slot_count_and_schema_are_created(self):
        conn = sqlite3.connect(self.db_path)
        slots = conn.execute(
            "SELECT SlotID, Status FROM ParkingSlots ORDER BY SlotID").fetchall()
        conn.close()
        self.assertEqual(len(slots), 2)
        self.assertEqual([status for _, status in slots],
                         ["Available", "Available"])

    def test_entry_records_slot_and_time(self):
        result = self.system.entry("ABC 123 A")
        self.assertEqual(result["slot_id"], 1)
        self.assertEqual(result["entry_time"], self.current_time.isoformat())
        self.assertEqual(self.system.database.get_slot_status(1), "Occupied")
        self.assertEqual(self.system.available_slots, 1)

    def test_duplicate_active_registration_is_rejected(self):
        self.system.entry("ABC 123 A")
        with self.assertRaisesRegex(ValueError, "already has an active parking record"):
            self.system.entry("ABC 123 A")

    def test_entry_requires_exact_plate_format(self):
        with self.assertRaisesRegex(ValueError, "ABC 123 A format"):
            self.system.entry("ABC123")
        with self.assertRaisesRegex(ValueError, "ABC 123 A format"):
            self.system.entry("ABC 123")

    def test_entry_when_full_is_rejected(self):
        self.system.entry("ABC 123 A")
        self.system.entry("XYZ 789 A")
        with self.assertRaisesRegex(RuntimeError, "No parking spaces available"):
            self.system.entry("QRS 456 A")

    def test_unknown_vehicle_exit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No active parking record"):
            self.system.exit("ABC123")

    def test_successful_exit_updates_record_and_slot(self):
        self.system.entry("ABC 123 A")
        self.current_time += timedelta(hours=2, minutes=30)
        receipt = self.system.exit("ABC 123 A")

        self.assertEqual(receipt["plate"], "ABC 123 A")
        self.assertEqual(receipt["slot_id"], 1)
        self.assertEqual(receipt["duration_seconds"], 9000)
        self.assertAlmostEqual(receipt["amount_paid"], 125.0)
        self.assertEqual(self.system.database.get_slot_status(1), "Available")
        self.assertEqual(self.system.available_slots, 2)

    def test_fee_formula_matches_algorithm(self):
        self.assertEqual(calculate_fee(timedelta(minutes=30)), 25.0)
        self.assertEqual(calculate_fee(timedelta(hours=1)), 50.0)
        self.assertEqual(calculate_fee(timedelta(hours=2, minutes=30)), 125.0)
        self.assertAlmostEqual(calculate_fee(
            timedelta(hours=3, minutes=1)), 150.83)

    def test_completed_record_remains_in_database(self):
        self.system.entry("ABC 123 A")
        self.current_time += timedelta(hours=1)
        self.system.exit("ABC 123 A")
        record = self.system.database.get_active_record("ABC 123 A")
        self.assertIsNone(record)
        completed = self.system.database.get_completed_records("ABC 123 A")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["RegistrationNumber"], "ABC 123 A")
        self.assertEqual(completed[0]["AmountPaid"], 50.0)

    def test_active_and_completed_records_survive_restart(self):
        self.system.entry("ABC 123 A")
        self.system.database.close()

        restored = ParkingSystem.create(self.db_path, slot_count=2)
        self.assertEqual(restored.available_slots, 1)
        self.assertEqual(restored.database.get_slot_status(1), "Occupied")
        active_record = restored.database.get_active_record("ABC 123 A")
        if active_record is None:
            self.fail("Expected the active record to survive restart.")
        self.assertEqual(active_record["RegistrationNumber"], "ABC 123 A")
        restored.database.close()

    def test_database_constraints_prevent_duplicate_active_slot_and_plate(self):
        self.system.entry("ABC 123 A")
        with self.assertRaisesRegex(ValueError, "already has an active parking record"):
            self.system.entry("ABC 123 A")

        self.system.exit("ABC 123 A")
        self.system.entry("XYZ 789 A")
        self.system.entry("QRS 999 A")
        self.assertEqual(self.system.available_slots, 0)


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = self.temp_dir.name + "/parking.sqlite"
        self.app = create_app(database_path=self.db_path, slot_count=2)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.config["parking_system"].database.close()
        self.temp_dir.cleanup()

    def test_dashboard_loads_with_available_slots(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Parking Management", response.get_data(as_text=True))
        self.assertIn("Available spaces", response.get_data(as_text=True))

    def test_entry_and_exit_routes_work(self):
        entry_response = self.client.post(
            "/", data={"action": "entry", "registration_number": "ABC 123 A"})
        self.assertEqual(entry_response.status_code, 200)
        self.assertIn("assigned to slot 1",
                      entry_response.get_data(as_text=True))

        exit_response = self.client.post(
            "/", data={"action": "exit", "registration_number": "ABC 123 A"})
        self.assertEqual(exit_response.status_code, 200)
        self.assertIn("Amount due: KSh", exit_response.get_data(as_text=True))

    def test_dashboard_includes_live_parking_view_and_plate_format(self):
        self.client.post(
            "/", data={"action": "entry", "registration_number": "ABC 123 A"})
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Live Parking View", response.get_data(as_text=True))
        self.assertIn("ABC 123 A", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
