import random
from datetime import datetime, timedelta
from database import get_connection, initialize_database, get_database_stats

MACHINES_SEED = [
    {"id": "M01", "name": "CNC Milling Alpha", "location": "Floor A - Section 1", "type": "CNC Mill", "status": "RUNNING", "installed": "2023-01-15", "base_temp": 42.0, "base_energy": 35.0, "base_vib": 1.2, "base_prod": 520, "def_rate": 0.02},
    {"id": "M02", "name": "CNC Lathe Beta", "location": "Floor A - Section 2", "type": "Lathe", "status": "RUNNING", "installed": "2023-02-10", "base_temp": 58.0, "base_energy": 48.0, "base_vib": 1.8, "base_prod": 480, "def_rate": 0.03},
    {"id": "M03", "name": "Hydraulic Press Gamma", "location": "Floor B - Heavy Line", "type": "Hydraulic Press", "status": "WARNING", "installed": "2022-11-05", "base_temp": 82.5, "base_energy": 85.0, "base_vib": 3.6, "base_prod": 290, "def_rate": 0.07},
    {"id": "M04", "name": "Robotic Welder Delta", "location": "Floor B - Assembly", "type": "Welding Robot", "status": "RUNNING", "installed": "2023-05-20", "base_temp": 38.0, "base_energy": 26.0, "base_vib": 0.8, "base_prod": 650, "def_rate": 0.01},
    {"id": "M05", "name": "Injection Molder Epsilon", "location": "Floor C - Plastics", "type": "Injection Molder", "status": "MAINTENANCE", "installed": "2022-08-14", "base_temp": 49.0, "base_energy": 52.0, "base_vib": 1.4, "base_prod": 410, "def_rate": 0.04},
    {"id": "M06", "name": "Laser Cutter Zeta", "location": "Floor A - Precision", "type": "Fiber Laser", "status": "RUNNING", "installed": "2023-09-01", "base_temp": 44.0, "base_energy": 64.0, "base_vib": 0.9, "base_prod": 590, "def_rate": 0.015},
    {"id": "M07", "name": "Industrial Robot Eta", "location": "Floor B - Packaging", "type": "Pick & Place", "status": "RUNNING", "installed": "2023-03-30", "base_temp": 36.5, "base_energy": 22.0, "base_vib": 0.7, "base_prod": 710, "def_rate": 0.008},
    {"id": "M08", "name": "Stamping Machine Theta", "location": "Floor C - Forming", "type": "Mechanical Press", "status": "RUNNING", "installed": "2022-06-18", "base_temp": 63.0, "base_energy": 72.0, "base_vib": 2.9, "base_prod": 460, "def_rate": 0.035},
    {"id": "M09", "name": "Surface Grinder Iota", "location": "Floor A - Tooling", "type": "Precision Grinder", "status": "IDLE", "installed": "2023-07-22", "base_temp": 31.0, "base_energy": 12.0, "base_vib": 0.4, "base_prod": 120, "def_rate": 0.01},
    {"id": "M10", "name": "Packaging Unit Kappa", "location": "Floor C - Logistics", "type": "Automated Bander", "status": "RUNNING", "installed": "2023-10-12", "base_temp": 39.0, "base_energy": 31.0, "base_vib": 1.1, "base_prod": 680, "def_rate": 0.012},
]

MAINTENANCE_ISSUES = [
    ("Bearing wear and vibration spike", "PREVENTIVE"),
    ("Hydraulic cylinder seal replacement", "CORRECTIVE"),
    ("Laser optics realignment and lens cleaning", "CALIBRATION"),
    ("Coolant leak and radiator flush", "CORRECTIVE"),
    ("Servo motor thermal overload check", "INSPECTION"),
    ("High-pressure pump valve inspection", "PREVENTIVE"),
    ("Conveyor belt tension adjustment", "PREVENTIVE"),
    ("Spindle runout calibration", "CALIBRATION"),
    ("Sensor telemetry drift calibration", "CALIBRATION"),
    ("Emergency stop switch replacement", "EMERGENCY"),
    ("Lubrication manifold flush and recharge", "PREVENTIVE"),
    ("Gearbox oil replacement and magnetic filter cleaning", "PREVENTIVE")
]


def seed_database(reset: bool = True):
    conn = get_connection()
    if reset:
        with conn:
            conn.execute("DROP TABLE IF EXISTS maintenance;")
            conn.execute("DROP TABLE IF EXISTS production;")
            conn.execute("DROP TABLE IF EXISTS sensor_readings;")
            conn.execute("DROP TABLE IF EXISTS machines;")
    conn.close()

    initialize_database()
    conn = get_connection()
    now = datetime.now()

    # 1. Seed Machines
    print("Seeding machines table...")
    with conn:
        for m in MACHINES_SEED:
            conn.execute("""
                INSERT OR REPLACE INTO machines (machine_id, machine_name, location, machine_type, status, installation_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (m["id"], m["name"], m["location"], m["type"], m["status"], m["installed"]))

    # 2. Seed Sensor Readings (At least 5,000 records)
    # 600 readings per machine = 6,000 total records covering past 2 days with 5-minute granularity
    # and last 2 hours with 30-second granularity for high density queries!
    print("Seeding sensor_readings table (6,000 records)...")
    sensor_records = []
    
    # 500 coarse historical steps (past 48 hours to past 2 hours, step ~5.5 min)
    for step in range(500, 0, -1):
        ts = now - timedelta(minutes=step * 5.5)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        for m in MACHINES_SEED:
            temp = round(m["base_temp"] + random.uniform(-2.5, 3.0), 2)
            hum = round(50.0 + random.uniform(-8.0, 8.0), 2)
            energy = round(m["base_energy"] + random.uniform(-4.0, 4.0), 2)
            vib = round(m["base_vib"] + random.uniform(-0.25, 0.35), 2)
            sensor_records.append((m["id"], temp, hum, energy, vib, ts_str))

    # 100 dense fine-grained steps (last 2 hours to present, step ~1.2 min)
    for step in range(100, -1, -1):
        ts = now - timedelta(minutes=step * 1.2)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        for m in MACHINES_SEED:
            temp = round(m["base_temp"] + random.uniform(-2.0, 2.5), 2)
            hum = round(50.0 + random.uniform(-6.0, 6.0), 2)
            energy = round(m["base_energy"] + random.uniform(-3.0, 3.5), 2)
            vib = round(m["base_vib"] + random.uniform(-0.2, 0.3), 2)
            sensor_records.append((m["id"], temp, hum, energy, vib, ts_str))

    with conn:
        conn.executemany("""
            INSERT INTO sensor_readings (machine_id, temperature, humidity, energy, vibration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sensor_records)

    # 3. Seed Production (At least 1,000 records)
    # 100 daily records per machine covering past 100 days = 1,000 records
    print("Seeding production table (1,000 records)...")
    production_records = []
    for day in range(100, -1, -1):
        p_date = (now - timedelta(days=day)).strftime("%Y-%m-%d")
        for m in MACHINES_SEED:
            base = m["base_prod"]
            # Sunday has lower output
            day_of_week = (now - timedelta(days=day)).weekday()
            factor = 0.4 if day_of_week == 6 else 1.0
            
            units = int(base * factor + random.randint(-40, 50))
            if units < 0:
                units = 0
            
            # Anomaly: M03 has high defects; M05 has 0 output today if under maintenance
            if day == 0 and m["id"] == "M05":
                units = 45
            
            defects = int(units * m["def_rate"] + random.randint(0, 3))
            production_records.append((m["id"], units, defects, p_date))

    with conn:
        conn.executemany("""
            INSERT INTO production (machine_id, units_produced, defective_units, production_date)
            VALUES (?, ?, ?, ?)
        """, production_records)

    # 4. Seed Maintenance (At least 100 records)
    # 120 historical and current maintenance records across all machines
    print("Seeding maintenance table (120 records)...")
    maintenance_records = []
    
    # Historical completed records over past 180 days
    for i in range(110):
        m = random.choice(MACHINES_SEED)
        days_ago = random.randint(3, 180)
        m_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        issue, m_type = random.choice(MAINTENANCE_ISSUES)
        maintenance_records.append((m["id"], issue, m_type, m_date, "COMPLETED"))

    # Specific well-known records for benchmark queries:
    # M05 has an active maintenance issue ongoing today!
    maintenance_records.append(("M05", "Hydraulic cylinder seal replacement and valve leak", "CORRECTIVE", now.strftime("%Y-%m-%d"), "IN_PROGRESS"))
    # M03 has scheduled maintenance
    maintenance_records.append(("M03", "Cooling system descaling and radiator flush", "PREVENTIVE", (now - timedelta(days=2)).strftime("%Y-%m-%d"), "IN_PROGRESS"))
    # M02 last maintenance 12 days ago
    maintenance_records.append(("M02", "Spindle runout calibration and bearing lubrication", "PREVENTIVE", (now - timedelta(days=12)).strftime("%Y-%m-%d"), "COMPLETED"))
    # M01 last maintenance 25 days ago
    maintenance_records.append(("M01", "Conveyor belt tension adjustment", "PREVENTIVE", (now - timedelta(days=25)).strftime("%Y-%m-%d"), "COMPLETED"))
    # Additional scheduled records
    for i in range(8):
        m = random.choice(MACHINES_SEED)
        days_ahead = random.randint(1, 14)
        m_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        issue, m_type = random.choice(MAINTENANCE_ISSUES)
        maintenance_records.append((m["id"], issue, m_type, m_date, "SCHEDULED"))

    with conn:
        conn.executemany("""
            INSERT INTO maintenance (machine_id, issue, maintenance_type, maintenance_date, status)
            VALUES (?, ?, ?, ?, ?)
        """, maintenance_records)

    conn.close()
    stats = get_database_stats()
    print("\n--- Seeding Complete ---")
    print(f"Machines:        {stats['machines']}")
    print(f"Sensor Readings: {stats['sensor_readings']}")
    print(f"Production:      {stats['production']}")
    print(f"Maintenance:     {stats['maintenance']}")
    return stats


if __name__ == "__main__":
    seed_database(reset=True)
