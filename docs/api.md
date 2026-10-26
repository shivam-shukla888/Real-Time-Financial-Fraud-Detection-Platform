# API Specification & Integration Reference

The AEGIS Fraud Detection API is built with FastAPI and runs by default on port `8010`.

## Base URL
```
http://localhost:8010
```

Interactive Swagger documentation is available at `http://localhost:8010/docs`.

---

## 1. System & Health Endpoints

### `GET /health`
Liveness probe checking basic service uptime.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "service": "Real-Time Financial Fraud Detection Platform",
  "version": "1.0.0",
  "timestamp": "2026-10-27T00:34:32.332169",
  "port": 8010
}
```

### `GET /ready`
Readiness probe verifying model loading, database connectivity, and MLflow state.
- **Response `200 OK`**:
```json
{
  "ready": true,
  "model_loaded": true,
  "model_type": "XGBoost",
  "streaming_adapter": "LOCAL_IN_MEMORY_QUEUE",
  "database_connected": true,
  "mlflow_tracking_active": true,
  "pyg_extension_available": false
}
```

---

## 2. Real-Time Scoring Endpoint

### `POST /score`
Scores an incoming transaction in real-time using the event-time feature pipeline, supervised XGBoost model, and NetworkX syndicate detector.

- **Request Body**:
```json
{
  "transaction_id": "TXN_109281",
  "timestamp": "2026-10-15 14:30:00",
  "account_id": "ACC_1042",
  "merchant_id": "MERCH_3015",
  "category": "electronics",
  "amount": 450.00,
  "device_id": "DEV_2011",
  "location": "New York, US",
  "payment_method": "credit_card"
}
```

- **Response `200 OK`**:
```json
{
  "transaction_id": "TXN_109281",
  "account_id": "ACC_1042",
  "timestamp": "2026-10-15 14:30:00",
  "amount": 450.0,
  "ml_score": 0.0821,
  "graph_score": 0.05,
  "blended_score": 0.0709,
  "risk_tier": "LOW",
  "is_alert": false,
  "alert_id": null,
  "latency_ms": 6.25,
  "graph_analysis": {
    "graph_risk_score": 0.05,
    "cluster_size": 3,
    "linked_accounts_count": 0,
    "shared_devices_count": 1,
    "is_known_ring": false,
    "ring_name": null,
    "suspicious_factors": ["Standard isolated relationship"]
  },
  "features": {
    "amount": 450.0,
    "amount_log": 6.11,
    "txn_count_1h": 0.0,
    "txn_count_24h": 1.0,
    "txn_count_7d": 4.0,
    "amount_to_hist_avg_ratio": 1.45,
    "is_new_device": 0.0,
    "is_new_location": 0.0
  }
}
```

---

## 3. Streaming Replay Endpoints

### `POST /replay/start`
Starts background replay of transactions at a specified event rate.
- **Request Body (Optional)**:
```json
{
  "rate": 3.0,
  "max_events": 500
}
```
- **Response `200 OK`**:
```json
{
  "status": "started",
  "rate_events_per_sec": 3.0,
  "max_events": 500,
  "streaming_mode": "LOCAL_IN_MEMORY_QUEUE"
}
```

### `POST /replay/stop`
Pauses or terminates background replay.
- **Response `200 OK`**:
```json
{
  "status": "stopped"
}
```

### `GET /transactions`
Returns the most recent scored transactions from the in-memory circular buffer.
- **Query Parameters**:
  - `limit` (default: 50, max: 200)

---

## 4. Alert & Case Investigation Endpoints

### `GET /alerts`
Fetches paginated alerts stored in SQLite with optional filtering.
- **Query Parameters**:
  - `status`: `OPEN`, `INVESTIGATING`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `CLOSED`
  - `risk_tier`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - `limit`: int (default 50)
  - `offset`: int (default 0)

### `GET /alerts/{alert_id}`
Returns details for a single alert.

### `POST /alerts/{alert_id}/feedback`
Allows analysts to record status updates and investigation notes into the audit trail.
- **Request Body**:
```json
{
  "status": "CONFIRMED_FRAUD",
  "notes": "Verified high-velocity device sharing matching Mule Syndicate #1.",
  "analyst_id": "lead_analyst_jane"
}
```

---

## 5. Syndicate Graph & Drift Endpoints

### `GET /graph/rings`
Returns all multi-account syndicate clusters detected by NetworkX.

### `GET /graph/subgraph`
Returns nodes and edges formatted for the interactive UI graph canvas.

### `GET /drift`
Returns statistical Kolmogorov-Smirnov and PSI data drift results.

### `POST /retrain`
Approval-gated retraining trigger:
- **Query Parameter**: `approver_id` (default: `lead_ml_engineer`)
- Retrains model on approved training baseline, logs to MLflow, and hot-reloads inference engine.
