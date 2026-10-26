#!/usr/bin/env python3
"""Demo data generator for movement records"""

import os
import sys
import random
import logging
import argparse
from datetime import datetime, timedelta

# Ensure local imports and environment resolution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import env_loader
except ImportError:
    pass

from db_adapter import get_db_connection as get_adapter_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('ParkingDataGen')

VEHICLE_TYPES = ['Car', 'Bike', 'SUV', 'Microbus', 'CNG', 'Pickup', 'Auto']

PLATE_PATTERNS = [
    ('Dhaka', 'Metro', ['Ga', 'Gha', 'Kha', 'Cha', 'Ba', 'Ha']),
    ('Chatt', 'Metro', ['Ka', 'Kha', 'Ga', 'Gha']),
    ('Sylhet', 'Metro', ['Ka', 'Ga']),
    ('Rajshahi', 'Metro', ['Ka', 'Kha']),
    ('Khulna', 'Metro', ['Ga', 'Ka']),
    ('Cumilla', 'Metro', ['Ka', 'Ga']),
    ('Gazipur', 'Metro', ['Ka', 'Kha', 'Ga']),
]

def generate_plate() -> str:
    """Generate a realistic vehicle number plate."""
    city, area, letters = random.choice(PLATE_PATTERNS)
    letter = random.choice(letters)
    num1 = random.randint(11, 88)
    num2 = random.randint(1000, 9999)
    return f"{city} Metro-{letter} {num1}-{num2}"

def build_parking_sessions(count: int = 120) -> list[dict]:
    """Build realistic parking entries & exits with duration calculations."""
    now = datetime.now()
    records = []

    # 1. Generate EXITED vehicles (past completed visits today & yesterday)
    exited_count = int(count * 0.70)
    for _ in range(exited_count):
        vtype = random.choices(
            VEHICLE_TYPES,
            weights=[45, 20, 15, 8, 6, 4, 2],
            k=1
        )[0]
        plate = generate_plate()
        
        # Entry between 24 hours ago and 2 hours ago
        minutes_ago = random.randint(120, 1440)
        entry_time = now - timedelta(minutes=minutes_ago)
        
        # Duration parked: between 20 minutes and 11 hours (660 mins)
        duration_minutes = random.randint(20, min(minutes_ago - 10, 660))
        exit_time = entry_time + timedelta(minutes=duration_minutes)

        records.append({
            'plate_number': plate,
            'vehicle_type': vtype,
            'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_minutes': duration_minutes,
            'status': 'EXITED',
            'entry_gate': 'Gate 1 (Inbound)',
            'exit_gate': 'Gate 2 (Outbound)',
            'entry_image': f"captured_vehicles/{vtype.lower()}_{entry_time.strftime('%Y%m%d_%H%M%S')}.jpg",
            'exit_image': f"captured_vehicles/{vtype.lower()}_{exit_time.strftime('%Y%m%d_%H%M%S')}.jpg",
            'confidence': round(random.uniform(90.0, 99.5), 1),
            'plate_conf': round(random.uniform(85.0, 98.0), 1),
            'slot_number': f"{random.choice(['A','B','C'])}-{random.randint(1, 50):02d}",
        })

    # 2. Generate CURRENTLY PARKED vehicles (still inside now, exit_time = NULL)
    parked_count = count - exited_count
    for i in range(parked_count):
        vtype = random.choices(
            VEHICLE_TYPES,
            weights=[50, 18, 16, 6, 5, 3, 2],
            k=1
        )[0]
        plate = generate_plate()
        
        # Entered between 15 minutes ago and 8 hours ago today
        minutes_parked = random.randint(15, 480)
        entry_time = now - timedelta(minutes=minutes_parked)

        records.append({
            'plate_number': plate,
            'vehicle_type': vtype,
            'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': None,
            'duration_minutes': minutes_parked,
            'status': 'PARKED',
            'entry_gate': 'Gate 1 (Inbound)',
            'exit_gate': None,
            'entry_image': f"captured_vehicles/{vtype.lower()}_{entry_time.strftime('%Y%m%d_%H%M%S')}.jpg",
            'exit_image': '',
            'confidence': round(random.uniform(92.0, 99.8), 1),
            'plate_conf': round(random.uniform(88.0, 98.5), 1),
            'slot_number': f"{random.choice(['A','B','C'])}-{random.randint(1, 50):02d}",
        })

    records.sort(key=lambda r: r['entry_time'], reverse=True)
    return records

def seed_database(records: list[dict], truncate: bool = False):
    conn = get_adapter_connection()
    if not conn:
        logger.error("Could not obtain database connection.")
        return

    cursor = conn.cursor()

    if truncate:
        try:
            cursor.execute("DELETE FROM parking_sessions;")
            cursor.execute("DELETE FROM vehicle_detections;")
            conn.commit()
            logger.info("Cleared existing parking sessions table.")
        except Exception as e:
            logger.warning(f"Could not truncate tables: {e}")

    sql_parking = """
        INSERT INTO parking_sessions
        (plate_number, vehicle_type, entry_time, exit_time, duration_minutes,
         status, entry_gate, exit_gate, entry_image, exit_image, confidence, plate_conf, slot_number)
        VALUES
        (%(plate_number)s, %(vehicle_type)s, %(entry_time)s, %(exit_time)s, %(duration_minutes)s,
         %(status)s, %(entry_gate)s, %(exit_gate)s, %(entry_image)s, %(exit_image)s, %(confidence)s, %(plate_conf)s, %(slot_number)s)
    """

    sql_legacy = """
        INSERT INTO vehicle_detections
        (vehicle_type, plate_number, image_path, camera_id, entry_time,
         confidence, toll_amount, plate_conf, lane, status)
        VALUES
        (%(vehicle_type)s, %(plate_number)s, %(entry_image)s, 1, %(entry_time)s,
         %(confidence)s, 0.00, %(plate_conf)s, %(entry_gate)s, 'verified')
    """

    for r in records:
        try:
            cursor.execute(sql_parking, r)
            cursor.execute(sql_legacy, r)
        except Exception as e:
            logger.debug(f"Row insert note: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Successfully seeded {len(records)} realistic parking sessions into DB.")

def print_summary(records: list[dict]):
    parked = sum(1 for r in records if r['status'] == 'PARKED')
    exited = sum(1 for r in records if r['status'] == 'EXITED')
    avg_stay = sum(r['duration_minutes'] for r in records if r['status'] == 'EXITED') / max(1, exited)

    print("\n" + "=" * 50)
    print("🚗 SMART AI PARKING SYSTEM — DATA SUMMARY")
    print("=" * 50)
    print(f"Total Logged Movements : {len(records):,}")
    print(f"Currently Parked Inside : {parked:,} vehicles (Occupancy)")
    print(f"Completed Exits         : {exited:,} vehicles")
    print(f"Average Stay Duration   : {int(avg_stay // 60)}h {int(avg_stay % 60)}m ({int(avg_stay)} mins)")
    print("=" * 50 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Smart Parking Demo Data Generator')
    parser.add_argument('--count', type=int, default=100, help='Total movements to generate')
    parser.add_argument('--truncate', action='store_true', default=True, help='Clear old data before seeding')
    args = parser.parse_args()

    records = build_parking_sessions(count=args.count)
    print_summary(records)
    seed_database(records, truncate=args.truncate)

if __name__ == '__main__':
    main()
