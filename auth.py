import re
import bcrypt
import mysql.connector
from database import connect_db
 
 
def validate_password(password):
    """Min 8 chars, at least 1 uppercase and 1 special character."""
    pattern = r'^(?=.*[A-Z])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$'
    return bool(re.match(pattern, password))
 
 
def register_user(username, email, password, car_no, car_brand, car_model):
    """
    Register a new user and simultaneously insert their vehicle.
    FIX 1: accepts car_no, car_brand, car_model to match the GUI form.
    FIX 2: duplicate username/email/plate check with specific error messages.
    FIX 3: uses a transaction so user + vehicle are inserted atomically.
    FIX 4: finally block guarantees connection is always closed.
    """
    if not validate_password(password):
        return "Password must be 8+ characters with at least 1 uppercase letter and 1 special character (!@#$%^&*)."
 
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
 
    conn = connect_db()
    cursor = conn.cursor()
 
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (username, email, hashed_password.decode())
        )
 
        cursor.execute(
            """
            INSERT INTO vehicles (owner_name, number_plate, brand, model)
            VALUES (%s, %s, %s, %s)
            """,
            (username, car_no.upper().strip(), car_brand.strip(), car_model.strip())
        )
 
        conn.commit()
        return "Registration successful!"
 
    except mysql.connector.IntegrityError as e:
        conn.rollback()
        err = str(e).lower()
        if "username" in err:
            return "Username already taken. Please choose another."
        if "email" in err:
            return "An account with this email already exists."
        if "number_plate" in err:
            return "This number plate is already registered."
        return f"Registration failed: {e}"
 
    except mysql.connector.Error as e:
        conn.rollback()
        return f"Database error: {e}"
 
    finally:
        conn.close()
 
 
def login_user(username, password):
    """
    Returns True on valid credentials, False otherwise.
    FIX: wrapped in try/except so a DB outage doesn't crash the app.
    """
    conn = connect_db()
    cursor = conn.cursor()
 
    try:
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = %s",
            (username,)
        )
        result = cursor.fetchone()
 
        if result:
            stored_hash = result[0]
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return True
 
        return False
 
    except mysql.connector.Error:
        return False
 
    finally:
        conn.close()