"""
Pydantic Request & Response Schemas for Fraud Detection API.
Enforces strict input validation, range checks, and type safety.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TransactionPayload(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier", json_schema_extra={"example": "TXN_109281"})
    timestamp: Optional[str] = Field(None, description="ISO format timestamp", json_schema_extra={"example": "2026-10-15 14:30:00"})
    account_id: str = Field(..., description="Originating account ID", json_schema_extra={"example": "ACC_1042"})
    merchant_id: str = Field(..., description="Destination merchant ID", json_schema_extra={"example": "MERCH_3015"})
    category: str = Field("online_retail", description="Transaction category", json_schema_extra={"example": "electronics"})
    amount: float = Field(..., gt=0.0, description="Transaction amount in USD (must be > 0)", json_schema_extra={"example": 249.99})
    device_id: str = Field(..., description="Device fingerprint ID", json_schema_extra={"example": "DEV_2011"})
    location: Optional[str] = Field("New York, US", description="Geographic location / IP node", json_schema_extra={"example": "London, UK"})
    payment_method: Optional[str] = Field("credit_card", description="Payment rail", json_schema_extra={"example": "credit_card"})


class ScoreResponse(BaseModel):
    transaction_id: str
    account_id: str
    timestamp: str
    amount: float
    ml_score: float = Field(..., description="Supervised XGBoost fraud risk probability [0.0 - 1.0]")
    graph_score: float = Field(..., description="NetworkX syndicate / ring risk score [0.0 - 1.0]")
    blended_score: float = Field(..., description="Weighted ensemble risk score [0.0 - 1.0]")
    risk_tier: str = Field(..., description="Risk classification: CRITICAL, HIGH, MEDIUM, LOW")
    is_alert: bool = Field(..., description="Whether threshold triggered an analyst alert")
    alert_id: Optional[str] = None
    latency_ms: float = Field(..., description="Measured real-time inference latency in milliseconds")
    graph_analysis: Dict[str, Any]
    features: Dict[str, Any]


class AnalystFeedbackPayload(BaseModel):
    status: str = Field(..., description="OPEN, INVESTIGATING, CONFIRMED_FRAUD, FALSE_POSITIVE, CLOSED", json_schema_extra={"example": "CONFIRMED_FRAUD"})
    notes: str = Field("", description="Analyst rationale and case notes", json_schema_extra={"example": "Confirmed bot emulator farm."})
    analyst_id: Optional[str] = Field("analyst_1", description="Investigating analyst identifier", json_schema_extra={"example": "analyst_jane"})


class ReplayStartPayload(BaseModel):
    rate: Optional[float] = Field(3.0, ge=0.5, le=50.0, description="Events per second (0.5 to 50.0)")
    max_events: Optional[int] = Field(None, ge=1, le=10000, description="Maximum events to stream before auto-stop")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    port: int


class ReadyResponse(BaseModel):
    ready: bool
    model_loaded: bool
    model_type: Optional[str]
    streaming_adapter: str
    database_connected: bool
    mlflow_tracking_active: bool
    pyg_extension_available: bool
