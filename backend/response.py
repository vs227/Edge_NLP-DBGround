from typing import Dict, Any, List

METRIC_LABELS = {
    "temperature": ("temperature", "°C"),
    "humidity": ("humidity", "%"),
    "energy": ("energy consumption", "kW"),
    "vibration": ("vibration level", "mm/s"),
}


def format_response(query_result: Dict[str, Any], structured_nlp: Dict[str, Any]) -> str:
    intent = structured_nlp.get("intent")
    metric = structured_nlp.get("metric", "temperature")
    m_label, m_unit = METRIC_LABELS.get(metric, (metric, ""))

    if intent == "OUT_OF_SCOPE" or not structured_nlp.get("is_valid"):
        return "I can only answer questions about factory operational, sensor, production, and maintenance data."

    if not query_result or not query_result.get("success"):
        return "I could not resolve that query against the factory database. Please specify a machine (e.g. M01-M10) or metric."

    # 1. GET_LATEST
    if intent == "GET_LATEST":
        if not query_result.get("found"):
            return f"No telemetry records found for {structured_nlp.get('machine_id', 'machines')}."
        mid = query_result.get("machine_id")
        if mid:
            val = query_result.get("value")
            name = query_result.get("machine_name", mid)
            ts = query_result.get("data", {}).get("timestamp", "recently")
            return f"The latest {m_label} of {mid} ({name}) is {val}{m_unit} (recorded at {ts})."
        else:
            rows = query_result.get("data", [])
            summary = ", ".join(f"{r['machine_id']}: {r.get(metric)}{m_unit}" for r in rows[:5])
            return f"Latest {m_label} readings: {summary}."

    # 2. GET_AVERAGE
    elif intent == "GET_AVERAGE":
        val = query_result.get("value")
        if val is None or not query_result.get("found"):
            return f"No records available to compute average {m_label}."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        target = f"{mid} ({name})" if mid else "all machines"
        time_desc = " over the requested period" if structured_nlp.get("start_time") else ""
        return f"The average {m_label} of {target}{time_desc} was {val}{m_unit} (computed across {query_result.get('sample_count')} readings)."

    # 3. GET_MAX
    elif intent == "GET_MAX":
        if not query_result.get("found"):
            return f"No maximum {m_label} recorded in telemetry."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        val = query_result.get("value")
        return f"{mid} ({name}) currently has the highest {m_label} at {val}{m_unit}."

    # 4. GET_MIN
    elif intent == "GET_MIN":
        if not query_result.get("found"):
            return f"No minimum {m_label} recorded in telemetry."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        val = query_result.get("value")
        return f"{mid} ({name}) has the lowest {m_label} at {val}{m_unit}."

    # 5. FILTER_DATA
    elif intent == "FILTER_DATA":
        matching = query_result.get("matching_machines", [])
        thresh = query_result.get("threshold")
        op = query_result.get("operator")
        if not matching:
            return f"No machines currently have {m_label} {op} {thresh}{m_unit}."
        return f"Machines with {m_label} {op} {thresh}{m_unit}: {', '.join(matching)}."

    # 6. GET_STATUS
    elif intent == "GET_STATUS":
        if not query_result.get("found"):
            return f"Could not find status for machine {structured_nlp.get('machine_id')}."
        if query_result.get("machine_id"):
            d = query_result.get("data", {})
            return f"{d.get('machine_id')} ({d.get('machine_name')}) is in {d.get('status')} status at {d.get('location')} (latest temp: {d.get('latest_temp')}°C, vibration: {d.get('latest_vib')} mm/s)."
        else:
            machines = query_result.get("machines", [])
            overview = ", ".join(f"{m['machine_id']}: {m['status']}" for m in machines[:6])
            return f"Machine status overview: {overview} (10 machines total)."

    # 7. GET_TREND
    elif intent == "GET_TREND":
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        direction = query_result.get("direction", "STABLE")
        pts = query_result.get("points", [])
        latest = pts[-1]["val"] if pts else "N/A"
        return f"{mid} ({name}) shows a {direction} {m_label} trend over the period (latest reading: {latest}{m_unit} across {len(pts)} data points)."

    # 8. GET_PRODUCTION
    elif intent == "GET_PRODUCTION":
        if not query_result.get("found"):
            return f"No production records found for {structured_nlp.get('machine_id', 'machines')}."
        mid = query_result.get("machine_id")
        if mid:
            name = query_result.get("machine_name", mid)
            units = query_result.get("units_produced")
            defects = query_result.get("defective_units")
            date = query_result.get("date")
            return f"{mid} ({name}) produced {units} units on {date} with {defects} defective units."
        else:
            plist = query_result.get("production_list", [])
            summary = ", ".join(f"{p['machine_id']}: {p['units_produced']} units" for p in plist[:5])
            return f"Production output today: {summary}."

    # 9. GET_MAX_PRODUCTION
    elif intent == "GET_MAX_PRODUCTION":
        if not query_result.get("found"):
            return "No production records available today."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        units = query_result.get("units_produced")
        defects = query_result.get("defective_units")
        date = query_result.get("date")
        return f"{mid} ({name}) produced the most units today ({date}) with {units} units produced ({defects} defects)."

    # 10. GET_DEFECTS
    elif intent == "GET_DEFECTS":
        if not query_result.get("found"):
            return "No defect data found for that machine."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        defects = query_result.get("defective_units")
        units = query_result.get("units_produced")
        rate = query_result.get("defect_rate")
        date = query_result.get("date")
        return f"{mid} ({name}) produced {defects} defective units out of {units} total on {date} (defect rate: {rate}%)."

    # 11. COMPARE_PRODUCTION
    elif intent == "COMPARE_PRODUCTION":
        comp = query_result.get("comparison", [])
        if not comp:
            return "Insufficient production records to compare."
        parts = [f"{c['machine_id']} ({c['machine_name']}: {c['units_produced']} units, {c['defective_units']} defects)" for c in comp]
        return "Production comparison: " + " versus ".join(parts) + "."

    # 12. COMPARE_SENSOR
    elif intent == "COMPARE_SENSOR":
        comp = query_result.get("comparison", [])
        if not comp:
            return "Insufficient sensor data to compare."
        parts = [f"{c['machine_id']} ({c['machine_name']} avg {m_label}: {c['avg_val']}{m_unit})" for c in comp]
        return "Sensor comparison: " + " versus ".join(parts) + "."

    # 13. GET_MAINTENANCE_STATUS
    elif intent == "GET_MAINTENANCE_STATUS":
        records = query_result.get("records", [])
        if not records:
            return "No machines are currently undergoing active or scheduled maintenance."
        summary = ", ".join(f"{r['machine_id']} ({r['machine_name']} - {r['issue']} [{r['status']}])" for r in records[:4])
        return f"Currently {len(records)} machine(s) with active maintenance: {summary}."

    # 14. GET_LAST_MAINTENANCE
    elif intent == "GET_LAST_MAINTENANCE":
        if not query_result.get("found"):
            return f"No historical maintenance records found for {structured_nlp.get('machine_id')}."
        mid = query_result.get("machine_id")
        name = query_result.get("machine_name", mid)
        date = query_result.get("date")
        issue = query_result.get("issue")
        st = query_result.get("status")
        m_type = query_result.get("maintenance_type")
        return f"{mid} ({name}) was last maintained on {date} (Type: {m_type}, Status: {st}, Issue: {issue})."

    # 15. ANOMALY_CORRELATION
    elif intent == "ANOMALY_CORRELATION":
        anomalies = query_result.get("anomalies", [])
        if not anomalies:
            return "No operational anomalies detected across machines today."
        parts = [f"{a['machine_id']} ({a['machine_name']}) at elevated temp {a['avg_temp']}°C with reduced output of {a['units_produced']} units ({a['defective_units']} defects)" for a in anomalies]
        return "Cross-table anomaly detected: " + "; ".join(parts) + "."

    # 16. COUNT_EVENTS
    elif intent == "COUNT_EVENTS":
        cnt = query_result.get("count", 0)
        st = query_result.get("status", "RUNNING")
        machines = query_result.get("matching_machines", [])
        machines_str = f" ({', '.join(machines)})" if machines else ""
        return f"There are currently {cnt} machine(s) in {st} status{machines_str}."

    return "Query executed successfully."
