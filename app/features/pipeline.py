"""
Feature Engineering Pipeline for Real-Time Fraud Detection.
Implements event-time historical state tracking to strictly prevent target leakage.
Provides identical feature representations for both batch training and real-time streaming inference.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd


# Category baseline risk priors (prior domain knowledge, not learned from labels)
CATEGORY_RISK_PRIORS = {
    "groceries": 0.05,
    "dining": 0.08,
    "entertainment": 0.12,
    "online_retail": 0.20,
    "electronics": 0.35,
    "travel": 0.30,
    "money_transfer": 0.65,
    "crypto_exchange": 0.75,
}

FEATURE_COLUMNS = [
    "amount",
    "amount_log",
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "amount_sum_1h",
    "amount_sum_24h",
    "amount_to_hist_avg_ratio",
    "is_new_device",
    "is_new_location",
    "device_account_count",
    "hour_of_day",
    "day_of_week",
    "is_night",
    "is_weekend",
    "category_risk_prior"
]


class FeatureStoreState:
    """
    Maintains historical event-time state per account and device.
    Used for online serving and stateful batch feature computation.
    """
    def __init__(self, cold_start_avg_amount: float = 120.0):
        self.cold_start_avg_amount = cold_start_avg_amount
        # account_id -> list of (timestamp: datetime, amount: float)
        self.account_history: Dict[str, List[Tuple[datetime, float]]] = {}
        # account_id -> set of known device_ids
        self.account_devices: Dict[str, set] = {}
        # account_id -> set of known locations
        self.account_locations: Dict[str, set] = {}
        # device_id -> set of accounts that used this device
        self.device_accounts: Dict[str, set] = {}

    def extract_and_update(self, txn: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract features for transaction strictly using PAST state (prior to txn timestamp),
        and THEN updates the state with this transaction.
        Ensures 0 target leakage and 0 future lookahead.
        """
        # Parse timestamp
        raw_ts = txn["timestamp"]
        if isinstance(raw_ts, str):
            ts = datetime.strptime(raw_ts[:19], "%Y-%m-%d %H:%M:%S")
        elif isinstance(raw_ts, datetime):
            ts = raw_ts
        else:
            ts = pd.to_datetime(raw_ts).to_pydatetime()

        account_id = str(txn["account_id"])
        device_id = str(txn["device_id"])
        location = str(txn.get("location", "Unknown"))
        amount = float(txn["amount"])
        category = str(txn.get("category", "online_retail")).lower()

        # 1. Temporal time-of-day features
        hour = ts.hour
        day_of_week = ts.weekday()
        is_night = 1.0 if (hour >= 23 or hour <= 6) else 0.0
        is_weekend = 1.0 if day_of_week >= 5 else 0.0

        # 2. Historical account stats (BEFORE current transaction)
        hist = self.account_history.get(account_id, [])
        known_devs = self.account_devices.get(account_id, set())
        known_locs = self.account_locations.get(account_id, set())
        dev_accs = self.device_accounts.get(device_id, set())

        # Velocity in windows strictly before ts
        one_hour_ago = ts - timedelta(hours=1)
        one_day_ago = ts - timedelta(days=1)
        seven_days_ago = ts - timedelta(days=7)

        count_1h = 0
        sum_1h = 0.0
        count_24h = 0
        sum_24h = 0.0
        count_7d = 0

        past_amounts = []
        for past_ts, past_amt in hist:
            past_amounts.append(past_amt)
            if past_ts >= one_hour_ago:
                count_1h += 1
                sum_1h += past_amt
            if past_ts >= one_day_ago:
                count_24h += 1
                sum_24h += past_amt
            if past_ts >= seven_days_ago:
                count_7d += 1

        # Historical average amount
        if len(past_amounts) > 0:
            hist_avg = sum(past_amounts) / len(past_amounts)
        else:
            hist_avg = self.cold_start_avg_amount  # Cold-start fallback

        amount_ratio = amount / max(hist_avg, 1.0)
        is_new_dev = 1.0 if (len(known_devs) > 0 and device_id not in known_devs) else (0.5 if len(known_devs) == 0 else 0.0)
        is_new_loc = 1.0 if (len(known_locs) > 0 and location not in known_locs) else (0.5 if len(known_locs) == 0 else 0.0)
        dev_account_count = float(len(dev_accs))

        category_prior = CATEGORY_RISK_PRIORS.get(category, 0.20)

        # Assemble feature dict
        features = {
            "amount": amount,
            "amount_log": float(np.log1p(max(0.0, amount))),
            "txn_count_1h": float(count_1h),
            "txn_count_24h": float(count_24h),
            "txn_count_7d": float(count_7d),
            "amount_sum_1h": float(sum_1h),
            "amount_sum_24h": float(sum_24h),
            "amount_to_hist_avg_ratio": float(amount_ratio),
            "is_new_device": float(is_new_dev),
            "is_new_location": float(is_new_loc),
            "device_account_count": float(dev_account_count),
            "hour_of_day": float(hour),
            "day_of_week": float(day_of_week),
            "is_night": float(is_night),
            "is_weekend": float(is_weekend),
            "category_risk_prior": float(category_prior)
        }

        # NOW update state for future transactions (Strict post-event update)
        if account_id not in self.account_history:
            self.account_history[account_id] = []
            self.account_devices[account_id] = set()
            self.account_locations[account_id] = set()

        self.account_history[account_id].append((ts, amount))
        self.account_devices[account_id].add(device_id)
        self.account_locations[account_id].add(location)

        if device_id not in self.device_accounts:
            self.device_accounts[device_id] = set()
        self.device_accounts[device_id].add(account_id)

        return features


class FeaturePipeline:
    """
    Batch and online feature engineering processor.
    """
    def __init__(self, cold_start_avg_amount: float = 120.0):
        self.cold_start_avg_amount = cold_start_avg_amount
        self.feature_columns = FEATURE_COLUMNS

    def transform_batch(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Transforms a dataframe in chronological order into feature matrix X and label series y.
        Strictly applies event-time simulation without target leakage.
        """
        # Ensure chronological order
        df_sorted = df.sort_values(by="timestamp").copy()
        state = FeatureStoreState(cold_start_avg_amount=self.cold_start_avg_amount)

        feature_rows = []
        for _, row in df_sorted.iterrows():
            txn_dict = row.to_dict()
            feats = state.extract_and_update(txn_dict)
            feature_rows.append(feats)

        X = pd.DataFrame(feature_rows, columns=self.feature_columns)
        y = df_sorted["is_fraud"].reset_index(drop=True) if "is_fraud" in df_sorted.columns else None

        return X, y

    def extract_single(self, txn: Dict[str, Any], state: FeatureStoreState) -> List[float]:
        """
        Extracts vector of features in exact training order for real-time model inference.
        """
        feats = state.extract_and_update(txn)
        return [feats[col] for col in self.feature_columns]
