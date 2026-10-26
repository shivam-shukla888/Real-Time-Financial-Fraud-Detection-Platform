# Capstone Presentation: Real-Time Financial Fraud Detection Platform

**Presenter**: Senior Machine Learning & Fraud Analytics Engineer  
**Duration**: 10 Minutes (Internship Capstone Presentation)  
**System Name**: AEGIS Fraud Intelligence Platform  

---

## Slide 1: The Problem — The Financial Fraud Battlefield (Minute 1)
- **The Challenge**: Card-not-present fraud, account takeovers (ATO), and multi-account bot farms generate billions in financial chargebacks annually.
- **The Operational Dilemma**:
  - In a financial stream where 98% of transactions are legitimate, naive models achieve 98% accuracy by flagging nothing.
  - Too many false positives drown fraud analysts in alerts (customer friction & alert fatigue).
  - False negatives directly create unrecoverable dollar losses.
- **Our Goal**: Build an end-to-end, sub-10ms real-time detection platform combining supervised gradient boosting with graph-based syndicate detection.

---

## Slide 2: End-to-End System Architecture (Minute 2)
- **Multi-Layer Ensemble**:
  1. **Event Streaming**: Asynchronous replay producer routing through a Kafka-compatible streaming adapter.
  2. **Event-Time Feature Engine**: Zero-leakage historical velocity and amount ratios.
  3. **Supervised ML Tier (65% weight)**: XGBoost histogram classifier handling 55:1 class imbalance.
  4. **Graph Syndicate Tier (35% weight)**: NetworkX entity graph detecting connected components and emulator bot farms.
  5. **Case Management**: SQLite persistence storing alerts and analyst audit trails.
  6. **Analyst Dashboard**: React + Vite dark-mode cybersecurity UI with live feed and graph visualizer.

---

## Slide 3: Dataset Provenance & Synthetic Disclaimer (Minute 3)
- **Safety First**: Generated a deterministic 6,000-transaction synthetic dataset (`data/sample_transactions.csv`) using random seed 42.
- **Prevalence**: 5,869 legitimate transactions (97.82%) vs. 131 fraud events (2.18%).
- **Embedded Typologies**:
  - Mule Syndicate Ring #1 (5 accounts, 2 shared devices funneling wire transfers).
  - Emulator Bot Farm #2 (4 accounts on a single virtual device executing crypto swap bursts).
- **Ethics**: No real bank credentials, PII, or card numbers are processed.

---

## Slide 4: Feature Engineering & Zero Target Leakage (Minute 4)
- **16 Engineered Features**:
  - Velocity counts: `txn_count_1h`, `txn_count_24h`, `txn_count_7d`
  - Spending sums: `amount_sum_1h`, `amount_sum_24h`
  - Ratio: `amount_to_hist_avg_ratio`
  - Behavioral anomalies: `is_new_device`, `is_new_location`, `device_account_count`
  - Temporal: `hour_of_day`, `day_of_week`, `is_night`, `is_weekend`
- **Zero Leakage Rule**: Features for transaction $t_i$ strictly depend on history $< t_i$. The ground truth label `is_fraud` is never accessed.
- **Cold-Start Resilience**: Robust default priors for first-time customer transactions.

---

## Slide 5: Supervised Model & Imbalanced Training (Minute 5)
- **Time-Based Partitioning**:
  - Train: 70% (4,200 records, 75 fraud events)
  - Validation: 15% (900 records, 27 fraud events)
  - Held-out Test: 15% (900 records, 29 fraud events)
- **Imbalance Strategy**: Dynamic `scale_pos_weight = 55.0` inside XGBoost. No SMOTE before split.
- **Training Time**: **0.16 seconds** on CPU.
- **Experiment Tracking**: Integrated with local MLflow SQLite backend (`artifacts/mlflow.db`).

---

## Slide 6: NetworkX Fraud Ring & Syndicate Detection (Minute 6)
- **Why Graphs Matter**: Fraudsters deliberately keep individual transactions small to fly under simple amount thresholds.
- **Bipartite Entity Modeling**:
  - Nodes: Accounts, Devices, Merchants, Locations.
  - Edges: Usage frequency and transaction volume.
- **Connected Components**:
  - Detects multi-account clusters sharing identical devices or emulator signatures.
  - Escalates risk score when 4+ accounts share a single hardware footprint.
  - High-risk override: known emulator signatures instantly trigger CRITICAL alerts.

---

## Slide 7: Streaming & Real-Time FastAPI Scoring (Minute 7)
- **Latency Benchmarks**:
  - Average Real-Time Scoring Latency: **6.2 ms** (measured via `time.perf_counter()`).
  - P95 Latency: **9.4 ms** (CPU-only laptop).
- **API Endpoints**:
  - `POST /score`: Real-time feature extraction + XGBoost + NetworkX scoring.
  - `GET /alerts`: Filterable case investigation queue.
  - `POST /alerts/{id}/feedback`: Analyst status updates and audit logs.
  - `POST /replay/start` & `stop`: Interactive stream replay.
- **Streaming Adapter**: Seamless dual-mode support for in-memory async queues and external Kafka brokers.

---

## Slide 8: Analyst Dashboard & Live Demo Walkthrough (Minute 8)
- **UI Highlights**:
  - Real-time streaming transaction monitor with instant risk meter.
  - Case investigation drawer with resolution actions (`CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `CLOSED`).
  - Interactive SVG Syndicate Graph Visualizer with node filtering and degree inspection.
  - Precision-Recall curve viewer and operational trade-off breakdown.
  - Data drift monitoring tab with KS-test statistics and retraining triggers.

---

## Slide 9: Measured Results & Confusion Matrix (Minute 9)
- **Evaluation on Held-out 900 Test Transactions**:
  - **PR-AUC (Average Precision)**: **0.9978**
  - **ROC-AUC**: **0.9999**
  - **Precision (at t=0.50)**: **100.0%** (28/28 alerts confirmed fraud)
  - **Recall (at t=0.50)**: **96.55%** (28/29 fraud cases caught)
  - **F1 Score**: **0.9825**
- **Test Confusion Matrix**:
  - True Negatives: **871**
  - False Positives: **0** (Zero customer friction / false alarms)
  - False Negatives: **1**
  - True Positives: **28**

---

## Slide 10: Reflection, Limitations & Next Steps (Minute 10)
- **Engineering Overcomes**:
  - Python 3.14 compatibility handled via transparent statistical drift fallbacks (KS-test + PSI).
  - Port isolation: runs cleanly on ports `:8010` and `:5173` without port conflicts.
- **Quality Assurance**: 21/21 automated pytest tests passed in 4.02s.
- **Future Roadmap**:
  - Distributed Redis feature store for multi-region active-active clusters.
  - Graph Neural Network (GNN / GraphSAGE) upgrade once PyG wheels compile on Python 3.14.
  - SHAP value explanations attached to alert payloads.
