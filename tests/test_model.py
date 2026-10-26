"""
Tests for Model Artifacts, Inference Engine, and PR-AUC Evaluation.
"""

import pytest
import json
import numpy as np
from configs.settings import settings
from app.ml.engine import engine


def test_model_artifacts_exist():
    """Verify saved model, metadata, and feature names exist."""
    assert settings.MODEL_PATH.exists(), "Trained model artifact missing"
    assert settings.FEATURE_NAMES_PATH.exists(), "Feature names artifact missing"
    assert settings.METRICS_PATH.exists(), "Metrics JSON artifact missing"


def test_inference_engine_scoring():
    """Verify live scoring returns valid probabilities and latency measurement."""
    assert engine.is_ready is True
    sample_txn = {
        "transaction_id": "TXN_PYTEST_1",
        "timestamp": "2026-10-15 15:00:00",
        "account_id": "ACC_TEST_42",
        "merchant_id": "MERCH_101",
        "category": "groceries",
        "amount": 45.50,
        "device_id": "DEV_TEST_42",
        "location": "Austin, US"
    }

    result = engine.score_transaction(sample_txn)
    assert 0.0 <= result["ml_score"] <= 1.0
    assert 0.0 <= result["graph_score"] <= 1.0
    assert 0.0 <= result["blended_score"] <= 1.0
    assert result["risk_tier"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert result["latency_ms"] > 0.0
    assert "features" in result


def test_evaluation_metrics_validity():
    """Verify saved PR-AUC and confusion matrix satisfy mathematical properties."""
    with open(settings.METRICS_PATH, "r") as f:
        metrics = json.load(f)

    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0

    cm = metrics["confusion_matrix"]
    total_evaluated = cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"] + cm["true_positives"]
    assert total_evaluated == metrics["test_records"]
