# EdgeNLP: Edge-Based NLP System for Natural Language Querying of Real-Time Operational Data

An edge computing Natural Language Processing (NLP) system running locally on a **Redmi Y2** Android smartphone via Termux. EdgeNLP enables plant engineers and operators to query real-time industrial telemetry using conversational natural language without sending any data to external cloud LLM APIs.

---

## 1. System Architecture

```
User (Browser)
      ↓
React + Vite Dashboard (Laptop)
      ↓ HTTP POST (JSON)
Redmi Y2 Android Edge Device (Termux, Port 8000)
      ↓
Pure-Python NLP Engine (TF-IDF + Logistic Regression Inference)
      ↓
Intent Classification + Entity & Slot Extraction + Relative Time Parser
      ↓
Safe Parameterized SQL Template Mapping
      ↓
SQLite Engine (WAL Mode, Local Database)
      ↓
Natural Language Response Formatter
      ↓
User
```

---

## 2. Project Directory Structure

```
EdgeNLP/
│
├── backend/
│   ├── main.py             # REST API server (HTTP, CORS, latency profiling)
│   ├── database.py         # SQLite connection manager with WAL mode and indexing
│   ├── simulator.py        # Real-time industrial telemetry generator (M01-M05)
│   ├── nlp.py              # Pure-Python TF-IDF + Logistic Regression & Slot Extractor
│   ├── query_engine.py     # Parameterized SQL query templates for all 10 intents
│   ├── time_parser.py      # Custom relative time expression parser
│   └── response.py         # Natural language answer generator
│
├── models/
│   └── intent_model/
│       └── model.json      # Trained weights, vocabulary, IDF, intercepts (zero C++ dependencies)
│
├── data/
│   └── edgenlp.db          # SQLite operational database with WAL mode
│
├── training/
│   ├── intents.csv         # 220 labeled industrial operational queries
│   └── train.py            # Model training & cross-validation exporter
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Query input, live telemetry cards, Recharts trend graph
│   │   ├── App.css         # Plain CSS styling (no Tailwind)
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── tests/
│   └── test_edgenlp.py     # End-to-end integration and benchmark test suite
│
├── requirements.txt
└── README.md
```

---

## 3. Supported Intents & Query Types

| Intent | Description | Example Query |
| :--- | :--- | :--- |
| `GET_LATEST` | Most recent telemetry reading | *"What is the latest temperature of machine 2?"* |
| `GET_AVERAGE` | Aggregated mean over a time window | *"What was the average temperature of machine 2 in the last 30 minutes?"* |
| `GET_MAX` | Peak value across machines / time | *"Which machine has the highest temperature?"* |
| `GET_MIN` | Minimum value across machines | *"Which machine has the lowest energy consumption?"* |
| `GET_STATUS` | Current operating state | *"What is the status of machine 3?"* |
| `FILTER_DATA` | Threshold-based filtering | *"Show machines above 70 degrees."* |
| `COMPARE` | Side-by-side metric comparison | *"Compare the temperature of machine 1 and machine 2."* |
| `COUNT_EVENTS` | Count of matching events/states | *"How many machines are currently in warning status?"* |
| `THRESHOLD_ALERT`| Active alert detection | *"Any machine threshold alert right now?"* |
| `GET_TREND` | Telemetry progression over time | *"Show temperature trend of machine 2 for the last hour."* |
| `OUT_OF_SCOPE` | Guardrail for non-industrial inputs | *"Tell me tomorrow's weather."* |

---

## 4. Hardware & Measured Performance Benchmarks

### Test Environment
- **Edge Device**: Xiaomi Redmi Y2 (Android 9, ARMv7 32-bit `armv7l`)
- **Runtime**: Termux with Python 3.14.6
- **Database**: SQLite 3 with WAL (`Write-Ahead Logging`)

### Actual Measured Metrics
- **Model Training Cross-Validation Accuracy**: `86.4%` (5-fold CV)
- **End-to-End Query Benchmark Accuracy**: `100.0%` (10/10 standard test queries)
- **On-Device NLP Inference Latency**: `2.3ms – 11.6ms`
- **SQLite Query Latency**: `1.4ms – 3.8ms`
- **Total On-Device Processing Latency**: `5.4ms – 25.9ms` (Average: `13.15ms`)
- **Memory Footprint (RSS)**: `14.3 MB` (Resident Set Size)
- **CPU Utilization during Query**: `~2.3%`

---

## 5. How to Run

### 1. On the Redmi Y2 (Phone via Termux / SSH)
```bash
# Start backend API server
cd ~/EdgeNLP/backend
~/EdgeNLP/.venv/bin/python main.py

# (Optional) Run continuous telemetry simulator in background
~/EdgeNLP/.venv/bin/python simulator.py &
```

### 2. On the Laptop (React UI)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser. Telemetry will automatically stream from the Redmi Y2.

### 3. Running Automated Tests
```bash
python tests/test_edgenlp.py
```
# Edge_NLP-DBGround
