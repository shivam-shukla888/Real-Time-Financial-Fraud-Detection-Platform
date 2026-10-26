"""
Persistent Case Management & Alert Storage Service using SQLite.
Stores detected alerts, analyst investigation states, and case history.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from configs.settings import settings, DATA_DIR


DB_FILE = DATA_DIR / "fraud_cases.db"


def init_db(db_path: Path = DB_FILE):
    """Initializes tables for alerts and analyst feedback if not existing."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                account_id TEXT NOT NULL,
                merchant_id TEXT,
                category TEXT,
                amount REAL NOT NULL,
                device_id TEXT,
                location TEXT,
                ml_score REAL NOT NULL,
                graph_score REAL NOT NULL,
                blended_score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                analyst_notes TEXT DEFAULT '',
                analyst_id TEXT DEFAULT 'system',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT NOT NULL,
                analyst_id TEXT NOT NULL,
                notes TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_tier ON alerts(risk_tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp)")
        conn.commit()


class CaseDatabase:
    def __init__(self, db_path: Path = DB_FILE):
        self.db_path = db_path
        init_db(self.db_path)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_alert(self, alert_data: Dict[str, Any]) -> str:
        """Saves a new alert. Idempotent on transaction_id."""
        now = datetime.now().isoformat()
        alert_id = alert_data.get("alert_id") or f"ALT_{alert_data['transaction_id']}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO alerts (
                    alert_id, transaction_id, timestamp, account_id, merchant_id,
                    category, amount, device_id, location, ml_score, graph_score,
                    blended_score, risk_tier, status, analyst_notes, analyst_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                alert_data["transaction_id"],
                alert_data["timestamp"],
                alert_data["account_id"],
                alert_data.get("merchant_id", "Unknown"),
                alert_data.get("category", "Unknown"),
                float(alert_data["amount"]),
                alert_data.get("device_id", "Unknown"),
                alert_data.get("location", "Unknown"),
                float(alert_data["ml_score"]),
                float(alert_data["graph_score"]),
                float(alert_data["blended_score"]),
                alert_data["risk_tier"],
                alert_data.get("status", "OPEN"),
                alert_data.get("analyst_notes", ""),
                alert_data.get("analyst_id", "system"),
                now,
                now
            ))
            conn.commit()
        return alert_id

    def list_alerts(
        self,
        status: Optional[str] = None,
        risk_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Returns filtered list of alerts."""
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        if status and status.upper() != "ALL":
            query += " AND status = ?"
            params.append(status.upper())
        if risk_tier and risk_tier.upper() != "ALL":
            query += " AND risk_tier = ?"
            params.append(risk_tier.upper())
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_alert_feedback(
        self,
        alert_id: str,
        new_status: str,
        analyst_notes: str,
        analyst_id: str = "analyst_1"
    ) -> Optional[Dict[str, Any]]:
        """Updates alert status and inserts an audit log entry."""
        valid_statuses = {"OPEN", "INVESTIGATING", "CONFIRMED_FRAUD", "FALSE_POSITIVE", "CLOSED"}
        new_status = new_status.upper()
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM alerts WHERE alert_id = ?", (alert_id,))
            existing = cursor.fetchone()
            if not existing:
                return None
            prev_status = existing["status"]

            cursor.execute("""
                UPDATE alerts
                SET status = ?, analyst_notes = ?, analyst_id = ?, updated_at = ?
                WHERE alert_id = ?
            """, (new_status, analyst_notes, analyst_id, now, alert_id))

            cursor.execute("""
                INSERT INTO audit_log (alert_id, previous_status, new_status, analyst_id, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alert_id, prev_status, new_status, analyst_id, analyst_notes, now))
            conn.commit()

        return self.get_alert_by_id(alert_id)

    def get_alert_counts(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status")
            counts = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) FROM alerts")
            total = cursor.fetchone()[0]
            counts["TOTAL"] = total
            return counts
