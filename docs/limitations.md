# Known Limitations, Constraints & Production Roadmap

## 1. Synthetic Data & Behavioral Realism

1. **Synthetic Data Boundaries**:
   - The dataset was generated deterministically to provide clear pedagogical value and test repeatability.
   - Real-world financial fraud features sophisticated adversarial mutation: fraudsters continuously rotate proxies, spoof device fingerprints, and launder funds through complex multi-hop mule networks.
   - **Metrics Disclaimer**: The 0.9978 PR-AUC achieved on this synthetic benchmark demonstrates algorithm mechanics and feature relevance, but should not be taken as an expected real-world banking fraud catch rate.

---

## 2. Python 3.14 Environment & Ecosystem Constraints

During local verification on **Python 3.14.3 (Windows)**, several ecosystem constraints were identified and handled with transparent engineering fallbacks:

| Library / Tool | Python 3.14 Limitation | AEGIS Engineering Solution | Status |
| :--- | :--- | :--- | :--- |
| **Evidently AI** | Upstream dependency on `pydantic.v1` throws `ConfigError` under Python 3.14. | Implemented pure `scipy.stats` 2-sample Kolmogorov-Smirnov (KS) test and Population Stability Index (PSI) drift engine in `app/services/drift.py`. | **Operational & Verified** |
| **PyTorch Geometric (PyG)** | Pre-compiled C++ wheels are not available for Windows Python 3.14. | Implemented full bipartite entity modeling and syndicate detection in NetworkX (`app/graph/detector.py`). Documented PyG as optional future extension. | **Operational & Verified** |
| **Feast Feature Store** | Feast CLI installation introduces complex dependency conflicts on Python 3.14. | Provided complete local Feast configuration (`configs/feast/feature_store.yaml`) and entity definitions (`fraud_features.py`). | **Documented & Ready** |
| **MLflow Tracking** | File store URI deprecated by MLflow 3.17. | Upgraded tracking URI to SQLite database (`sqlite:///artifacts/mlflow.db`). | **Operational & Verified** |

---

## 3. Scalability & Architectural Evolution

1. **State Persistence**:
   - Currently, `FeatureStoreState` and `FraudRingDetector` maintain state in process memory with periodic SQLite checkpointing.
   - For enterprise scale (> 50,000 transactions per second across multiple data centers):
     - Replace in-memory state with an ultra-low latency key-value cluster (Redis Enterprise or Dragonfly).
     - Replace NetworkX with a distributed graph database (Neo4j, Amazon Neptune, or TigerGraph).
2. **Streaming Broker**:
   - Default mode uses the zero-dependency `LocalQueueAdapter` so students and evaluators can run the entire platform on a single laptop without configuring Zookeeper or Redpanda.
   - Production deployment switches `FRAUD_STREAMING_BACKEND=kafka` to connect to an enterprise Kafka cluster.

---

## 4. Security & Compliance Safeguards

- **No Real Credentials**: Synthetic accounts and tokens only. No real PANs (Primary Account Numbers) or CVVs are ever processed.
- **Request Size Limiting**: Pydantic models reject payloads with negative amounts or missing entity IDs.
- **Auditing**: Every status change in case management is recorded in `audit_log` with timestamp, previous state, and analyst ID.
