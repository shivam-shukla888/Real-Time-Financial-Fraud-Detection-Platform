"""
Feast Feature Store Definitions for Real-Time Financial Fraud Detection.
Provides entity and feature view declarations for offline training data extraction
and low-latency online serving.
"""

from datetime import timedelta

try:
    from feast import Entity, Field, FeatureView, FileSource
    from feast.types import Float32, Int64, String
    FEAST_INSTALLED = True
except ImportError:
    FEAST_INSTALLED = False
    Entity = Field = FeatureView = FileSource = None
    Float32 = Int64 = String = None


if FEAST_INSTALLED:
    # 1. Declare Primary Entities
    account_entity = Entity(
        name="account_id",
        value_type=String,
        description="Unique bank account identifier"
    )

    device_entity = Entity(
        name="device_id",
        value_type=String,
        description="Unique client device fingerprint"
    )

    # 2. File Source (Parquet or CSV)
    batch_source = FileSource(
        path="data/sample_transactions.csv",
        timestamp_field="timestamp",
        created_timestamp_column="created_at"
    )

    # 3. Account Velocity & Risk Feature View
    account_velocity_fv = FeatureView(
        name="account_velocity_features",
        entities=[account_entity],
        ttl=timedelta(days=14),
        schema=[
            Field(name="txn_count_1h", dtype=Float32),
            Field(name="txn_count_24h", dtype=Float32),
            Field(name="txn_count_7d", dtype=Float32),
            Field(name="amount_sum_1h", dtype=Float32),
            Field(name="amount_sum_24h", dtype=Float32),
            Field(name="amount_to_hist_avg_ratio", dtype=Float32),
        ],
        source=batch_source
    )

    # 4. Device Sharing Feature View
    device_sharing_fv = FeatureView(
        name="device_sharing_features",
        entities=[device_entity],
        ttl=timedelta(days=14),
        schema=[
            Field(name="device_account_count", dtype=Float32),
            Field(name="is_new_device", dtype=Float32),
        ],
        source=batch_source
    )
else:
    # Educational documentation stub when Feast is not installed
    pass
