# AEGIS: Real-Time Financial Fraud Detection Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-3.4+-eb6100.svg)](https://xgboost.readthedocs.io/)
[![React](https://img.shields.io/badge/React-18.0+-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.0+-646cff.svg)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/Tests-21%20Passed%20(100%25)-10b981.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **EDUCATIONAL CAPSTONE PROJECT**: This platform is an educational demonstration of imbalanced machine learning, graph analytics, and real-time streaming architectures. **All transaction records, account identifiers, device fingerprints, and merchant names are synthetic.** It contains NO real cardholder data and does not connect to live banking networks or real credit card processors.

---

## 1. System Architecture

AEGIS implements a multi-layer ensemble scoring architecture:
1. **Supervised ML Tier (65% weight)**: Fast histogram-based XGBoost classifier trained on 16 event-time behavioral features with class-weight compensation (`scale_pos_weight = 55.0`).
2. **Graph Syndicate Tier (35% weight)**: NetworkX bipartite entity graph analyzing multi-account device sharing, connected components, and emulator bot farms.
3. **Real-Time Streaming Layer**: Asynchronous event replay engine supporting both local zero-dependency in-memory queues and external Apache Kafka / Redpanda brokers.
4. **Analyst Dashboard**: Modern React + Vite cybersecurity interface featuring real-time stream monitoring, interactive graph visualization, and case management with audit logging.

```mermaid
graph TD
    subgraph Data Sources & Ingestion
        CSV[Sample Data CSV] -->|Chronological Replay| Producer[Transaction Replayer]
        Producer -->|Publish Event| StreamAdapter[Streaming Adapter]
    end

    subgraph Streaming Layer
        StreamAdapter -->|Default Fallback| Queue[Local Async Queue]
        StreamAdapter -.->|Opt-In Profile| Kafka[Kafka / Redpanda Broker]
    end

    subgraph Scoring Engine
        Queue -->|Consume Event| Engine[Fraud Inference Engine]
        Kafka -.->|Consume Event| Engine
        
        Engine -->|Stateful Event-Time Transform| FeatPipe[Feature Pipeline]
        FeatPipe -->|16 Features| XGB[XGBoost Classifier]
        
        Engine -->|Graph Ingestion & Traversal| NXGraph[NetworkX Entity Graph]
        NXGraph -->|Connected Components & Syndicate Scoring| GraphScore[Syndicate Detector]

        XGB -->|Supervised Probability (65%)| Blender[Score Blender]
        GraphScore -->|Graph Topology Risk (35%)| Blender
        Blender -->|Blended Score & Risk Tier| Decision[Decision Engine]
    end

    subgraph Case Management & Storage
        Decision -->|Trigger Alert| DB[(SQLite fraud_cases.db)]
        Engine -->|Parameters & Metrics| MLflow[(MLflow SQLite Tracking)]
    end

    subgraph Serving & Frontend
        FastAPI[FastAPI Scoring Service :8010] <--> Engine
        FastAPI <--> DB
        ReactUI[React + Vite Analyst Dashboard :5173] <-->|REST & Polling| FastAPI
    end
```

---

## 2. Key Features

- **Strict Zero Target Leakage**: Sequential event-time historical state computation; transaction $t_i$ strictly depends on transactions $< t_i$. Label column is never accessed during feature creation.
- **Sub-10ms Scoring Latency**: High-resolution measurement shows average inference latency of **6.2 ms** (P95: 9.4 ms) on standard CPU laptops.
- **Imbalanced Metric Focus**: Evaluated using **PR-AUC (0.9978)** and ROC-AUC (0.9999) rather than misleading raw accuracy.
- **Syndicate & Bot Farm Detection**: NetworkX bipartite graph discovers multi-account shared devices (e.g. Mule Syndicate #1 and Emulator Bot Farm #2).
- **Interactive Analyst Dashboard**: Dark-mode fintech UI with live stream monitor, interactive SVG graph visualizer, case review drawer with feedback actions, and data drift viewer.
- **Data Drift & Retraining**: Statistical 2-sample Kolmogorov-Smirnov test and Population Stability Index (PSI) with approval-gated retraining triggers.
- **Safe Port Isolation**: Runs on dedicated ports **`:8010`** (FastAPI) and **`:5173`** (Vite), completely avoiding collisions with existing Docker containers on ports 8000 and 8501.

---

## 3. Quickstart Guide (Local Development)

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### Step 2: Prepare Dataset & Train Model
```powershell
# 1. Generate 6,000 deterministic synthetic transactions (seed=42)
python scripts/prepare_data.py --count 6000

# 2. Verify schema and event monotonicity
python scripts/verify_data.py

# 3. Train imbalanced XGBoost model & log to MLflow
python scripts/train_model.py
```

### Step 3: Start the Backend API (:8010)
```powershell
uvicorn app.api.main:app --host 127.0.0.1 --port 8010 --reload
```
Interactive Swagger docs: **`http://127.0.0.1:8010/docs`**

### Step 4: Start the Analyst Dashboard (:5173)
In a second terminal:
```powershell
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 4. Run with Docker Compose

Build and launch both the backend API and frontend dashboard:
```powershell
docker compose up --build
```
- **Analyst Dashboard**: `http://localhost:5173`
- **FastAPI Scoring API**: `http://localhost:8010`
- **Health Check**: `http://localhost:8010/health`

To start with the optional Redpanda Kafka broker:
```powershell
docker compose --profile kafka up --build
```

---

## 5. Measured Test Evaluation Results

Evaluated on 900 held-out test transactions (ground truth fraud prevalence = 3.22%):

| Metric | Measured Value | Operational Context |
| :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | **0.9978** | Primary imbalanced ranking metric |
| **ROC-AUC** | **0.9999** | Receiver Operating Characteristic Area |
| **Precision (at t=0.50)** | **1.0000** | 28 / 28 generated alerts were true fraud |
| **Recall (at t=0.50)** | **0.9655** | 28 / 29 actual fraud cases caught |
| **F1 Score** | **0.9825** | Harmonic mean of precision and recall |
| **Inference Latency** | **6.2 ms (avg)** | Real-time scoring speed on CPU |
| **Training Duration** | **0.16 seconds** | Fast lightweight execution |

```
Confusion Matrix (Test Set, n=900):
  True Negatives (TN): 871    False Positives (FP): 0
  False Negatives (FN):  1    True Positives (TP): 28
```

---

## 6. Project Directory Structure

```
real-time-fraud-detection/
├── app/
│   ├── api/             # FastAPI routers, schemas, and CORS configuration
│   ├── ml/              # XGBoost inference engine and latency tracker
│   ├── features/        # Event-time feature pipeline and zero-leakage state
│   ├── graph/           # NetworkX fraud-ring and syndicate detector
│   ├── streaming/       # Async LocalQueueAdapter and transaction replayer
│   └── services/        # SQLite case persistence and statistical drift engine
├── frontend/            # React 18 + Vite dark-mode analyst dashboard
│   ├── src/             # App.jsx, components/GraphVisualizer.jsx, index.css
│   └── Dockerfile       # Nginx production container
├── data/                # sample_transactions.csv, fraud_cases.db, data README
├── configs/             # Settings module and Feast feature store definitions
├── artifacts/           # Trained model, feature names, MLflow SQLite DB
├── reports/             # Metrics JSON, evaluation report, drift report & charts
├── scripts/             # Data prep, verification, and model training CLI
├── tests/               # 21 automated pytest unit and integration tests
├── docs/                # Comprehensive architecture, data/model cards, API reference
├── presentation/        # 10-minute capstone presentation slides outline
├── Dockerfile           # Multi-stage CPU-friendly backend container
├── compose.yaml         # Docker Compose orchestration with Kafka profile
└── requirements.txt     # Pinned Python dependencies
```

---

## 7. Automated Test Suite

Run the complete test suite:
```powershell
python -m pytest tests/ -v
```
**Results**:
- `tests/test_data.py`: 3 passed
- `tests/test_features.py`: 3 passed
- `tests/test_model.py`: 3 passed
- `tests/test_graph.py`: 3 passed
- `tests/test_api.py`: 4 passed
- `tests/test_streaming.py`: 2 passed
- `tests/test_drift.py`: 3 passed
- **Total: 21 passed, 0 failed in 4.02 seconds (100% PASS)**

---

## 8. Documentation Index

- [Architecture & Mermaid Diagrams](docs/architecture.md)
- [Dataset Card & Provenance](docs/data_card.md)
- [Model Card & Performance Trade-offs](docs/model_card.md)
- [API Reference & Schema Specification](docs/api.md)
- [Deployment & Operations Guide](docs/deployment.md)
- [Testing & Quality Assurance Report](docs/testing.md)
- [Known Limitations & Roadmap](docs/limitations.md)
- [Engineering Reflection & Retrospective](docs/reflection.md)
- [Requirements Traceability Matrix](docs/requirements_traceability.md)
- [Presentation Outline (10-Minute Slide Deck)](presentation/slides.md)
- [Final Verification Report](reports/final_verification.md)
