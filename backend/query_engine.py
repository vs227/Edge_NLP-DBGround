import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from database import get_connection

ALLOWED_METRICS = {
    "temperature": "temperature",
    "humidity": "humidity",
    "energy": "energy",
    "vibration": "vibration",
}

ALLOWED_OPERATORS = {
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    "=": "=",
    "==": "=",
}


class QueryEngine:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        return self._conn if self._conn else get_connection()

    def execute_query(self, structured_query: Dict[str, Any]) -> Dict[str, Any]:
        intent = structured_query.get("intent")
        metric_raw = structured_query.get("metric", "temperature")
        metric = ALLOWED_METRICS.get(metric_raw, "temperature") if metric_raw else "temperature"

        machine_id = structured_query.get("machine_id")
        machines = structured_query.get("machines", [])
        if machine_id and machine_id not in machines:
            machines = [machine_id] + machines

        start_time = structured_query.get("start_time")
        end_time = structured_query.get("end_time")
        operator = ALLOWED_OPERATORS.get(structured_query.get("operator", ">"), ">")
        threshold = structured_query.get("threshold")
        status = structured_query.get("status")

        today_str = datetime.now().strftime("%Y-%m-%d")

        conn = self._get_conn()
        close_needed = self._conn is None

        try:
            # 1. GET_LATEST
            if intent == "GET_LATEST":
                return self._handle_get_latest(conn, machine_id, metric)

            # 2. GET_AVERAGE
            elif intent == "GET_AVERAGE":
                return self._handle_get_average(conn, machine_id, metric, start_time, end_time)

            # 3. GET_MAX
            elif intent == "GET_MAX":
                return self._handle_get_max(conn, machine_id, metric, start_time, end_time)

            # 4. GET_MIN
            elif intent == "GET_MIN":
                return self._handle_get_min(conn, machine_id, metric, start_time, end_time)

            # 5. FILTER_DATA
            elif intent == "FILTER_DATA":
                return self._handle_filter_data(conn, metric, operator, threshold, start_time, end_time)

            # 6. GET_STATUS
            elif intent == "GET_STATUS":
                return self._handle_get_status(conn, machine_id)

            # 7. GET_TREND
            elif intent == "GET_TREND":
                return self._handle_get_trend(conn, machine_id, metric, start_time, end_time)

            # 8. GET_PRODUCTION
            elif intent == "GET_PRODUCTION":
                return self._handle_get_production(conn, machine_id, today_str)

            # 9. GET_MAX_PRODUCTION
            elif intent == "GET_MAX_PRODUCTION":
                return self._handle_get_max_production(conn, today_str)

            # 10. GET_DEFECTS
            elif intent == "GET_DEFECTS":
                return self._handle_get_defects(conn, machine_id, today_str)

            # 11. COMPARE_PRODUCTION
            elif intent == "COMPARE_PRODUCTION":
                return self._handle_compare_production(conn, machines, today_str)

            # 12. COMPARE_SENSOR
            elif intent == "COMPARE_SENSOR":
                return self._handle_compare_sensor(conn, machines, metric, start_time, end_time)

            # 13. GET_MAINTENANCE_STATUS
            elif intent == "GET_MAINTENANCE_STATUS":
                return self._handle_get_maintenance_status(conn)

            # 14. GET_LAST_MAINTENANCE
            elif intent == "GET_LAST_MAINTENANCE":
                return self._handle_get_last_maintenance(conn, machine_id)

            # 15. ANOMALY_CORRELATION
            elif intent == "ANOMALY_CORRELATION":
                return self._handle_anomaly_correlation(conn, today_str)

            # 16. COUNT_EVENTS
            elif intent == "COUNT_EVENTS":
                return self._handle_count_events(conn, status)

            else:
                return {"success": False, "error": f"Unsupported intent: {intent}", "data": None}
        finally:
            if close_needed:
                conn.close()

    def _handle_get_latest(self, conn, machine_id, metric):
        if machine_id:
            sql = """
                SELECT s.machine_id, m.machine_name, m.location, m.status as machine_status,
                       s.temperature, s.humidity, s.energy, s.vibration, s.timestamp
                FROM sensor_readings s
                JOIN machines m ON s.machine_id = m.machine_id
                WHERE s.machine_id = ?
                ORDER BY s.timestamp DESC, s.reading_id DESC
                LIMIT 1
            """
            row = conn.execute(sql, (machine_id,)).fetchone()
            if not row:
                return {"success": True, "intent": "GET_LATEST", "found": False, "data": None}
            res = dict(row)
            return {
                "success": True,
                "intent": "GET_LATEST",
                "found": True,
                "machine_id": machine_id,
                "machine_name": res["machine_name"],
                "metric": metric,
                "value": res.get(metric),
                "data": res
            }
        else:
            sql = """
                SELECT s.machine_id, m.machine_name, s.temperature, s.humidity, s.energy, s.vibration, s.timestamp
                FROM sensor_readings s
                JOIN machines m ON s.machine_id = m.machine_id
                WHERE s.reading_id IN (
                    SELECT MAX(reading_id) FROM sensor_readings GROUP BY machine_id
                )
                ORDER BY s.machine_id ASC
            """
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            return {"success": True, "intent": "GET_LATEST", "found": len(rows) > 0, "data": rows}

    def _handle_get_average(self, conn, machine_id, metric, start_time, end_time):
        conditions = []
        params = []
        if machine_id:
            conditions.append("s.machine_id = ?")
            params.append(machine_id)
        if start_time:
            conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("s.timestamp <= ?")
            params.append(end_time)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT AVG(s.{metric}) as avg_val, COUNT(*) as count, m.machine_name
            FROM sensor_readings s
            LEFT JOIN machines m ON s.machine_id = m.machine_id
            {where_clause}
        """
        row = conn.execute(sql, tuple(params)).fetchone()
        avg_val = round(row["avg_val"], 2) if row and row["avg_val"] is not None else None
        count = row["count"] if row else 0

        return {
            "success": True,
            "intent": "GET_AVERAGE",
            "found": count > 0,
            "machine_id": machine_id,
            "machine_name": row["machine_name"] if row and row["machine_name"] else machine_id,
            "metric": metric,
            "value": avg_val,
            "sample_count": count,
            "start_time": start_time,
            "end_time": end_time
        }

    def _handle_get_max(self, conn, machine_id, metric, start_time, end_time):
        conditions = []
        params = []
        if machine_id:
            conditions.append("s.machine_id = ?")
            params.append(machine_id)
        if start_time:
            conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("s.timestamp <= ?")
            params.append(end_time)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT s.machine_id, m.machine_name, s.{metric} as max_val, s.timestamp
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            {where_clause}
            ORDER BY s.{metric} DESC
            LIMIT 1
        """
        row = conn.execute(sql, tuple(params)).fetchone()
        if not row or row["max_val"] is None:
            return {"success": True, "intent": "GET_MAX", "found": False, "data": None}

        return {
            "success": True,
            "intent": "GET_MAX",
            "found": True,
            "machine_id": row["machine_id"],
            "machine_name": row["machine_name"],
            "metric": metric,
            "value": round(row["max_val"], 2),
            "timestamp": row["timestamp"]
        }

    def _handle_get_min(self, conn, machine_id, metric, start_time, end_time):
        conditions = []
        params = []
        if machine_id:
            conditions.append("s.machine_id = ?")
            params.append(machine_id)
        if start_time:
            conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("s.timestamp <= ?")
            params.append(end_time)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT s.machine_id, m.machine_name, s.{metric} as min_val, s.timestamp
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            {where_clause}
            ORDER BY s.{metric} ASC
            LIMIT 1
        """
        row = conn.execute(sql, tuple(params)).fetchone()
        if not row or row["min_val"] is None:
            return {"success": True, "intent": "GET_MIN", "found": False, "data": None}

        return {
            "success": True,
            "intent": "GET_MIN",
            "found": True,
            "machine_id": row["machine_id"],
            "machine_name": row["machine_name"],
            "metric": metric,
            "value": round(row["min_val"], 2),
            "timestamp": row["timestamp"]
        }

    def _handle_filter_data(self, conn, metric, operator, threshold, start_time, end_time):
        if threshold is None:
            threshold = 80.0 if metric == "temperature" else 3.0

        conditions = [f"s.{metric} {operator} ?"]
        params = [threshold]
        if start_time:
            conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("s.timestamp <= ?")
            params.append(end_time)

        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT DISTINCT s.machine_id, m.machine_name, s.{metric} as val, s.timestamp, m.status
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            {where_clause}
            ORDER BY s.timestamp DESC
            LIMIT 20
        """
        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        unique_machines = sorted(list({f"{r['machine_id']} ({r['machine_name']})" for r in rows}))
        return {
            "success": True,
            "intent": "FILTER_DATA",
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "matching_machines": unique_machines,
            "records": rows
        }

    def _handle_get_status(self, conn, machine_id):
        if machine_id:
            sql = """
                SELECT m.machine_id, m.machine_name, m.location, m.machine_type, m.status, m.installation_date,
                       (SELECT temperature FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as latest_temp,
                       (SELECT vibration FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as latest_vib
                FROM machines m
                WHERE m.machine_id = ?
            """
            row = conn.execute(sql, (machine_id,)).fetchone()
            if not row:
                return {"success": True, "intent": "GET_STATUS", "found": False, "data": None}
            res = dict(row)
            return {"success": True, "intent": "GET_STATUS", "found": True, "machine_id": machine_id, "data": res}
        else:
            sql = """
                SELECT m.machine_id, m.machine_name, m.location, m.machine_type, m.status,
                       (SELECT temperature FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as latest_temp
                FROM machines m
                ORDER BY m.machine_id ASC
            """
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            return {"success": True, "intent": "GET_STATUS", "found": len(rows) > 0, "machines": rows}

    def _handle_get_trend(self, conn, machine_id, metric, start_time, end_time):
        target_machine = machine_id or "M02"
        conditions = ["s.machine_id = ?"]
        params = [target_machine]

        if start_time:
            conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("s.timestamp <= ?")
            params.append(end_time)

        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT s.timestamp, s.{metric} as val, m.machine_name
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            {where_clause}
            ORDER BY s.timestamp ASC
            LIMIT 60
        """
        rows = conn.execute(sql, tuple(params)).fetchall()
        points = [dict(r) for r in rows]
        m_name = points[0]["machine_name"] if points else target_machine

        direction = "STABLE"
        if len(points) >= 2:
            diff = points[-1]["val"] - points[0]["val"]
            if diff > 1.0:
                direction = "RISING"
            elif diff < -1.0:
                direction = "FALLING"

        return {
            "success": True,
            "intent": "GET_TREND",
            "machine_id": target_machine,
            "machine_name": m_name,
            "metric": metric,
            "direction": direction,
            "points": points,
            "chart_type": "line"
        }

    def _handle_get_production(self, conn, machine_id, today_str):
        if machine_id:
            sql = """
                SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
                FROM production p
                JOIN machines m ON p.machine_id = m.machine_id
                WHERE p.machine_id = ? AND p.production_date = ?
            """
            row = conn.execute(sql, (machine_id, today_str)).fetchone()
            if not row:
                # Fallback to latest recorded production day
                sql_fallback = """
                    SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
                    FROM production p
                    JOIN machines m ON p.machine_id = m.machine_id
                    WHERE p.machine_id = ?
                    ORDER BY p.production_date DESC LIMIT 1
                """
                row = conn.execute(sql_fallback, (machine_id,)).fetchone()
            
            res = dict(row) if row else None
            return {
                "success": True,
                "intent": "GET_PRODUCTION",
                "found": bool(res),
                "machine_id": machine_id,
                "machine_name": res["machine_name"] if res else machine_id,
                "units_produced": res["units_produced"] if res else 0,
                "defective_units": res["defective_units"] if res else 0,
                "date": res["production_date"] if res else today_str
            }
        else:
            # Overview of all machines today
            sql = """
                SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
                FROM production p
                JOIN machines m ON p.machine_id = m.machine_id
                WHERE p.production_date = ?
                ORDER BY p.units_produced DESC
            """
            rows = [dict(r) for r in conn.execute(sql, (today_str,)).fetchall()]
            return {"success": True, "intent": "GET_PRODUCTION", "found": len(rows) > 0, "production_list": rows, "chart_type": "bar"}

    def _handle_get_max_production(self, conn, today_str):
        sql = """
            SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
            FROM production p
            JOIN machines m ON p.machine_id = m.machine_id
            WHERE p.production_date = ?
            ORDER BY p.units_produced DESC
            LIMIT 1
        """
        row = conn.execute(sql, (today_str,)).fetchone()
        if not row:
            # Fallback to latest date
            row = conn.execute("""
                SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
                FROM production p
                JOIN machines m ON p.machine_id = m.machine_id
                ORDER BY p.production_date DESC, p.units_produced DESC
                LIMIT 1
            """).fetchone()

        if not row:
            return {"success": True, "intent": "GET_MAX_PRODUCTION", "found": False}

        res = dict(row)
        return {
            "success": True,
            "intent": "GET_MAX_PRODUCTION",
            "found": True,
            "machine_id": res["machine_id"],
            "machine_name": res["machine_name"],
            "units_produced": res["units_produced"],
            "defective_units": res["defective_units"],
            "date": res["production_date"]
        }

    def _handle_get_defects(self, conn, machine_id, today_str):
        target = machine_id or "M03"
        sql = """
            SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date,
                   ROUND(p.defective_units * 100.0 / MAX(1, p.units_produced), 2) as defect_rate
            FROM production p
            JOIN machines m ON p.machine_id = m.machine_id
            WHERE p.machine_id = ? AND p.production_date = ?
        """
        row = conn.execute(sql, (target, today_str)).fetchone()
        if not row:
            row = conn.execute("""
                SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date,
                       ROUND(p.defective_units * 100.0 / MAX(1, p.units_produced), 2) as defect_rate
                FROM production p
                JOIN machines m ON p.machine_id = m.machine_id
                WHERE p.machine_id = ?
                ORDER BY p.production_date DESC LIMIT 1
            """, (target,)).fetchone()

        if not row:
            return {"success": True, "intent": "GET_DEFECTS", "found": False}

        res = dict(row)
        return {
            "success": True,
            "intent": "GET_DEFECTS",
            "found": True,
            "machine_id": res["machine_id"],
            "machine_name": res["machine_name"],
            "defective_units": res["defective_units"],
            "units_produced": res["units_produced"],
            "defect_rate": res["defect_rate"],
            "date": res["production_date"]
        }

    def _handle_compare_production(self, conn, machines, today_str):
        if not machines or len(machines) < 2:
            machines = ["M01", "M02"]

        placeholders = ",".join("?" for _ in machines)
        params = list(machines) + [today_str]
        sql = f"""
            SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
            FROM production p
            JOIN machines m ON p.machine_id = m.machine_id
            WHERE p.machine_id IN ({placeholders}) AND p.production_date = ?
            ORDER BY p.units_produced DESC
        """
        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        
        # If today not yet populated, fallback to latest common date
        if not rows:
            params = list(machines)
            sql_fallback = f"""
                SELECT p.machine_id, m.machine_name, p.units_produced, p.defective_units, p.production_date
                FROM production p
                JOIN machines m ON p.machine_id = m.machine_id
                WHERE p.machine_id IN ({placeholders})
                ORDER BY p.production_date DESC
                LIMIT {len(machines)}
            """
            rows = [dict(r) for r in conn.execute(sql_fallback, tuple(params)).fetchall()]

        return {
            "success": True,
            "intent": "COMPARE_PRODUCTION",
            "machines": machines,
            "comparison": rows,
            "chart_type": "bar"
        }

    def _handle_compare_sensor(self, conn, machines, metric, start_time, end_time):
        if not machines or len(machines) < 2:
            machines = ["M01", "M02"]

        placeholders = ",".join("?" for _ in machines)
        params = list(machines)

        time_conditions = []
        if start_time:
            time_conditions.append("s.timestamp >= ?")
            params.append(start_time)
        if end_time:
            time_conditions.append("s.timestamp <= ?")
            params.append(end_time)

        time_sql = (" AND " + " AND ".join(time_conditions)) if time_conditions else ""
        sql = f"""
            SELECT s.machine_id, m.machine_name,
                   ROUND(AVG(s.{metric}), 2) as avg_val,
                   ROUND(MAX(s.{metric}), 2) as max_val,
                   ROUND(MIN(s.{metric}), 2) as min_val,
                   COUNT(*) as sample_count
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            WHERE s.machine_id IN ({placeholders}) {time_sql}
            GROUP BY s.machine_id
            ORDER BY s.machine_id ASC
        """
        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        return {
            "success": True,
            "intent": "COMPARE_SENSOR",
            "metric": metric,
            "machines": machines,
            "comparison": rows,
            "chart_type": "bar"
        }

    def _handle_get_maintenance_status(self, conn):
        sql = """
            SELECT m.maintenance_id, m.machine_id, mc.machine_name, mc.location,
                   m.issue, m.maintenance_type, m.maintenance_date, m.status
            FROM maintenance m
            JOIN machines mc ON m.machine_id = mc.machine_id
            WHERE m.status IN ('IN_PROGRESS', 'SCHEDULED')
            ORDER BY m.status ASC, m.maintenance_date DESC
        """
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return {
            "success": True,
            "intent": "GET_MAINTENANCE_STATUS",
            "found": len(rows) > 0,
            "count": len(rows),
            "records": rows
        }

    def _handle_get_last_maintenance(self, conn, machine_id):
        target = machine_id or "M05"
        sql = """
            SELECT m.maintenance_id, m.machine_id, mc.machine_name,
                   m.issue, m.maintenance_type, m.maintenance_date, m.status
            FROM maintenance m
            JOIN machines mc ON m.machine_id = mc.machine_id
            WHERE m.machine_id = ?
            ORDER BY m.maintenance_date DESC, m.maintenance_id DESC
            LIMIT 1
        """
        row = conn.execute(sql, (target,)).fetchone()
        if not row:
            return {"success": True, "intent": "GET_LAST_MAINTENANCE", "found": False, "machine_id": target}

        res = dict(row)
        return {
            "success": True,
            "intent": "GET_LAST_MAINTENANCE",
            "found": True,
            "machine_id": target,
            "machine_name": res["machine_name"],
            "issue": res["issue"],
            "maintenance_type": res["maintenance_type"],
            "date": res["maintenance_date"],
            "status": res["status"]
        }

    def _handle_anomaly_correlation(self, conn, today_str):
        # Correlated multi-table query: High temperature in sensor_readings + low production in production
        sql = """
            SELECT s.machine_id, m.machine_name, m.location,
                   ROUND(AVG(s.temperature), 2) as avg_temp,
                   p.units_produced, p.defective_units, m.status as machine_status
            FROM sensor_readings s
            JOIN machines m ON s.machine_id = m.machine_id
            JOIN production p ON m.machine_id = p.machine_id
            WHERE p.production_date = ?
            GROUP BY s.machine_id
            HAVING avg_temp > 65.0 AND p.units_produced < 450
            ORDER BY avg_temp DESC
        """
        rows = conn.execute(sql, (today_str,)).fetchall()
        if not rows:
            # Fallback to latest date
            sql_fallback = """
                SELECT s.machine_id, m.machine_name, m.location,
                       ROUND(AVG(s.temperature), 2) as avg_temp,
                       p.units_produced, p.defective_units, m.status as machine_status
                FROM sensor_readings s
                JOIN machines m ON s.machine_id = m.machine_id
                JOIN production p ON m.machine_id = p.machine_id
                GROUP BY s.machine_id
                HAVING avg_temp > 65.0 AND p.units_produced < 450
                ORDER BY avg_temp DESC
                LIMIT 3
            """
            rows = conn.execute(sql_fallback).fetchall()

        records = [dict(r) for r in rows]
        return {
            "success": True,
            "intent": "ANOMALY_CORRELATION",
            "found": len(records) > 0,
            "anomalies": records
        }

    def _handle_count_events(self, conn, status):
        status_val = status.upper() if status else "RUNNING"
        sql = "SELECT COUNT(*) as count FROM machines WHERE status = ?"
        row = conn.execute(sql, (status_val,)).fetchone()
        cnt = row["count"] if row else 0

        # Also get list of machines in that status
        sql_list = "SELECT machine_id, machine_name FROM machines WHERE status = ?"
        matching = [f"{r['machine_id']} ({r['machine_name']})" for r in conn.execute(sql_list, (status_val,)).fetchall()]

        return {
            "success": True,
            "intent": "COUNT_EVENTS",
            "count": cnt,
            "status": status_val,
            "matching_machines": matching
        }
