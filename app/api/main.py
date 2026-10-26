"""
FastAPI Real-Time Fraud Scoring & Analytics Service.
Serves real-time inference, alert investigation, streaming replay,
graph syndicate analysis, and drift metrics.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Path as FPath, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from configs.settings import settings, REPORTS_DIR, ARTIFACTS_DIR
from app.api.schemas import (
    TransactionPayload,
    ScoreResponse,
    AnalystFeedbackPayload,
    ReplayStartPayload,
    HealthResponse,
    ReadyResponse
)
from app.ml.engine import engine
from app.services.database import CaseDatabase
from app.streaming.replayer import replayer
from app.services.drift import drift_detector, RetrainingService
from app.graph.detector import check_pyg_support


db = CaseDatabase()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure artifacts are loaded and stream consumer initialized
    print("[*] Starting Real-Time Fraud Detection API Service...")
    if not engine.is_ready:
        engine.load_artifacts()
    await replayer.initialize()
    print(f"[OK] Fraud API ready and listening on port {settings.PORT}.")
    yield
    # Shutdown
    print("[*] Shutting down Fraud Detection API...")
    replayer.stop_replay()
    await replayer.adapter.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Financial Fraud Detection Platform with Supervised ML, NetworkX Syndicate Analysis, and Streaming.",
    lifespan=lifespan
)

# Enable CORS for React / Vite and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Liveness probe returning operational state and port."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "port": settings.PORT
    }


@app.get("/ready", response_model=ReadyResponse, tags=["System"])
async def readiness_check():
    """Readiness probe checking model loading and database health."""
    pyg_info = check_pyg_support()
    mlflow_db = ARTIFACTS_DIR / "mlflow.db"
    return {
        "ready": engine.is_ready,
        "model_loaded": engine.is_ready,
        "model_type": "XGBoost" if engine.is_ready else None,
        "streaming_adapter": replayer.adapter.mode,
        "database_connected": True,
        "mlflow_tracking_active": mlflow_db.exists(),
        "pyg_extension_available": pyg_info["available"]
    }


@app.post("/score", response_model=ScoreResponse, tags=["Scoring"])
async def score_transaction(payload: TransactionPayload):
    """
    Real-time fraud scoring endpoint.
    Extracts event-time features, computes supervised XGBoost probability,
    evaluates NetworkX entity graph for fraud rings, and blends scores.
    """
    if not engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference engine is not ready. Model is not trained or loaded."
        )

    txn_dict = payload.model_dump()
    if not txn_dict.get("timestamp"):
        txn_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = engine.score_transaction(txn_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/transactions", tags=["Streaming"])
async def get_recent_transactions(limit: int = Query(50, ge=1, le=200)):
    """Returns the most recent scored streaming transactions from in-memory ring buffer."""
    return replayer.get_recent(limit=limit)


@app.get("/alerts", tags=["Analyst Investigation"])
async def list_alerts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, INVESTIGATING, CONFIRMED_FRAUD, FALSE_POSITIVE, CLOSED"),
    risk_tier: Optional[str] = Query(None, description="Filter by tier: CRITICAL, HIGH, MEDIUM, LOW"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Returns paginated analyst alerts from SQLite store."""
    alerts = db.list_alerts(status=status_filter, risk_tier=risk_tier, limit=limit, offset=offset)
    counts = db.get_alert_counts()
    return {
        "alerts": alerts,
        "total_count": counts.get("TOTAL", len(alerts)),
        "status_breakdown": counts
    }


@app.get("/alerts/{alert_id}", tags=["Analyst Investigation"])
async def get_alert(alert_id: str = FPath(..., description="Unique alert ID")):
    """Returns specific alert record with investigation history."""
    alert = db.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found.")
    return alert


@app.post("/alerts/{alert_id}/feedback", tags=["Analyst Investigation"])
async def submit_analyst_feedback(
    payload: AnalystFeedbackPayload,
    alert_id: str = FPath(..., description="Unique alert ID")
):
    """Updates case status, adds analyst investigation notes, and logs to audit trail."""
    try:
        updated = db.update_alert_feedback(
            alert_id=alert_id,
            new_status=payload.status,
            analyst_notes=payload.notes,
            analyst_id=payload.analyst_id
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found.")
        return {
            "message": "Analyst feedback recorded successfully.",
            "alert": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/metrics", tags=["Metrics & Ops"])
async def get_metrics():
    """Returns model training performance metrics and operational streaming statistics."""
    model_metrics = {}
    if settings.METRICS_PATH.exists():
        with open(settings.METRICS_PATH, "r") as f:
            model_metrics = json.load(f)

    runtime_stats = engine.get_stats()
    alert_counts = db.get_alert_counts()

    return {
        "model_evaluation": model_metrics,
        "runtime_ops": runtime_stats,
        "case_management": alert_counts,
        "thresholds": {
            "ml_weight": settings.ML_WEIGHT,
            "graph_weight": settings.GRAPH_WEIGHT,
            "high_risk_threshold": settings.HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": settings.MEDIUM_RISK_THRESHOLD,
            "graph_override_threshold": settings.GRAPH_OVERRIDE_THRESHOLD
        }
    }


@app.get("/graph/rings", tags=["Graph Syndicate Detection"])
async def get_fraud_rings():
    """Returns detected multi-account syndicate clusters across the entity graph."""
    rings = engine.graph_detector.get_rings_summary()
    return {
        "rings_count": len(rings),
        "rings": rings
    }


@app.get("/graph/subgraph", tags=["Graph Syndicate Detection"])
async def get_subgraph(max_nodes: int = Query(60, ge=10, le=150)):
    """Exports representative entity graph nodes and edges for front-end graph visualizer."""
    return engine.graph_detector.export_subgraph(max_nodes=max_nodes)


@app.post("/replay/start", tags=["Streaming"])
async def start_streaming_replay(payload: Optional[ReplayStartPayload] = None):
    """Starts background transaction replay streaming loop."""
    rate = payload.rate if payload else 3.0
    max_ev = payload.max_events if payload else None
    started = await replayer.start_replay(max_events=max_ev, rate=rate)
    return {
        "status": "started" if started else "already_running",
        "rate_events_per_sec": rate,
        "max_events": max_ev,
        "streaming_mode": replayer.adapter.mode
    }


@app.post("/replay/stop", tags=["Streaming"])
async def stop_streaming_replay():
    """Stops the streaming replay loop."""
    stopped = replayer.stop_replay()
    return {
        "status": "stopped" if stopped else "not_running"
    }


@app.get("/drift", tags=["Drift & Retraining"])
async def get_drift_report():
    """Returns current statistical data drift report."""
    if settings.DRIFT_REPORT_PATH.exists():
        with open(settings.DRIFT_REPORT_PATH, "r") as f:
            return json.load(f)
    # Generate on demand if missing
    return drift_detector.analyze_drift()


@app.post("/retrain", tags=["Drift & Retraining"])
async def trigger_retraining(approver_id: str = Query("lead_ml_engineer", description="Authorized approver ID")):
    """Executes approval-gated model retraining."""
    result = RetrainingService.trigger_retraining(approver_id=approver_id)
    # Reload newly trained model into inference engine
    engine.load_artifacts()
    return result
