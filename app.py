"""Flask application for the parking management system."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, render_template, request

from parking import ParkingSystem


def _format_plate(value: str) -> str:
    cleaned = "".join(char for char in (value or "").upper() if char.isalnum())
    if not cleaned:
        return ""

    letters = "".join(char for char in cleaned if char.isalpha())
    digits = "".join(char for char in cleaned if char.isdigit())

    if len(cleaned) >= 7 and letters[:3].isalpha() and digits[:3].isdigit() and letters[-1].isalpha():
        return f"{letters[:3]} {digits[:3]} {letters[-1]}"

    if letters and digits:
        return f"{letters[:3]} {digits[:3]}" if len(letters) >= 3 else f"{letters} {digits}"

    return cleaned[:3] + (f" {cleaned[3:]}" if len(cleaned) > 3 else "")


def _bay_label(slot_no: int) -> str:
    return f"B-{slot_no:02d}"


def _build_activity(active_records: list[dict], completed_records: list[dict]) -> list[dict]:
    activity: list[dict] = []
    for record in active_records[:5]:
        activity.append({
            "label": f"{_format_plate(record['registration_number'])} entered → Bay {_bay_label(record['slot_no'])}",
            "kind": "entry",
        })
    for record in completed_records[:5]:
        activity.append({
            "label": f"{_format_plate(record['registration_number'])} exited → KSh {float(record['amount_paid'] or 0):.2f} paid",
            "kind": "exit",
        })
    return activity[:6]


def create_app(database_path: str = "parking.db", slot_count: int = 10):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DATABASE_PATH"] = database_path
    app.config["SLOT_COUNT"] = slot_count
    app.config["parking_system"] = ParkingSystem.create(
        database_path, slot_count)

    @app.route("/", methods=["GET", "POST"])
    def dashboard():
        system = app.config["parking_system"]
        message = ""
        error = ""

        if request.method == "POST":
            registration_number = (request.form.get(
                "registration_number") or "").strip().upper()
            action = request.form.get("action")
            try:
                if action == "entry":
                    result = system.entry(registration_number)
                    message = f"Vehicle {result['registration_number']} assigned to slot {result['slot_id']}."
                elif action == "exit":
                    result = system.exit(registration_number)
                    message = (
                        f"Vehicle {result['plate']} exited. Duration: {result['duration_seconds']}s, "
                        f"Amount due: KSh {result['amount_paid']:.2f}."
                    )
                else:
                    error = "Unknown action."
            except (RuntimeError, ValueError) as exc:
                error = str(exc)

        slot_rows = system.status()
        total_slots = len(slot_rows)
        available_slots = system.available_slots
        occupied_slots = total_slots - available_slots
        active_records = system.active_records()
        completed_records = system.completed_records()
        today = datetime.now(timezone.utc).date()

        vehicles_entered_today = 0
        vehicles_exited_today = 0
        payments_collected_today = 0.0
        for row in system.database.connection.execute("SELECT * FROM ParkingRecords").fetchall():
            entry_time = datetime.fromisoformat(
                row["EntryTime"]).astimezone(timezone.utc)
            exit_time = row["ExitTime"]
            if entry_time.date() == today:
                vehicles_entered_today += 1
            if exit_time is not None:
                exit_dt = datetime.fromisoformat(
                    exit_time).astimezone(timezone.utc)
                if exit_dt.date() == today:
                    vehicles_exited_today += 1
                    payments_collected_today += float(row["AmountPaid"] or 0)

        availability_percent = (
            available_slots / total_slots * 100) if total_slots else 0
        recent_activity = _build_activity(active_records, completed_records)

        return render_template(
            "dashboard.html",
            title="Parking-Management-System",
            available_slots=available_slots,
            occupied_slots=occupied_slots,
            total_slots=total_slots,
            availability_percent=availability_percent,
            slots=slot_rows,
            active_records=[{
                **record,
                "display_plate": _format_plate(record["registration_number"]),
                "bay_label": _bay_label(record["slot_no"]),
            } for record in active_records],
            completed_records=[{
                **record,
                "display_plate": _format_plate(record["registration_number"]),
                "bay_label": _bay_label(record["slot_no"]),
            } for record in completed_records[:5]],
            recent_activity=recent_activity,
            vehicles_entered_today=vehicles_entered_today,
            vehicles_exited_today=vehicles_exited_today,
            payments_collected_today=round(payments_collected_today, 2),
            currently_parked=len(active_records),
            message=message,
            error=error,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
