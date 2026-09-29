import tempfile
import unittest

from webapp import ParkingWebApp


class ParkingWebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = ParkingWebApp(
            self.temp_dir.name + "/parking.sqlite", slot_count=2)

    def tearDown(self):
        self.app.close()
        self.temp_dir.cleanup()

    def test_status_payload_includes_slot_state(self):
        payload = self.app.status_payload()
        self.assertEqual(payload["available_slots"], 2)
        self.assertEqual(len(payload["slots"]), 2)
        self.assertFalse(payload["slots"][0]["occupied"])
        self.assertIsNone(payload["slots"][0]["vehicle_type"])

    def test_entry_and_exit_round_trip(self):
        self.app.handle_entry("ABC 123 A", "Car")
        payload = self.app.status_payload()
        self.assertEqual(payload["available_slots"], 1)
        self.assertTrue(payload["slots"][0]["occupied"])
        self.assertEqual(payload["slots"][0]["vehicle_type"], "Car")

        receipt = self.app.handle_exit("ABC 123 A")
        self.assertEqual(receipt["plate"], "ABC 123 A")
        self.assertGreaterEqual(receipt["amount_paid"], 0)


if __name__ == "__main__":
    unittest.main()
