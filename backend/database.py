import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "edgenlp.db"


def get_connection(db_path=None):
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path=None):
    conn = get_connection(db_path)
    with conn:
        # 1. Machines Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                machine_id TEXT PRIMARY KEY,
                machine_name TEXT NOT NULL,
                location TEXT NOT NULL,
                machine_type TEXT NOT NULL,
                status TEXT NOT NULL,
                installation_date TEXT NOT NULL
            )
        """)

        # 2. Sensor Readings Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                energy REAL NOT NULL,
                vibration REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
            )
        """)

        # 3. Production Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS production (
                production_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                units_produced INTEGER NOT NULL,
                defective_units INTEGER NOT NULL,
                production_date TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
            )
        """)

        # 4. Maintenance Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance (
                maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                maintenance_type TEXT NOT NULL,
                maintenance_date TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
            )
        """)

        # Performance Indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_machine_time 
            ON sensor_readings (machine_id, timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_timestamp 
            ON sensor_readings (timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prod_machine_date 
            ON production (machine_id, production_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_maint_machine_date 
            ON maintenance (machine_id, maintenance_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_maint_status 
            ON maintenance (status)
        """)
    conn.close()


def get_database_stats(db_path=None):
    conn = get_connection(db_path)
    stats = {}
    tables = ["machines", "sensor_readings", "production", "maintenance"]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        stats[t] = count
    conn.close()
    return stats


if __name__ == "__main__":
    initialize_database()
    print("Database schema initialized with 4 relational tables and indexes.")
    print("Current table row counts:", get_database_stats())
