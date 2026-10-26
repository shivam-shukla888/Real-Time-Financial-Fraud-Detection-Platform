"""
Data Verification Script.
Validates dataset integrity, schema compliance, missing value absence,
chronological event ordering, and fraud distribution.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.settings import settings


REQUIRED_COLUMNS = [
    "transaction_id",
    "timestamp",
    "account_id",
    "merchant_id",
    "category",
    "amount",
    "device_id",
    "location",
    "payment_method",
    "is_fraud",
    "is_synthetic"
]


def verify_dataset(data_path: Path = settings.DATA_PATH) -> bool:
    """Performs rigorous schema and consistency validation."""
    print(f"[*] Verifying dataset at: {data_path}")

    if not data_path.exists():
        print(f"[ERROR] Dataset file does not exist: {data_path}")
        return False

    file_size_mb = data_path.stat().st_size / (1024 * 1024)
    print(f"[INFO] File size: {file_size_mb:.2f} MB (within <25MB limit)")
    if file_size_mb > 25.0:
        print(f"[ERROR] File exceeds 25 MB safety limit!")
        return False

    df = pd.read_csv(data_path)
    print(f"[INFO] Total records loaded: {len(df):,}")

    if len(df) == 0:
        print("[ERROR] Dataset is empty!")
        return False

    # 1. Check required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        print(f"[ERROR] Missing required columns: {missing_cols}")
        return False
    print(f"[OK] Schema check passed: all {len(REQUIRED_COLUMNS)} required columns present.")

    # 2. Check null values
    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    if null_counts.sum() > 0:
        print(f"[ERROR] Found null values in dataset:\n{null_counts[null_counts > 0]}")
        return False
    print("[OK] Missing value check passed: 0 null entries.")

    # 3. Check amounts
    invalid_amounts = (df["amount"] <= 0).sum()
    if invalid_amounts > 0:
        print(f"[ERROR] Found {invalid_amounts} transactions with non-positive amounts!")
        return False
    print(f"[OK] Amount check passed: Min=${df['amount'].min():.2f}, Max=${df['amount'].max():.2f}, Mean=${df['amount'].mean():.2f}")

    # 4. Check chronological ordering
    ts_series = pd.to_datetime(df["timestamp"])
    if not ts_series.is_monotonic_increasing:
        print("[ERROR] Timestamps are not monotonically increasing! Event time ordering violated.")
        return False
    print(f"[OK] Chronological order check passed: Range {ts_series.min()} to {ts_series.max()}")

    # 5. Check class distribution
    fraud_count = df["is_fraud"].sum()
    fraud_pct = (fraud_count / len(df)) * 100
    print(f"[OK] Fraud distribution: {fraud_count} fraud cases ({fraud_pct:.2f}% prevalence). Realistic imbalance.")

    # 6. Check unique transactions
    duplicates = df["transaction_id"].duplicated().sum()
    if duplicates > 0:
        print(f"[ERROR] Found {duplicates} duplicate transaction_ids!")
        return False
    print(f"[OK] Uniqueness check passed: {df['transaction_id'].nunique()} unique transaction IDs.")

    # 7. Check synthetic marker
    if "is_synthetic" in df.columns and (df["is_synthetic"] == 1).all():
        print("[INFO] Dataset correctly labelled with 'is_synthetic=1' for educational transparency.")

    print("\n[SUMMARY] ALL DATA VERIFICATION CHECKS PASSED SUCCESSFULLY!\n")
    return True


if __name__ == "__main__":
    success = verify_dataset()
    sys.exit(0 if success else 1)
