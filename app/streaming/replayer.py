"""
Transaction Replay Producer and Streaming Consumer.
Simulates real-time transaction flow at configurable event rates,
routes events through the streaming adapter (Local Queue or Kafka),
and executes automated real-time scoring and alerting.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

from configs.settings import settings
from app.streaming.adapter import get_streaming_adapter, BaseStreamingAdapter
from app.ml.engine import engine


class TransactionReplayer:
    def __init__(
        self,
        data_path: Path = settings.DATA_PATH,
        adapter: Optional[BaseStreamingAdapter] = None,
        rate_events_per_sec: float = 3.0
    ):
        self.data_path = data_path
        self.adapter = adapter or get_streaming_adapter(backend=settings.STREAMING_BACKEND)
        self.rate_events_per_sec = rate_events_per_sec
        self.is_replaying = False
        self._replay_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None

        # Recent stream cache for frontend queries (in-memory ring buffer)
        self.recent_transactions: List[Dict[str, Any]] = []
        self.max_cache_size = 200

    async def initialize(self):
        """Starts the background stream consumer."""
        await self.adapter.subscribe(
            topic=settings.KAFKA_TRANSACTIONS_TOPIC,
            callback=self._handle_incoming_transaction
        )

    async def _handle_incoming_transaction(self, event: Dict[str, Any]):
        """Callback invoked when transaction is consumed from queue."""
        try:
            # Score transaction using live ML & graph inference
            result = engine.score_transaction(event)

            # Prepend to recent transactions buffer
            self.recent_transactions.insert(0, result)
            if len(self.recent_transactions) > self.max_cache_size:
                self.recent_transactions.pop()

            # If alert, publish to alerts topic
            if result.get("is_alert"):
                await self.adapter.publish(
                    topic=settings.KAFKA_ALERTS_TOPIC,
                    event={
                        "alert_id": result["alert_id"],
                        "transaction_id": result["transaction_id"],
                        "risk_tier": result["risk_tier"],
                        "blended_score": result["blended_score"],
                        "timestamp": result["timestamp"]
                    }
                )
        except Exception as e:
            print(f"[ERROR scoring streamed transaction]: {e}")

    async def start_replay(self, max_events: Optional[int] = None, rate: Optional[float] = None) -> bool:
        """Starts async loop streaming transactions from CSV."""
        if self.is_replaying:
            return False

        if rate:
            self.rate_events_per_sec = rate

        if not self.data_path.exists():
            return False

        df = pd.read_csv(self.data_path)
        transactions = df.to_dict(orient="records")
        if max_events:
            transactions = transactions[:max_events]

        self.is_replaying = True

        async def _run():
            delay = 1.0 / max(0.5, self.rate_events_per_sec)
            for txn in transactions:
                if not self.is_replaying:
                    break
                await self.adapter.publish(
                    topic=settings.KAFKA_TRANSACTIONS_TOPIC,
                    event=txn
                )
                await asyncio.sleep(delay)
            self.is_replaying = False

        self._replay_task = asyncio.create_task(_run())
        return True

    def stop_replay(self) -> bool:
        """Stops the streaming replay loop."""
        if not self.is_replaying:
            return False
        self.is_replaying = False
        if self._replay_task:
            self._replay_task.cancel()
        return True

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.recent_transactions[:limit]


# Global replayer instance
replayer = TransactionReplayer()
