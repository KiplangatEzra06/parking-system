"""Command-line interface for the parking management system."""

import argparse
import shlex

from parking import ParkingSystem


def main() -> None:
    parser = argparse.ArgumentParser(description="Parking management system")
    parser.add_argument("--database", default="parking.db")
    parser.add_argument("--slots", type=int, default=10)
    args = parser.parse_args()

    system = ParkingSystem.create(args.database, args.slots)
    print(f"Commands: entry <registration_number>, exit <registration_number>, status, quit")

    while True:
        try:
            parts = shlex.split(input("> "))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not parts:
            continue
        if parts[0].lower() in {"quit", "q"}:
            break

        try:
            if parts[0].lower() == "entry" and len(parts) == 2:
                result = system.entry(parts[1])
                print(
                    f"Vehicle {result['registration_number']} assigned to slot {result['slot_id']}")
            elif parts[0].lower() == "exit" and len(parts) == 2:
                result = system.exit(parts[1])
                print(
                    f"Receipt: {result['plate']}, {result['duration_seconds']}s, KSh {result['amount_paid']:.2f}")
            elif parts[0].lower() == "status" and len(parts) == 1:
                print(f"Available slots: {system.available_slots}")
                for slot in system.status():
                    print(f"  Slot {slot['slot_id']}: {slot['status']}")
            else:
                print(
                    "Usage: entry <registration_number> | exit <registration_number> | status | quit")
        except (RuntimeError, ValueError) as error:
            print(f"Error: {error}")

    system.database.close()


if __name__ == "__main__":
    main()
