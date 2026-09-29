# Parking Management System Algorithm

## Goal
The system tracks parking slots and active parking records for vehicles entering and leaving a small parking lot.

## Data model
### 1. ParkingSlots
A table named `ParkingSlots` stores one row per parking space.

Columns:
- `SlotID` — integer primary key
- `Status` — text status of the slot, either `Available` or `Occupied`

### 2. ParkingRecords
A table named `ParkingRecords` stores each parking session.

Columns:
- `RecordID` — integer primary key
- `RegistrationNumber` — text registration number for the vehicle
- `SlotNo` — integer foreign key referring to `ParkingSlots.SlotID`
- `EntryTime` — timestamp when the vehicle entered
- `ExitTime` — timestamp when the vehicle exited; null while the vehicle is still parked
- `AmountPaid` — decimal amount charged for the stay

The relationship is:
- each active or completed parking record references exactly one slot
- a slot can be assigned to only one active vehicle at a time
- a vehicle can have only one active parking record at a time

## Parking slot behaviour
- When the system starts, every slot is created as `Available`.
- An available slot is assigned to a vehicle when it enters.
- The slot is marked `Occupied` while the vehicle is active.
- The slot is reset to `Available` when the vehicle exits.
- The system must track the number of available spaces and show it to the user.

## Entry workflow
1. Show the current number of available spaces.
2. Accept a registration number.
3. Reject empty or invalid registration numbers.
4. Reject a vehicle if it already has an active parking record.
5. Check whether any slot is available.
6. If no slot is available, deny entry and show a message.
7. If a slot is available, assign the vehicle to one slot.
8. Record the registration number, slot number, and entry time.
9. Mark the slot as `Occupied`.
10. Update the available-space count.

## Exit workflow
1. Accept a registration number.
2. Find the vehicle's active parking record.
3. Reject unknown vehicles with a clear message.
4. Record the exit time.
5. Calculate the parking duration.
6. Calculate the parking fee according to the rate rule below.
7. Store `AmountPaid` and `ExitTime` on the record.
8. Mark the slot as `Available`.
9. Update the available-space count.
10. Keep the completed record in the database for history.

## Fee calculation
The daily rate in this system is fixed at KSh 50 per hour.

The calculation is:
- `amount = (duration_in_seconds / 3600) * 50`
- the result is rounded to 2 decimal places

This means the charge is proportional to the actual elapsed parking time; it does not apply a custom started-hour rounding rule.

## Persistence and restart
- The database file is created automatically if it does not exist.
- Tables and indexes are created automatically on startup.
- Slot status and parking records remain consistent after application restart.
- Completed records remain stored after checkout.
- Active and completed records survive application restart.

## User interface requirements
The application should display:
- a title for the parking system
- available spaces
- the status of each parking slot
- a vehicle entry form
- a vehicle exit form
- active parking information
- completed parking information where appropriate
- clear success and error messages
- parking fee information

## Default configuration
The default parking lot size is 10 slots unless a different value is configured for the application.
