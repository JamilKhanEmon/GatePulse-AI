-- Smart AI Parking Management System - Database Schema

CREATE DATABASE IF NOT EXISTS smart_parking
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_parking;

-- Main parking sessions table (Entry, Exit, Duration, Status)
CREATE TABLE IF NOT EXISTS parking_sessions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    plate_number        VARCHAR(64)   NOT NULL DEFAULT ''
                        COMMENT 'Detected vehicle license plate (e.g. Dhaka Metro-Ga 11-1234)',
    vehicle_type        VARCHAR(50)   NOT NULL DEFAULT 'Car'
                        COMMENT 'Bike, Car, SUV, CNG, Auto, Pickup, Microbus, Bus, Truck',
    entry_time          DATETIME      NOT NULL
                        COMMENT 'Timestamp when vehicle entered parking',
    exit_time           DATETIME      DEFAULT NULL
                        COMMENT 'Timestamp when vehicle exited parking (NULL if currently parked)',
    duration_minutes    INT           NOT NULL DEFAULT 0
                        COMMENT 'Total parked duration in minutes',
    status              ENUM('PARKED', 'EXITED') NOT NULL DEFAULT 'PARKED'
                        COMMENT 'PARKED = inside facility, EXITED = departed',
    entry_gate          VARCHAR(50)   NOT NULL DEFAULT 'Gate 1 (Inbound)'
                        COMMENT 'Camera/gate of entry',
    exit_gate           VARCHAR(50)   DEFAULT NULL
                        COMMENT 'Camera/gate of exit',
    entry_image         VARCHAR(512)  DEFAULT ''
                        COMMENT 'Vehicle image captured at entry gate',
    exit_image          VARCHAR(512)  DEFAULT ''
                        COMMENT 'Vehicle image captured at exit gate',
    confidence          DECIMAL(5,2)  NOT NULL DEFAULT 0.00
                        COMMENT 'YOLO vehicle detection confidence',
    plate_conf          DECIMAL(5,2)  NOT NULL DEFAULT 0.00
                        COMMENT 'OCR license plate recognition confidence',
    slot_number         VARCHAR(20)   DEFAULT NULL
                        COMMENT 'Assigned parking bay slot (e.g. A-12, B-05)',
    notes               TEXT          DEFAULT NULL,
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_plate         (plate_number),
    INDEX idx_status        (status),
    INDEX idx_entry_time    (entry_time),
    INDEX idx_exit_time     (exit_time),
    INDEX idx_vehicle_type  (vehicle_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Vehicle parking movements with entry/exit tracking and duration';

-- Backward-compatibility view for legacy detection queries
CREATE OR REPLACE VIEW vehicle_detections AS
SELECT
    id,
    vehicle_type,
    plate_number,
    entry_image AS image_path,
    1 AS camera_id,
    entry_time,
    confidence,
    0.00 AS toll_amount,
    plate_conf,
    entry_gate AS lane,
    CASE WHEN status = 'PARKED' THEN 'verified' ELSE 'manual_check' END AS status,
    created_at
FROM parking_sessions;

-- Parking capacity configuration
CREATE TABLE IF NOT EXISTS parking_config (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    facility_name       VARCHAR(100)  DEFAULT 'Smart Central Parking',
    total_capacity      INT           DEFAULT 150,
    overstay_threshold_hours INT      DEFAULT 12,
    updated_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO parking_config (id, facility_name, total_capacity, overstay_threshold_hours)
VALUES (1, 'Smart Central Parking Facility', 150, 12);

-- Operational Views

-- 1. Currently parked inside
CREATE OR REPLACE VIEW v_active_parked AS
SELECT
    id,
    plate_number,
    vehicle_type,
    entry_time,
    entry_gate,
    entry_image,
    TIMESTAMPDIFF(MINUTE, entry_time, NOW()) AS current_duration_minutes,
    slot_number
FROM parking_sessions
WHERE status = 'PARKED'
ORDER BY entry_time DESC;

-- 2. Daily Entry vs Exit counts
CREATE OR REPLACE VIEW v_daily_traffic AS
SELECT
    DATE(entry_time) AS log_date,
    COUNT(*) AS total_entries,
    SUM(CASE WHEN status = 'EXITED' THEN 1 ELSE 0 END) AS total_exits,
    SUM(CASE WHEN status = 'PARKED' THEN 1 ELSE 0 END) AS still_parked,
    AVG(CASE WHEN status = 'EXITED' THEN duration_minutes ELSE NULL END) AS avg_duration_minutes
FROM parking_sessions
GROUP BY DATE(entry_time)
ORDER BY log_date DESC;

-- 3. Vehicle distribution inside
CREATE OR REPLACE VIEW v_vehicle_occupancy AS
SELECT
    vehicle_type,
    COUNT(*) AS count_inside
FROM parking_sessions
WHERE status = 'PARKED'
GROUP BY vehicle_type;
