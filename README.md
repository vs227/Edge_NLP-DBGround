# EdgeNLP: Edge-Based NLP System for Natural Language Querying of Real-Time Operational Data

An edge computing Natural Language Processing (NLP) system running locally on an Android smartphone via Termux. EdgeNLP enables plant engineers and operators to query real-time industrial telemetry using conversational natural language without sending any data to external cloud LLM APIs.

---

## 1. System Architecture

```
User (Browser)
      ↓
React + Vite Frontend (Laptop)
      ↓ HTTP POST (JSON)
Android Edge Device (Termux, Port 8000)
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
│   ├── seed_data.py        # Seed data generator for all 4 tables
│   ├── simulator.py        # Real-time industrial telemetry generator (M01-M10)
│   ├── nlp.py              # Pure-Python TF-IDF + Logistic Regression & Slot Extractor
│   ├── query_engine.py     # Parameterized SQL query templates for all 17 intents
│   ├── time_parser.py      # Custom relative time expression parser
│   └── response.py         # Natural language answer generator
│
├── models/
│   └── intent_model/
│       └── model.json      # Trained weights, vocabulary, IDF, intercepts (zero C++ dependencies)
│
├── training/
│   ├── intents.csv         # Labeled industrial operational queries
│   └── train.py            # Model training & cross-validation exporter
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # ChatGPT-style chat interface with ER diagram modal
│   │   ├── App.css         # Plain CSS styling (no Tailwind)
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 3. Database Schema

EdgeNLP uses a relational SQLite database with 4 tables:

| Table | Description |
| :--- | :--- |
| `machines` | 10 machines (M01–M10) with name, location, type, status |
| `sensor_readings` | 6,000+ timestamped readings (temperature, humidity, energy, vibration) |
| `production` | 1,000+ production records (units produced, defective units) |
| `maintenance` | 100+ maintenance logs (issue, type, date, status) |

All tables are linked via `machine_id` foreign keys with proper indexes.

---

## 4. Supported Intents & Query Types

| Intent | Example Query |
| :--- | :--- |
| `GET_LATEST` | *"What is the latest temperature of M02?"* |
| `GET_AVERAGE` | *"Average temperature of M02 in the last 30 minutes"* |
| `GET_MAX` | *"Which machine has the highest temperature?"* |
| `GET_MIN` | *"Which machine has the lowest energy consumption?"* |
| `FILTER_DATA` | *"Show machines above 80 degrees"* |
| `COMPARE` | *"Compare production M01 vs M02"* |
| `GET_TREND` | *"Temperature trend M02"* |
| `GET_PRODUCTION` | *"Production of M03 today"* |
| `GET_PRODUCTION_MAX` | *"Highest production machine"* |
| `GET_DEFECTS` | *"How many defective units did M03 produce?"* |
| `GET_MAINTENANCE` | *"Which machines are currently under maintenance?"* |
| `GET_LAST_MAINTENANCE` | *"When was M05 last maintained?"* |
| `GET_ENERGY` | *"Show the energy consumption of M02 in the last hour"* |
| `CROSS_TABLE` | *"Which machine has high temperature and low production?"* |
| `OUT_OF_SCOPE` | *"Tell me tomorrow's weather"* |

---

## 5. Performance

- **On-Device NLP Inference Latency**: 2–12 ms
- **SQLite Query Latency**: 1–5 ms
- **Total End-to-End Latency**: 5–25 ms
- **Memory Footprint**: ~14 MB RSS
- **No cloud APIs, no LLMs, no C++ dependencies on device**

---

## 6. How to Run

### 1. On the Edge Device (Phone via Termux / SSH)
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
Open `http://localhost:3000` in your browser.
