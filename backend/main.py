import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from database import initialize_database, get_connection, get_database_stats
from nlp import NLPEngine
from query_engine import QueryEngine
from response import format_response

initialize_database()
nlp_engine = NLPEngine()
query_engine = QueryEngine()


class EdgeAPIHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(204)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._set_cors_headers(200)
            payload = {
                "status": "healthy",
                "device": "Redmi Y2 (ARMv7)",
                "engine": "EdgeNLP 2.0",
                "model": "TF-IDF + Logistic Regression (17 Intents)",
                "database": "SQLite Relational (4 Tables)"
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        elif path == "/status":
            self._set_cors_headers(200)
            conn = get_connection()
            sql = """
                SELECT m.machine_id, m.machine_name, m.location, m.machine_type, m.status,
                       (SELECT temperature FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as temperature,
                       (SELECT vibration FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as vibration,
                       (SELECT energy FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as energy,
                       (SELECT timestamp FROM sensor_readings WHERE machine_id = m.machine_id ORDER BY timestamp DESC LIMIT 1) as timestamp
                FROM machines m
                ORDER BY m.machine_id ASC
            """
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            conn.close()
            self.wfile.write(json.dumps({"machines": rows}, ensure_ascii=False).encode("utf-8"))

        elif path == "/data":
            self._set_cors_headers(200)
            query_params = parse_qs(parsed.query)
            limit = int(query_params.get("limit", ["20"])[0])
            machine = query_params.get("machine", [None])[0]

            conn = get_connection()
            if machine:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM sensor_readings WHERE machine_id = ? ORDER BY timestamp DESC, reading_id DESC LIMIT ?",
                    (machine.upper(), limit)
                ).fetchall()]
            else:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM sensor_readings ORDER BY timestamp DESC, reading_id DESC LIMIT ?",
                    (limit,)
                ).fetchall()]
            conn.close()
            self.wfile.write(json.dumps({"data": rows}, ensure_ascii=False).encode("utf-8"))

        elif path == "/database/info":
            self._set_cors_headers(200)
            conn = get_connection()
            stats = get_database_stats()
            machines = [dict(r) for r in conn.execute("SELECT * FROM machines ORDER BY machine_id").fetchall()]
            recent_readings = [dict(r) for r in conn.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC, reading_id DESC LIMIT 10").fetchall()]
            recent_production = [dict(r) for r in conn.execute("SELECT * FROM production ORDER BY production_date DESC, production_id DESC LIMIT 10").fetchall()]
            recent_maintenance = [dict(r) for r in conn.execute("SELECT * FROM maintenance ORDER BY maintenance_date DESC, maintenance_id DESC LIMIT 10").fetchall()]
            conn.close()

            payload = {
                "tables": stats,
                "machines": machines,
                "recent_readings": recent_readings,
                "recent_production": recent_production,
                "recent_maintenance": recent_maintenance
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/query":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            req = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._set_cors_headers(400)
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        query_text = req.get("query", "").strip()
        use_baseline = bool(req.get("baseline", False))

        if not query_text:
            self._set_cors_headers(400)
            self.wfile.write(b'{"error": "Query cannot be empty"}')
            return

        t0 = time.perf_counter()
        structured_nlp = nlp_engine.parse_query(query_text, use_baseline=use_baseline)
        t_nlp = time.perf_counter()

        sql_result = query_engine.execute_query(structured_nlp)
        t_sql = time.perf_counter()

        answer = format_response(sql_result, structured_nlp)
        t_end = time.perf_counter()

        total_latency = round((t_end - t0) * 1000, 2)
        nlp_latency = round((t_nlp - t0) * 1000, 2)
        sql_latency = round((t_sql - t_nlp) * 1000, 2)

        resp = {
            "query": query_text,
            "answer": answer,
            "intent": structured_nlp.get("intent"),
            "confidence": structured_nlp.get("confidence", 0.0),
            "metric": structured_nlp.get("metric"),
            "machine_id": structured_nlp.get("machine_id"),
            "latency_ms": total_latency,
            "nlp_latency_ms": nlp_latency,
            "sql_latency_ms": sql_latency,
            "chart_type": sql_result.get("chart_type") if isinstance(sql_result, dict) else None,
            "details": sql_result
        }

        self._set_cors_headers(200)
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_server(port: int = 8000):
    server = HTTPServer(("0.0.0.0", port), EdgeAPIHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_server(8000)
