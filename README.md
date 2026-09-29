# Parking Management System

This project implements the parking system described in [algorithm.md](algorithm.md). It stores parking slots and active/completed records in SQLite, enforces the active-slot and active-vehicle rules, and exposes a small browser dashboard and CLI.

## Project structure

- [app.py](app.py) — Flask application entry point
- [main.py](main.py) — command-line interface
- [parking](parking) — domain logic and SQLite persistence
- [templates](templates) — dashboard template
- [static](static) — CSS styling
- [tests](tests) — automated verification
- [algorithm.md](algorithm.md) — source-of-truth specification

## Setup

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Initialize and run

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

The default lot size is 10 slots, and the value can be changed by passing `slot_count` when creating the app or by updating the default configuration in [app.py](app.py).

## Fee rule

The documented fee rule is KSh 50 per hour, calculated as:

```text
amount = (duration_in_seconds / 3600) * 50
```

The result is rounded to 2 decimal places. This follows the specification in [algorithm.md](algorithm.md) and does not use a custom started-hour rounding rule.

## Database behavior

The database is created automatically if it does not exist. It includes:

- `ParkingSlots` with `SlotID` and `Status`
- `ParkingRecords` with `RecordID`, `RegistrationNumber`, `SlotNo`, `EntryTime`, `ExitTime`, and `AmountPaid`

The `SlotNo` foreign key points to `ParkingSlots.SlotID`, and duplicate active registrations or active assignments are prevented by the application and database constraints.

## Tests

```powershell
py -m unittest discover -s tests -v
```
