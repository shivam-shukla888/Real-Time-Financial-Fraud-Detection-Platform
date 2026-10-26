"""
Tests for Data Drift Detection and Retraining Service.
"""

import pytest
import numpy as np
from app.services.drift import calculate_psi, drift_detector


def test_psi_identical_distributions():
    """Identical distributions should exhibit approximately 0 PSI."""
    ref = np.random.normal(loc=100, scale=15, size=500)
    curr = np.random.normal(loc=100, scale=15, size=500)
    psi = calculate_psi(ref, curr)
    assert psi < 0.10, f"Expected PSI < 0.10 for stable data, got {psi}"


def test_psi_shifted_distribution():
    """Drifted distribution should yield significant PSI (> 0.20)."""
    ref = np.random.normal(loc=100, scale=15, size=500)
    curr = np.random.normal(loc=250, scale=30, size=500)  # Significant shift
    psi = calculate_psi(ref, curr)
    assert psi > 0.20, f"Expected PSI > 0.20 for drifted data, got {psi}"


def test_drift_detector_execution():
    """Verify drift detector analyzes dataset and outputs structured report."""
    report = drift_detector.analyze_drift()
    assert "timestamp" in report
    assert "features" in report
    assert "dataset_drift_detected" in report
    assert "approval_status" in report
    assert len(report["features"]) > 0
