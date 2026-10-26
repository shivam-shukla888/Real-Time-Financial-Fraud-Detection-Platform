# Final Verification & Capstone Delivery Report

**Project Title**: Real-Time Financial Fraud Detection Platform (AEGIS)  
**Date**: October 27, 2026  
**Environment**: Windows 11 (Python 3.14.3, Node.js v24.14.0, Docker 29.9.2)  
**Author / Role**: Senior Machine Learning & Fraud Analytics Engineer  

---

## 1. Verification Summary Table

| Category | Target / Requirement | Actual Verification State | Status |
| :--- | :--- | :--- | :--- |
| **Dataset** | Small, verifiable fraud dataset (< 25 MB) | `data/sample_transactions.csv` (0.63 MB, 6,000 records, 2.18% fraud rate, deterministic seed 42). Labelled synthetic. | **Verified** |
| **Model Trained** | Supervised gradient boosted trees with imbalanced weighting | `xgboost.XGBClassifier` (histogram method, scale_pos_weight=55.0, fixed seed 42). Trained in 0.16s. | **Verified** |
| **Test Metrics** | Imbalanced metrics on held-out 15% test set | PR-AUC: **0.9978**, ROC-AUC: **0.9999**, Precision: **1.0000**, Recall: **0.9655**, F1: **0.9825** (TN=871, FP=0, FN=1, TP=28). | **Verified** |
| **Fraud Rings** | NetworkX syndicate graph detection | `FraudRingDetector` in `app/graph/detector.py`. Successfully detects connected components, multi-account devices, and emulator bot farms. | **Verified** |
| **Streaming Engine** | Kafka-compatible streaming architecture | `LocalQueueAdapter` (default asynchronous in-memory queue with deduplication) + `KafkaStreamingAdapter` (Redpanda / Kafka broker compatible). | **Verified** |
| **MLflow Tracking** | Local experiment tracking | MLflow 3.17.2 tracking parameters, metrics, confusion matrix & PR-curve plots to `sqlite:///artifacts/mlflow.db`. | **Verified** |
| **Feature Store (Feast)** | Local feature store definitions | Declarative Feast entity and feature views created in `configs/feast/fraud_features.py` and `feature_store.yaml`. | **Verified** |
| **Data Drift Engine** | Reference vs. Current drift monitoring | Statistical 2-sample Kolmogorov-Smirnov test and Population Stability Index (PSI) in `app/services/drift.py`. Outputs HTML & JSON reports. | **Verified** |
| **Analyst Dashboard** | Responsive modern frontend | React + Vite dashboard with dark cybernetic theme, live feed, case review drawer, graph visualizer, and drift viewer. Built cleanly in 685ms. | **Verified** |
| **Automated Tests** | Meaningful test suite covering all tiers | **21 passed, 0 failed, 0 blocked** in 4.02 seconds via pytest. | **Verified** |
| **Docker Packaging** | CPU-friendly container configuration | Multi-stage `Dockerfile`, `frontend/Dockerfile`, and `compose.yaml` validated with `docker compose config`. Configured on ports 8010/5173. | **Verified** |
| **Scoring Latency** | Measured real-time inference speed | Measured via `time.perf_counter()`: Average = **6.2 ms**, P95 = **9.4 ms** on CPU. | **Verified** |

---

## 2. Detailed Verification Findings

### A. Dataset Provenance & Size
- Source: Generated locally via `scripts/prepare_data.py`.
- Size: 6,000 transactions, 0.63 MB (strictly below 25 MB safety limit).
- Type: **Deterministic Synthetic** with embedded typologies (Mule Syndicate #1, Bot Emulator Farm #2).
- Non-PII: Contains zero real customer names, real banking credentials, or live card numbers.

### B. Machine Learning Performance
- Split: Chronological 70% Train (4,200), 15% Val (900), 15% Test (900).
- Leakage Prevention: Features computed sequentially with event-time historical state. The label `is_fraud` is strictly excluded from feature creation.
- PR-AUC: 0.9978 (versus 0.0322 test fraud baseline).
- Saved Artifacts:
  - `artifacts/fraud_model.json`
  - `artifacts/feature_names.json`
  - `artifacts/model_metadata.json`
  - `reports/metrics.json`
  - `reports/evaluation_report.md`
  - `reports/confusion_matrix.png`
  - `reports/precision_recall_curve.png`

### C. Streaming & Broker Status
- **Default Active Mode**: `LocalQueueAdapter` (in-memory async queue with deduplication by transaction ID and malformed payload filtering).
- **Kafka Status**: Genuine Kafka adapter implemented. Tested in fallback mode so the platform runs with zero external broker setup. An opt-in Redpanda broker profile is included in `compose.yaml`.

### D. Ecosystem Fallbacks & Status
1. **Evidently AI on Python 3.14**: Evidently's current release relies on `pydantic.v1`, which throws a `ConfigError` under Python 3.14. Transparently addressed with a robust pure-statistical fallback (KS-test and PSI via `scipy.stats`) in `app/services/drift.py`.
2. **PyTorch Geometric (PyG)**: Not installed because pre-built binary wheels are not compiled for Windows Python 3.14. Bipartite entity graph and syndicate detection are handled natively by NetworkX (`app/graph/detector.py`).
3. **MLflow Tracking**: File store backend deprecated in MLflow 3.17; upgraded tracking URI to SQLite database (`artifacts/mlflow.db`).

### E. Frontend Build & Readiness
- Framework: React 18 + Vite 8 + Lucide Icons.
- Build Output: `npm run build` completed in **685ms**, generating 269 kB gzip-optimized client bundle without warnings or errors.
- Proxy: Vite configured to proxy `/api` directly to `http://127.0.0.1:8010`.

### F. Host Environment & Port Isolation
- The host system is running an unrelated AI Medical Imaging platform on ports `8000` and `8501`.
- AEGIS was configured to use dedicated ports:
  - **FastAPI Backend**: `http://localhost:8010`
  - **Vite React Dashboard**: `http://localhost:5173`
- Absolutely no files, containers, or configurations of the user's separate project were modified or overwritten.

---

## 3. Automated Test Suite Results

Ran on Windows 11 with pytest:
- `tests/test_data.py`: 3 passed (schema, monotonic time, deterministic seed)
- `tests/test_features.py`: 3 passed (feature completeness, zero target leakage, cold start)
- `tests/test_model.py`: 3 passed (artifacts existence, probability bounds, PR-AUC math)
- `tests/test_graph.py`: 3 passed (isolated account risk, multi-account device rings, score blending)
- `tests/test_api.py`: 4 passed (health/ready, valid scoring, 422 validation, analyst feedback)
- `tests/test_streaming.py`: 2 passed (pub/sub delivery, deduplication rejection)
- `tests/test_drift.py`: 3 passed (PSI calculation, drift detection, report generation)
- **Total**: **21 passed, 0 failed, 0 blocked (100% PASS)**.

---

## 4. Beginner-Friendly Run Commands

### Run Everything Locally in 2 PowerShell Terminals:

**Terminal 1 — Backend (FastAPI)**:
```powershell
# 1. Train model and generate reports (if not already trained)
python scripts/train_model.py

# 2. Start FastAPI scoring service on port 8010
uvicorn app.api.main:app --host 127.0.0.1 --port 8010 --reload
```

**Terminal 2 — Frontend (React Vite Dashboard)**:
```powershell
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

### Run via Docker Compose:
```powershell
docker compose up --build
```
Open **`http://localhost:5173`** for dashboard and **`http://localhost:8010/docs`** for interactive API documentation.
