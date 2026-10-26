"""
Real-Time Fraud Inference Engine.
Coordinates:
- Feature extraction via FeaturePipeline & FeatureStoreState
- Supervised ML risk scoring via XGBoost
- Graph-based syndicate analysis via FraudRingDetector
- Score blending and automated alert generation
- Millisecond latency measurement
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from configs.settings import settings, ARTIFACTS_DIR
from app.features.pipeline import FeaturePipeline, FeatureStoreState
from app.graph.detector import FraudRingDetector, blend_scores
from app.services.database import CaseDatabase


class FraudInferenceEngine:
    def __init__(
        self,
        model_path: Path = settings.MODEL_PATH,
        feature_names_path: Path = settings.FEATURE_NAMES_PATH
    ):
        self.model_path = model_path
        self.feature_names_path = feature_names_path
        self.model = None
        self.feature_names: List[str] = []
        self.is_ready = False

        # In-memory feature state for low-latency streaming
        self.feature_state = FeatureStoreState(cold_start_avg_amount=settings.COLD_START_AVERAGE_AMOUNT)
        self.pipeline = FeaturePipeline(cold_start_avg_amount=settings.COLD_START_AVERAGE_AMOUNT)

        # Graph ring detector
        self.graph_detector = FraudRingDetector()

        # Alert database
        self.db = CaseDatabase()

        # Operational metrics tracking
        self.latencies_ms: List[float] = []
        self.total_scored: int = 0
        self.total_alerts: int = 0

        self.load_artifacts()

    def load_artifacts(self):
        """Loads trained XGBoost model and feature names from disk."""
        if not self.model_path.exists() or not self.feature_names_path.exists():
            print(f"[WARN] Artifacts not found at {self.model_path}. Train the model first.")
            self.is_ready = False
            return

        with open(self.feature_names_path, "r") as f:
            self.feature_names = json.load(f)

        try:
            import xgboost as xgb
            self.model = xgb.XGBClassifier()
            self.model.load_model(str(self.model_path))
            self.is_ready = True
            print(f"[OK] Successfully loaded XGBoost model from: {self.model_path}")
        except Exception as e:
            print(f"[WARN] Failed loading XGBoost model ({e}). Attempting joblib fallback.")
            try:
                import joblib
                joblib_path = self.model_path.with_suffix(".joblib")
                if joblib_path.exists():
                    self.model = joblib.load(str(joblib_path))
                    self.is_ready = True
                    print(f"[OK] Successfully loaded fallback model from: {joblib_path}")
            except Exception as e2:
                print(f"[ERROR] Could not load model: {e2}")
                self.is_ready = False

    def score_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores a single transaction event in real time.
        Measures exact wall-clock latency in milliseconds.
        """
        start_t = time.perf_counter()

        if not self.is_ready or self.model is None:
            raise RuntimeError("Fraud inference engine is not ready. Model is not loaded.")

        account_id = str(txn["account_id"])
        device_id = str(txn["device_id"])

        # 1. Update Graph & Evaluate Syndicate / Ring Risk
        self.graph_detector.add_transaction(txn)
        graph_eval = self.graph_detector.analyze_account(account_id, device_id)
        graph_score = float(graph_eval["graph_risk_score"])

        # 2. Extract Event-Time Features (Strict zero leakage)
        feature_dict = self.feature_state.extract_and_update(txn)
        feature_vector = [feature_dict[col] for col in self.feature_names]
        X = pd.DataFrame([feature_vector], columns=self.feature_names)

        # 3. Supervised ML Prediction Probability
        proba = self.model.predict_proba(X)[0]
        # Class 1 is fraud
        ml_score = float(proba[1]) if len(proba) > 1 else float(proba[0])

        # 4. Blend Supervised & Graph Risk Scores
        blended_score, risk_tier = blend_scores(
            ml_score=ml_score,
            graph_score=graph_score,
            ml_weight=settings.ML_WEIGHT,
            graph_weight=settings.GRAPH_WEIGHT,
            high_threshold=settings.HIGH_RISK_THRESHOLD,
            medium_threshold=settings.MEDIUM_RISK_THRESHOLD,
            graph_override_threshold=settings.GRAPH_OVERRIDE_THRESHOLD
        )

        # Compute elapsed latency in ms
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        self.latencies_ms.append(elapsed_ms)
        if len(self.latencies_ms) > 1000:
            self.latencies_ms.pop(0)
        self.total_scored += 1

        # 5. Check Alert Trigger
        is_alert = (risk_tier in ["HIGH", "CRITICAL"]) or (blended_score >= settings.HIGH_RISK_THRESHOLD)
        alert_id = None
        if is_alert:
            self.total_alerts += 1
            alert_id = f"ALT_{txn['transaction_id']}"
            alert_payload = {
                "alert_id": alert_id,
                "transaction_id": txn["transaction_id"],
                "timestamp": txn["timestamp"],
                "account_id": account_id,
                "merchant_id": txn.get("merchant_id", "Unknown"),
                "category": txn.get("category", "Unknown"),
                "amount": float(txn["amount"]),
                "device_id": device_id,
                "location": txn.get("location", "Unknown"),
                "ml_score": round(ml_score, 4),
                "graph_score": round(graph_score, 4),
                "blended_score": round(blended_score, 4),
                "risk_tier": risk_tier,
                "status": "OPEN",
                "analyst_notes": f"Triggered by {risk_tier} risk profile. Graph factors: {', '.join(graph_eval['suspicious_factors'])}",
                "analyst_id": "auto_trigger"
            }
            self.db.save_alert(alert_payload)

        return {
            "transaction_id": txn["transaction_id"],
            "account_id": account_id,
            "timestamp": txn["timestamp"],
            "amount": float(txn["amount"]),
            "ml_score": round(ml_score, 4),
            "graph_score": round(graph_score, 4),
            "blended_score": round(blended_score, 4),
            "risk_tier": risk_tier,
            "is_alert": is_alert,
            "alert_id": alert_id,
            "latency_ms": round(elapsed_ms, 2),
            "graph_analysis": graph_eval,
            "features": {k: round(v, 2) if isinstance(v, float) else v for k, v in feature_dict.items()}
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns runtime performance statistics."""
        avg_lat = float(np.mean(self.latencies_ms)) if self.latencies_ms else 0.0
        p95_lat = float(np.percentile(self.latencies_ms, 95)) if self.latencies_ms else 0.0
        p99_lat = float(np.percentile(self.latencies_ms, 99)) if self.latencies_ms else 0.0
        return {
            "total_scored": self.total_scored,
            "total_alerts": self.total_alerts,
            "alert_rate": round(self.total_alerts / max(1, self.total_scored), 4),
            "latency_ms": {
                "average": round(avg_lat, 2),
                "p95": round(p95_lat, 2),
                "p99": round(p99_lat, 2),
                "measurement_method": "High-resolution time.perf_counter() elapsed per scoring invocation"
            }
        }


# Global singleton engine instance
engine = FraudInferenceEngine()
