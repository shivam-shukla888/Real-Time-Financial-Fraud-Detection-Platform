"""
Application Configuration and Settings.
Supports environment variables and provides sensible defaults for local development.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
REPORTS_DIR = BASE_DIR / "reports"
CONFIGS_DIR = BASE_DIR / "configs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    # Application
    APP_NAME: str = "Real-Time Financial Fraud Detection Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8010
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"]

    # Storage Paths
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'fraud_cases.db'}"
    DATA_PATH: Path = DATA_DIR / "sample_transactions.csv"
    MODEL_PATH: Path = ARTIFACTS_DIR / "fraud_model.json"
    MODEL_METADATA_PATH: Path = ARTIFACTS_DIR / "model_metadata.json"
    FEATURE_NAMES_PATH: Path = ARTIFACTS_DIR / "feature_names.json"
    METRICS_PATH: Path = REPORTS_DIR / "metrics.json"
    DRIFT_REPORT_PATH: Path = REPORTS_DIR / "drift_report.json"

    # ML & Fraud Scoring Thresholds
    ML_WEIGHT: float = 0.65
    GRAPH_WEIGHT: float = 0.35
    HIGH_RISK_THRESHOLD: float = 0.70
    MEDIUM_RISK_THRESHOLD: float = 0.40
    GRAPH_OVERRIDE_THRESHOLD: float = 0.85

    # Feature Engineering Parameters
    VELOCITY_WINDOWS_HOURS: List[int] = [1, 24, 168]  # 1h, 1 day, 7 days
    COLD_START_AVERAGE_AMOUNT: float = 120.0

    # Streaming & Replay
    STREAMING_BACKEND: str = "local"  # "local" or "kafka"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TRANSACTIONS_TOPIC: str = "financial-transactions"
    KAFKA_ALERTS_TOPIC: str = "fraud-alerts"
    REPLAY_SPEED_EVENTS_PER_SEC: float = 5.0

    # Drift Detection
    DRIFT_P_VALUE_THRESHOLD: float = 0.05
    DRIFT_SHARE_THRESHOLD: float = 0.30

    # Random Seed for Reproducibility
    RANDOM_SEED: int = 42


settings = Settings()
