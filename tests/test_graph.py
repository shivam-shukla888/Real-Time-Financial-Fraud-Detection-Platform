"""
Tests for NetworkX Fraud Ring & Connected Component Detection.
"""

import pytest
from app.graph.detector import FraudRingDetector, blend_scores


def test_isolated_account_low_graph_risk():
    """An isolated account with a dedicated personal device must receive a low graph risk score."""
    detector = FraudRingDetector()
    txn = {
        "account_id": "ACC_LEGIT_1",
        "device_id": "DEV_LEGIT_1",
        "merchant_id": "MERCH_GROCERY",
        "amount": 50.0,
        "location": "Boston, US"
    }
    detector.add_transaction(txn)
    eval_res = detector.analyze_account("ACC_LEGIT_1", "DEV_LEGIT_1")
    assert eval_res["graph_risk_score"] <= 0.15
    assert eval_res["linked_accounts_count"] == 0
    assert eval_res["is_known_ring"] is False


def test_shared_device_fraud_ring_detection():
    """Multiple accounts transacting from the same device must trigger syndicate detection."""
    detector = FraudRingDetector()
    shared_device = "DEV_SHARED_MULE"

    for i in range(5):
        detector.add_transaction({
            "account_id": f"ACC_MULE_{i}",
            "device_id": shared_device,
            "merchant_id": "MERCH_MULE_CORP",
            "amount": 1500.0,
            "location": "Proxy Node"
        })

    eval_res = detector.analyze_account("ACC_MULE_0", shared_device)
    assert eval_res["graph_risk_score"] >= 0.70
    assert eval_res["linked_accounts_count"] == 4
    assert eval_res["is_known_ring"] is True


def test_blend_scores_and_high_risk_override():
    """Verify score blending weights and high-risk syndicate override."""
    # Standard weighting: 0.65 * 0.2 + 0.35 * 0.1 = 0.13 + 0.035 = 0.165
    blended, tier = blend_scores(ml_score=0.2, graph_score=0.1)
    assert tier == "LOW"
    assert pytest.approx(blended, rel=1e-2) == 0.165

    # High-risk graph override (syndicate emulator detected at 0.90)
    blended_override, tier_override = blend_scores(ml_score=0.3, graph_score=0.90)
    assert tier_override == "CRITICAL"
    assert blended_override >= 0.85
