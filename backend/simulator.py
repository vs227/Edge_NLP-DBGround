import sys
import time
import random
from datetime import datetime
from database import get_connection, initialize_database

MACHINES = ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10"]

BASE_PROFILES = {
    "M01": {"temp": 42.0, "energy": 35.0, "vib": 1.2},
    "M02": {"temp": 58.0, "energy": 48.0, "vib": 1.8},
    "M03": {"temp": 82.5, "energy": 85.0, "vib": 3.6},
    "M04": {"temp": 38.0, "energy": 26.0, "vib": 0.8},
    "M05": {"temp": 49.0, "energy": 52.0, "vib": 1.4},
    "M06": {"temp": 44.0, "energy": 64.0, "vib": 0.9},
    "M07": {"temp": 36.5, "energy": 22.0, "vib": 0.7},
    "M08": {"temp": 63.0, "energy": 72.0, "vib": 2.9},
    "M09": {"temp": 31.0, "energy": 12.0, "vib": 0.4},
    "M10": {"temp": 39.0, "energy": 31.0, "vib": 1.1},
}


def generate_sensor_record(machine_id: str, ts: datetime = None):
    profile = BASE_PROFILES[machine_id]
    temp = round(profile["temp"] + random.uniform(-2.0, 2.5), 2)
    humidity = round(50.0 + random.uniform(-6.0, 6.0), 2)
    energy = round(profile["energy"] + random.uniform(-3.0, 3.5), 2)
    vib = round(profile["vib"] + random.uniform(-0.2, 0.3), 2)
    timestamp_str = (ts or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    return (machine_id, temp, humidity, energy, vib, timestamp_str)


def insert_sensor_batch(records):
    conn = get_connection()
    with conn:
        conn.executemany("""
            INSERT INTO sensor_readings (
                machine_id, temperature, humidity, energy, vibration, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, records)
    conn.close()


def run_continuous_simulation(interval: float = 5.0):
    print("Real-time simulator started for machines M01-M10.")
    print(f"Generating telemetry every {int(interval)} seconds... Press Ctrl+C to stop.\n")
    try:
        while True:
            records = [generate_sensor_record(m) for m in MACHINES]
            insert_sensor_batch(records)
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{now_str}] Generated {len(records)} sensor records (M01-M10)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    initialize_database()
    run_continuous_simulation(interval=5.0)
