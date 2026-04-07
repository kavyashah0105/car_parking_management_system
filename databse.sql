CREATE DATABASE car_parking_system;
USE car_parking_system;

CREATE TABLE vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    number_plate VARCHAR(20) UNIQUE NOT NULL,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    subscription VARCHAR(10) DEFAULT 'No'
);

CREATE TABLE parking_slots (
    slot_id INT PRIMARY KEY,
    is_occupied BOOLEAN DEFAULT FALSE,
    vehicle_plate VARCHAR(20),
    arrival_time DATETIME
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255)
);