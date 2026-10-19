import re
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from difflib import get_close_matches
from time_parser import parse_time_range

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "intent_model" / "model.json"

METRIC_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "energy": "kW",
    "vibration": "mm/s",
    "units_produced": "units",
    "defective_units": "units"
}

METRIC_GAZETTEER = {
    "temperature": ["temperature", "temp", "heat", "hot", "thermal", "degrees", "celsius", "temperatures"],
    "humidity": ["humidity", "humid", "moisture", "dampness"],
    "energy": ["energy", "power", "electricity", "kw", "kwh", "consumption", "wattage", "watt"],
    "vibration": ["vibration", "vibrate", "vibrations", "shake", "shaking", "oscillation"],
}

FLAT_METRIC_KEYWORDS = {}
for metric_name, aliases in METRIC_GAZETTEER.items():
    for alias in aliases:
        FLAT_METRIC_KEYWORDS[alias] = metric_name

STATUS_KEYWORDS = {
    "running": "RUNNING",
    "idle": "IDLE",
    "maintenance": "MAINTENANCE",
    "warning": "WARNING",
    "stopped": "IDLE",
    "active": "RUNNING"
}

COMMON_WORDS = {
    "what", "when", "which", "where", "how", "who", "with", "from", "that", 
    "this", "have", "been", "show", "tell", "give", "the", "for", "and", 
    "are", "last", "past", "were", "was", "does", "did", "machine", "machines", 
    "unit", "units", "device", "devices", "production", "maintenance", "today"
}


def normalize_query_typos(text: str) -> str:
    tokens = text.split()
    corrected = []
    for t in tokens:
        clean = re.sub(r'^[^\w]+|[^\w]+$', '', t.lower())
        if clean in COMMON_WORDS:
            corrected.append(t)
        elif clean in FLAT_METRIC_KEYWORDS:
            corrected.append(FLAT_METRIC_KEYWORDS[clean])
        elif len(clean) >= 5:
            matches = get_close_matches(clean, FLAT_METRIC_KEYWORDS.keys(), n=1, cutoff=0.80)
            if matches:
                corrected.append(FLAT_METRIC_KEYWORDS[matches[0]])
            else:
                corrected.append(t)
        else:
            corrected.append(t)
    return " ".join(corrected)


class RuleBasedBaseline:
    INTENT_KEYWORDS = {
        "ANOMALY_CORRELATION": ["high temperature and low production", "high temp and low production", "overheating and poor", "high heat and low"],
        "GET_LAST_MAINTENANCE": ["last maintained", "last maintenance", "last serviced", "last repaired", "previous maintenance"],
        "GET_MAINTENANCE_STATUS": ["under maintenance", "in maintenance", "undergoing maintenance", "being repaired", "active maintenance"],
        "COMPARE_PRODUCTION": ["compare production", "production comparison", "production vs", "compare output", "output comparison"],
        "GET_MAX_PRODUCTION": ["most units", "highest production", "max production", "top producing", "peak output", "maximum parts"],
        "GET_DEFECTS": ["defective", "defects", "defect count", "scrap", "faulty units", "bad units"],
        "GET_PRODUCTION": ["production", "units produced", "output", "parts made", "manufactured"],
        "GET_TREND": ["trend", "history", "graph", "pattern", "over time", "curve", "rising", "falling"],
        "COMPARE_SENSOR": ["compare", "difference", "versus", "vs"],
        "COUNT_EVENTS": ["how many machines", "count of machines", "number of machines", "total number of machines"],
        "FILTER_DATA": ["above", "greater than", "more than", "over", "below", "less than", "under", "exceeding"],
        "GET_MAX": ["highest", "maximum", "max", "peak", "most", "hottest", "warmest"],
        "GET_MIN": ["lowest", "minimum", "min", "least", "coldest", "coolest"],
        "GET_AVERAGE": ["average", "avg", "mean"],
        "GET_STATUS": ["status", "state", "health", "condition", "how is"],
        "GET_LATEST": ["latest", "current", "now", "present", "recent", "right now", "reading"],
    }

    def predict(self, text: str) -> Tuple[str, float]:
        t_lower = text.lower()
        for intent, kws in self.INTENT_KEYWORDS.items():
            for kw in kws:
                if kw in t_lower:
                    return intent, 0.85
        return "OUT_OF_SCOPE", 0.30


class MLIntentClassifier:
    def __init__(self, model_path: Path = None):
        path = model_path or MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.classes = data["classes"]
        self.vocabulary = data["vocabulary"]
        self.idf = data["idf"]
        self.weights = data["weights"]
        self.intercept = data["intercept"]

    def predict(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        tokens = re.findall(r'\b\w+\b', text.lower())
        ngrams = list(tokens)
        for i in range(len(tokens) - 1):
            ngrams.append(f"{tokens[i]} {tokens[i+1]}")

        tf = {}
        for g in ngrams:
            if g in self.vocabulary:
                idx = self.vocabulary[g]
                tf[idx] = tf.get(idx, 0) + 1

        if not tf:
            return "OUT_OF_SCOPE", 0.0, {}

        vec = {}
        sum_sq = 0.0
        for idx, count in tf.items():
            v = (1.0 + math.log(count)) * self.idf[idx]
            vec[idx] = v
            sum_sq += v * v

        norm = math.sqrt(sum_sq)
        for idx in vec:
            vec[idx] /= norm

        logits = []
        for c_idx in range(len(self.classes)):
            score = self.intercept[c_idx]
            w_row = self.weights[c_idx]
            for idx, val in vec.items():
                score += w_row[idx] * val
            logits.append(score)

        max_logit = max(logits)
        exps = [math.exp(l - max_logit) for l in logits]
        sum_exps = sum(exps)
        probs = [e / sum_exps for e in exps]

        best_idx = max(range(len(self.classes)), key=lambda i: probs[i])
        prob_dict = {self.classes[i]: round(probs[i], 4) for i in range(len(self.classes))}
        return self.classes[best_idx], probs[best_idx], prob_dict


class EntityExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        t_lower = text.lower()
        entities = {}

        # 1. Machine IDs (M01 - M10, Machine 1 - Machine 10)
        found_machines = []
        matches = re.findall(r'\bm(?:0?([1-9])|10)\b|(?:machine|unit|device)\s*#?\s*(?:0?([1-9])|10)\b', t_lower)
        for m in matches:
            num = m[0] or m[1]
            if num:
                mid = f"M{int(num):02d}"
                if mid not in found_machines:
                    found_machines.append(mid)

        entities["machines"] = found_machines
        entities["machine_id"] = found_machines[0] if len(found_machines) == 1 else (found_machines[0] if found_machines else None)

        # 2. Metric
        entities["metric"] = self._extract_metric(t_lower)

        # 3. Operator
        if re.search(r'\b(?:above|greater than|more than|over|exceeding|higher than|>)\b', t_lower):
            entities["operator"] = ">"
        elif re.search(r'\b(?:below|less than|under|lower than|<)\b', t_lower):
            entities["operator"] = "<"
        elif re.search(r'\b(?:equal to|at|=|==)\b', t_lower):
            entities["operator"] = "="
        else:
            entities["operator"] = ">"

        # 4. Threshold
        m_thresh = re.search(r'(?:above|greater than|over|>|<|below|exceeding)\s*(\d+(?:\.\d+)?)', t_lower)
        if not m_thresh:
            m_thresh = re.search(r'(\d+(?:\.\d+)?)\s*(?:degrees?|°c|°|c|kw|kwh|%|mm/s)', t_lower)

        if m_thresh:
            entities["threshold"] = float(m_thresh.group(1))

        # 5. Status
        for kw, status_val in STATUS_KEYWORDS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', t_lower):
                entities["status"] = status_val
                break

        return entities

    def _extract_metric(self, text: str) -> str:
        tokens = re.findall(r'\b\w+\b', text)
        for token in tokens:
            if token not in COMMON_WORDS and token in FLAT_METRIC_KEYWORDS:
                return FLAT_METRIC_KEYWORDS[token]

        if "power" in text or "kw" in text or "energy" in text:
            return "energy"
        if "shake" in text or "vibration" in text:
            return "vibration"
        if "moist" in text or "humidity" in text:
            return "humidity"

        return "temperature"


class NLPEngine:
    def __init__(self):
        self.ml_classifier = MLIntentClassifier()
        self.baseline_classifier = RuleBasedBaseline()
        self.entity_extractor = EntityExtractor()

    def parse_query(self, user_text: str, use_baseline: bool = False) -> Dict[str, Any]:
        if not user_text or not user_text.strip():
            return {
                "intent": "OUT_OF_SCOPE",
                "confidence": 0.0,
                "is_valid": False,
                "error": "Empty query"
            }

        normalized_text = normalize_query_typos(user_text)

        if use_baseline:
            intent, conf = self.baseline_classifier.predict(normalized_text)
            probs = {}
        else:
            intent, conf, probs = self.ml_classifier.predict(normalized_text)
            if conf < 0.38:
                base_intent, base_conf = self.baseline_classifier.predict(normalized_text)
                if base_conf >= 0.70:
                    intent, conf = base_intent, base_conf

        if intent == "OUT_OF_SCOPE" or conf < 0.30:
            return {
                "intent": "OUT_OF_SCOPE",
                "confidence": round(conf, 4),
                "is_valid": False,
                "raw_query": user_text,
                "probabilities": probs
            }

        entities = self.entity_extractor.extract(normalized_text)
        start_time, end_time = parse_time_range(user_text)

        return {
            "intent": intent,
            "confidence": round(conf, 4),
            "metric": entities.get("metric", "temperature"),
            "machine_id": entities.get("machine_id"),
            "machines": entities.get("machines", []),
            "operator": entities.get("operator", ">"),
            "threshold": entities.get("threshold"),
            "status": entities.get("status"),
            "start_time": start_time,
            "end_time": end_time,
            "is_valid": True,
            "raw_query": user_text
        }
