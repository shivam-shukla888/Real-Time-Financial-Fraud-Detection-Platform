"""
Tests for FastAPI Endpoints, Input Validation, and Case Feedback.
"""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_health_and_readiness_endpoints():
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True


def test_score_valid_transaction():
    payload = {
        "transaction_id": "TXN_API_TEST_01",
        "account_id": "ACC_API_TEST",
        "merchant_id": "MERCH_101",
        "category": "online_retail",
        "amount": 125.00,
        "device_id": "DEV_API_TEST",
        "location": "Chicago, US"
    }
    res = client.post("/score", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["transaction_id"] == "TXN_API_TEST_01"
    assert "blended_score" in data
    assert "latency_ms" in data


def test_score_invalid_amount_rejected():
    """Verify negative or 0 transaction amounts are rejected with 422 Unprocessable Entity."""
    payload = {
        "transaction_id": "TXN_BAD",
        "account_id": "ACC_BAD",
        "merchant_id": "MERCH_101",
        "amount": -50.0,  # Invalid amount
        "device_id": "DEV_BAD"
    }
    res = client.post("/score", json=payload)
    assert res.status_code == 422


def test_alerts_listing_and_feedback_update():
    """Verify alerts endpoint and analyst feedback state transitions."""
    # Score a known high risk event to trigger alert
    payload = {
        "transaction_id": "TXN_ALERT_TEST_99",
        "account_id": "ACC_RING1_99",
        "merchant_id": "MERCH_MULE_CORP",
        "category": "money_transfer",
        "amount": 4500.0,
        "device_id": "DEV_RING1_A",
        "location": "Unknown Proxy"
    }
    score_res = client.post("/score", json=payload)
    assert score_res.status_code == 200
    alert_id = score_res.json()["alert_id"]
    assert alert_id is not None

    # Retrieve alerts
    alerts_res = client.get("/alerts")
    assert alerts_res.status_code == 200

    # Submit analyst feedback
    feedback_payload = {
        "status": "CONFIRMED_FRAUD",
        "notes": "Verified bot emulator and proxy mismatch.",
        "analyst_id": "analyst_qa"
    }
    fb_res = client.post(f"/alerts/{alert_id}/feedback", json=feedback_payload)
    assert fb_res.status_code == 200
    assert fb_res.json()["alert"]["status"] == "CONFIRMED_FRAUD"

    # Reject invalid status
    bad_fb = client.post(f"/alerts/{alert_id}/feedback", json={"status": "INVALID_STATE", "notes": ""})
    assert bad_fb.status_code == 400
