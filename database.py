import mysql.connector
import os


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "8879739933"),
    "database": os.getenv("DB_NAME", "car_parking_system"),
}


def connect_db():
    return mysql.connector.connect(**DB_CONFIG)


def create_tables():
    """Create all required tables if they don't already exist."""
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            owner_name VARCHAR(255),
            number_plate VARCHAR(50) UNIQUE NOT NULL,
            brand VARCHAR(100),
            model VARCHAR(100),
            subscription ENUM('Yes','No') DEFAULT 'No'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parking_slots (
            slot_id INT PRIMARY KEY,
            is_occupied BOOLEAN DEFAULT FALSE,
            vehicle_plate VARCHAR(50) DEFAULT NULL,
            arrival_time DATETIME DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            number_plate VARCHAR(50) NOT NULL,
            permanent_slot INT,
            amount_paid DECIMAL(10,2),
            valid_till DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            number_plate VARCHAR(50),
            entry_time DATETIME,
            exit_time DATETIME,
            fee DECIMAL(10,2),
            payment_method VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def seed_initial_data():
    """Seed sample vehicles and parking slots."""
    conn = connect_db()
    cursor = conn.cursor()

    sample_cars = [
        ("Rahul Sharma", "MH01AB1234", "Hyundai", "Creta"),
        ("Aman Verma", "MH02CD5678", "Honda", "City"),
        ("Priya Singh", "MH03EF9012", "Tata", "Nexon"),
        ("Karan Mehta", "MH04GH3456", "Maruti", "Baleno"),
    ]

    # Insert sample vehicles
    for car in sample_cars:
        try:
            cursor.execute("""
                INSERT INTO vehicles (owner_name, number_plate, brand, model)
                VALUES (%s, %s, %s, %s)
            """, car)
        except mysql.connector.IntegrityError:
            pass

    # Clear old parking slots before reseeding
    cursor.execute("DELETE FROM parking_slots")

    # Create 150 slots
    # First 25 occupied, remaining empty
    for i in range(1, 151):
        occupied = 1 if i <= 25 else 0

        cursor.execute("""
            INSERT INTO parking_slots (slot_id, is_occupied)
            VALUES (%s, %s)
        """, (i, occupied))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    seed_initial_data()
    print("Database setup complete with 150 parking slots.")