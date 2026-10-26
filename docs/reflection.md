# Capstone Engineering Reflection & Retrospective

## 1. Key Architectural & Design Decisions

### A. The Two-Layer Detection Strategy (ML + Graph)
Single-model tabular classifiers (such as Random Forest or XGBoost) excel at evaluating behavioral anomalies for an isolated account (e.g., sudden velocity spike, 5x typical transaction amount). However, sophisticated fraud syndicates (mule rings, emulator bot farms) operate by opening dozens of clean accounts that each conduct individually modest transactions. 
By pairing **XGBoost (65% weight)** with a **NetworkX Entity Graph (35% weight)**, the platform detects:
- High-velocity behavioral anomalies via gradient boosted trees.
- Shared-device collusion, multi-account emulator farms, and common mule merchants via connected components and ego-networks.

### B. Prioritizing PR-AUC Over Accuracy
In a dataset with ~2% fraud prevalence, a model that predicts 0 for every transaction achieves 98% accuracy while being completely useless for fraud mitigation. Tracking **Precision-Recall AUC (Average Precision)** forces the model to rank true positives at the top of the probability distribution, enabling operational risk teams to set actionable alert thresholds.

### C. Zero Target Leakage Discipline
In financial fraud, features cannot look forward in time or peek at the ground truth label. We implemented `FeatureStoreState` with strict event-time progression: features for a transaction at $t_i$ are computed strictly using history $< t_i$. The label `is_fraud` is never accessed in feature engineering. Automated tests in `tests/test_features.py` verify this constraint.

---

## 2. Challenges Overcome During Implementation

1. **Host Environment Port Isolation**:
   - The user's system was already running active Docker containers for an AI Medical Imaging platform on ports `8000` (API) and `8501` (Frontend).
   - *Solution*: Configured AEGIS to use dedicated ports **`8010` (FastAPI)** and **`5173` (React Vite)**, preventing port binding errors and avoiding interference with existing projects.
2. **Python 3.14 Library Ecosystem Gaps**:
   - Python 3.14 is very new; packages like `evidently` failed due to legacy `pydantic.v1` metaclass deprecations, and PyTorch Geometric lacked prebuilt Windows wheels.
   - *Solution*: Implemented transparent, mathematically rigorous fallbacks—a two-sample Kolmogorov-Smirnov and Population Stability Index (PSI) drift engine via `scipy.stats`, and a NetworkX pure graph detector.
3. **Windows PowerShell cp1252 Encoding**:
   - Terminal print statements with unicode checkmarks (`✓`) triggered character map encoding errors on Windows cp1252 console.
   - *Solution*: Enforced clean ASCII logging markers (`[OK]`, `[INFO]`, `[WARN]`, `[ERROR]`).

---

## 3. What Worked Well & Future Improvements

- **What Worked Well**:
  - The in-memory `LocalQueueAdapter` allowed rapid asynchronous testing and full end-to-end replay demonstrations without spinning up Kafka.
  - The React Vite dark-mode dashboard provides a responsive, analyst-ready experience with real-time graph visualization and case resolution workflows.
  - MLflow SQLite database tracking provides auditability and reproducibility.
- **Future Improvements**:
  - Integrate Redis for multi-worker distributed feature caching.
  - Implement a Graph Convolutional Network (GCN) via PyG when precompiled wheels become available on Python 3.14.
  - Add SHAP (SHapley Additive exPlanations) values to the API response for regulatory feature explainability.
