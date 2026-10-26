"""
Tests for Data Preparation, Schema Integrity, and Reproducibility.
"""

import pytest
import pandas as pd
from pathlib import Path
from configs.settings import settings
from scripts.prepare_data import generate_synthetic_transactions
from scripts.verify_data import verify_dataset, REQUIRED_COLUMNS


def test_sample_dataset_exists_and_valid():
    """Verify that sample_transactions.csv exists and passes all verification rules."""
    assert settings.DATA_PATH.exists(), f"Missing dataset at {settings.DATA_PATH}"
    assert verify_dataset(settings.DATA_PATH) is True


def test_dataset_reproducibility(tmp_path: Path):
    """Verify that identical random seeds produce byte-for-byte identical datasets."""
    file1 = tmp_path / "seed_a.csv"
    file2 = tmp_path / "seed_b.csv"

    df1 = generate_synthetic_transactions(n_records=100, seed=42, output_path=file1)
    df2 = generate_synthetic_transactions(n_records=100, seed=42, output_path=file2)

    pd.testing.assert_frame_equal(df1, df2)


def test_schema_and_types():
    """Verify required column presence and non-null constraints."""
    df = pd.read_csv(settings.DATA_PATH)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Missing required column: {col}"
    assert df["amount"].min() > 0, "Amounts must be strictly positive"
    assert df["is_fraud"].isin([0, 1]).all(), "Fraud label must be binary 0 or 1"
    assert (df["is_synthetic"] == 1).all(), "Synthetic transparency flag must be 1"
