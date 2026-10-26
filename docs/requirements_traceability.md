# Requirements Traceability Matrix

This document maps all capstone requirements to specific code implementations, automated tests, and generated artifacts.

| Phase / Requirement | User Requirement Summary | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase A: Data Prep** | Obtain or generate lightweight, reproducible synthetic dataset with fraud rings & class imbalance (<25 MB). | `scripts/prepare_data.py`, `scripts/verify_data.py`, `data/README.md` | `tests/test_data.py` | **100% Complete & Verified** |
| **Phase B: Features** | Event-time features: velocity, amount ratio, new device/location, cold-start fallback, zero target leakage. | `app/features/pipeline.py` | `tests/test_features.py` | **100% Complete & Verified** |
| **Phase C: ML Model** | Train imbalanced XGBoost (with scikit-learn fallback), time-based split, PR-AUC evaluation, save artifacts. | `scripts/train_model.py`, `app/ml/engine.py` | `tests/test_model.py` | **100% Complete & Verified** |
| **Phase D: Fraud Rings** | NetworkX entity graph (Accounts, Devices, Merchants), connected components, syndicate score, score blending. | `app/graph/detector.py` | `tests/test_graph.py` | **100% Complete & Verified** |
| **Phase E: MLflow & Feast** | Local MLflow tracking of parameters, metrics, artifacts; local Feast feature store configuration. | `configs/settings.py`, `configs/feast/` | `scripts/train_model.py` | **100% Complete & Verified** |
| **Phase F: Streaming & API** | Transaction replayer, Kafka-compatible Local Queue Adapter, FastAPI scoring service (`/health`, `/ready`, `/score`, `/alerts`, `/metrics`). | `app/streaming/adapter.py`, `app/streaming/replayer.py`, `app/api/main.py` | `tests/test_api.py`, `tests/test_streaming.py` | **100% Complete & Verified** |
| **Phase G: Analyst UI** | React + Vite dashboard with live feed, case status management, analyst feedback, graph visualizer, metrics. | `frontend/src/App.jsx`, `frontend/src/components/GraphVisualizer.jsx` | `npm run build` | **100% Complete & Verified** |
| **Phase H: Data Drift** | Reference vs Current drift report, KS-test, PSI score, approval-gated retraining trigger. | `app/services/drift.py` | `tests/test_drift.py` | **100% Complete & Verified** |
| **Phase I: Docker** | Multi-stage Dockerfile, `compose.yaml`, `.dockerignore`, `.env.example`, non-colliding ports (`:8010`, `:5173`). | `Dockerfile`, `frontend/Dockerfile`, `compose.yaml` | `docker compose config` | **100% Complete & Verified** |
| **Phase J: Testing & QA** | Meaningful pytest test suite covering all tiers; report pass/fail status. | `tests/` (7 test modules, 21 test cases) | `pytest` (21 passed) | **100% Complete & Verified** |
| **Phase K: Documentation** | Architecture, data card, model card, API, deployment, limitations, reflection, slides, final report. | `docs/`, `presentation/slides.md`, `reports/final_verification.md`, `README.md` | Markdown review | **100% Complete & Verified** |
