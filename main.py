"""Command-line interface for the parking management system."""

import argparse
import shlex

from parking import ParkingSystem, VehicleType


def main() -> None:
    parser = argparse.ArgumentParser(description="Parking management system")
    parser.add_argument("--database", default="parking.db")
    parser.add_argument("--slots", type=int, default=10)
    args = parser.parse_args()
    system = ParkingSystem.create(args.database, args.slots)
    print("Commands: entry <plate> <Motorcycle|Car|Truck>, exit <plate>, status, quit")
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
            if parts[0].lower() == "entry" and len(parts) == 3:
                session = system.entry(parts[1], VehicleType.parse(parts[2]))
                print(
                    f"Ticket: {session.plate} assigned to slot {session.slot_id}")
            elif parts[0].lower() == "exit" and len(parts) == 2:
                receipt = system.exit(parts[1])
                print(
                    f"Receipt: {receipt.plate}, {receipt.duration_seconds}s, KSh {receipt.amount_paid:.2f}")
            elif parts[0].lower() == "status" and len(parts) == 1:
                print(f"Available slots: {system.available_slots}")
                for slot in system.status():
                    vehicle_type = slot.vehicle_type
                    state = vehicle_type.value if vehicle_type is not None else "free"
                    print(f"  Slot {slot.id}: {state}")
            else:
                print("Usage: entry <plate> <type> | exit <plate> | status | quit")
        except (KeyError, RuntimeError, ValueError) as error:
            print(f"Error: {error}")
    system.database.close()


if __name__ == "__main__":
    main()
