import datetime
import mysql.connector
from database import connect_db


def check_vacancy():
    """Returns the number of free slots as a plain int."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM parking_slots WHERE is_occupied = FALSE")
        return int(cursor.fetchone()[0])
    except mysql.connector.Error:
        return 0
    finally:
        conn.close()


def get_all_slots():
    """
    Returns a list of dicts with slot_id, is_occupied, vehicle_plate, arrival_time.
    Used by the dashboard grid so it can show exactly which plate is in which slot.
    """
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT slot_id, is_occupied, vehicle_plate, arrival_time FROM parking_slots ORDER BY slot_id")
        return cursor.fetchall()
    except mysql.connector.Error:
        return []
    finally:
        conn.close()


def register_vehicle(owner, plate, brand, model):
    """Insert a vehicle — returns a result string."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO vehicles (owner_name, number_plate, brand, model) VALUES (%s, %s, %s, %s)",
            (owner, plate.upper().strip(), brand.strip(), model.strip())
        )
        conn.commit()
        return f"Vehicle {plate.upper()} registered successfully."
    except mysql.connector.IntegrityError:
        return "This number plate is already registered."
    except mysql.connector.Error as e:
        return f"Database error: {e}"
    finally:
        conn.close()


def reserve_slot(number_plate):
    """
    Assign the first free slot to number_plate.
    FIX 1: datetime.now() → datetime.datetime.now()
    FIX 2: returns a result string instead of printing, so the GUI can display it.
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT slot_id FROM parking_slots WHERE is_occupied = FALSE LIMIT 1")
        slot = cursor.fetchone()

        if not slot:
            return "No slots available at the moment."

        slot_id = slot[0]
        current_time = datetime.datetime.now()   # FIX 1

        cursor.execute(
            """
            UPDATE parking_slots
            SET is_occupied = TRUE,
                vehicle_plate = %s,
                arrival_time  = %s
            WHERE slot_id = %s
            """,
            (number_plate.upper().strip(), current_time, slot_id)
        )
        conn.commit()
        return f"Slot {slot_id} reserved successfully for {number_plate.upper()}."

    except mysql.connector.Error as e:
        conn.rollback()
        return f"Database error: {e}"
    finally:
        conn.close()


def cancel_slot(slot_id):
    """
    Free a slot by slot_id, record a receipt, and return result string.
    Annual subscription slots cannot be cancelled.
    """
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # fetch slot info first
        cursor.execute(
            """
            SELECT vehicle_plate, arrival_time
            FROM parking_slots
            WHERE slot_id = %s
            """,
            (slot_id,)
        )
        row = cursor.fetchone()

        if not row or not row[0]:
            return f"Slot {slot_id} is already free."

        plate, arrival_time = row

        # check if this plate has active subscription
        cursor.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE number_plate = %s
            AND valid_till >= CURDATE()
            """,
            (plate,)
        )
        sub = cursor.fetchone()

        if sub:
            return (
                f"Slot {slot_id} is permanently reserved "
                f"under annual subscription and cannot be cancelled."
            )

        # calculate fee
        exit_time = datetime.datetime.now()
        fee = calculate_fee(arrival_time, exit_time) if arrival_time else 0

        # save receipt
        cursor.execute(
            """
            INSERT INTO receipts
            (number_plate, entry_time, exit_time, fee)
            VALUES (%s, %s, %s, %s)
            """,
            (plate, arrival_time, exit_time, fee)
        )

        # free slot
        cursor.execute(
            """
            UPDATE parking_slots
            SET is_occupied   = FALSE,
                vehicle_plate = NULL,
                arrival_time  = NULL
            WHERE slot_id = %s
            """,
            (slot_id,)
        )

        conn.commit()

        return f"Slot {slot_id} cleared. Fee for {plate}: ₹{fee}."

    except mysql.connector.Error as e:
        conn.rollback()
        return f"Database error: {e}"

    finally:
        conn.close()


def calculate_fee(entry_time, exit_time):
    """
    Hourly rate: ₹80 during peak hours (8–11, 17–21), ₹50 off-peak.
    FIX: uses total_seconds() instead of .seconds so trips over 1 hour work correctly.
    """
    duration = exit_time - entry_time
    total_hours = max(1, int(duration.total_seconds() // 3600))   # FIX

    total_fee = 0
    for hour in range(total_hours):
        current_hour = (entry_time.hour + hour) % 24
        if 8 <= current_hour <= 11 or 17 <= current_hour <= 21:
            total_fee += 80
        else:
            total_fee += 50

    return total_fee


import threading
import time


def free_slot_after_delay(slot_id, delay):
    """
    Automatically frees a normal reserved slot after ETA.
    Subscription slots are ignored.
    """
    time.sleep(delay)

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # check if slot belongs to active subscription
        cursor.execute(
            """
            SELECT vehicle_plate
            FROM parking_slots
            WHERE slot_id = %s
            """,
            (slot_id,)
        )
        row = cursor.fetchone()

        if not row or not row[0]:
            return

        plate = row[0]

        cursor.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE number_plate = %s
            AND valid_till >= CURDATE()
            """,
            (plate,)
        )
        sub = cursor.fetchone()

        # do not free permanent subscription slot
        if sub:
            return

        cursor.execute(
            """
            UPDATE parking_slots
            SET is_occupied = FALSE,
                vehicle_plate = NULL,
                arrival_time = NULL
            WHERE slot_id = %s
            """,
            (slot_id,)
        )

        conn.commit()

    finally:
        conn.close()


def call_car(slot_id=None, floor=1):
    """
    Retrieve car and auto-free normal slot after ETA.
    """
    eta = 30 + floor * 20
    location = f"slot {slot_id}" if slot_id else "your slot"

    # auto-free only if slot_id exists
    if slot_id:
        timer_thread = threading.Thread(
            target=free_slot_after_delay,
            args=(slot_id, eta),
            daemon=True
        )
        timer_thread.start()

    return f"Your car is being retrieved from {location}. ETA: {eta} seconds."


def assign_permanent_slot(number_plate, slot_id):
    """
    Subscribe a vehicle to a permanent slot for 1 year.
    Permanently occupies the slot.
    """
    conn = connect_db()
    cursor = conn.cursor()

    try:
        plate = number_plate.upper().strip()

        # check if already subscribed
        cursor.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE number_plate = %s
            AND valid_till >= CURDATE()
            """,
            (plate,)
        )
        existing = cursor.fetchone()

        if existing:
            return f"{plate} already has an active yearly subscription."

        # occupy slot permanently
        cursor.execute(
            """
            UPDATE parking_slots
            SET is_occupied = TRUE,
                vehicle_plate = %s
            WHERE slot_id = %s
            """,
            (plate, slot_id)
        )

        # add subscription
        cursor.execute(
            """
            INSERT INTO subscriptions
            (number_plate, permanent_slot, amount_paid, valid_till)
            VALUES (%s, %s, %s, DATE_ADD(CURDATE(), INTERVAL 1 YEAR))
            """,
            (plate, slot_id, 5000)
        )

        conn.commit()

        return (
            f"Permanent slot {slot_id} assigned to {plate}. "
            f"Valid for 1 year."
        )

    except mysql.connector.Error as e:
        conn.rollback()
        return f"Database error: {e}"

    finally:
        conn.close()


def pay_annual_fee(number_plate, payment_method):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # check if already subscribed
    cursor.execute("""
        SELECT * FROM subscriptions
        WHERE number_plate = %s
        AND valid_till >= CURDATE()
    """, (number_plate,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return f"Subscription already active. Permanent slot: {existing['permanent_slot']}"

    # find first empty slot
    cursor.execute("""
        SELECT slot_id
        FROM parking_slots
        WHERE is_occupied = 0
        LIMIT 1
    """)
    slot = cursor.fetchone()

    if not slot:
        conn.close()
        return "No empty slots available for subscription."

    slot_id = slot["slot_id"]

    # permanently occupy slot
    cursor.execute("""
        UPDATE parking_slots
        SET is_occupied = 1,
            vehicle_plate = %s
        WHERE slot_id = %s
    """, (number_plate, slot_id))

    # create subscription for 1 year
    cursor.execute("""
        INSERT INTO subscriptions
        (number_plate, permanent_slot, amount_paid, valid_till)
        VALUES (%s, %s, %s, DATE_ADD(CURDATE(), INTERVAL 1 YEAR))
    """, (number_plate, slot_id, 5000))

    conn.commit()
    conn.close()

    return f"Subscription successful. Permanent slot {slot_id} booked for 1 year."