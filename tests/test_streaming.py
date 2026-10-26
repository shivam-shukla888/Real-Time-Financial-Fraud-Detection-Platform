"""
Tests for Streaming Queue Adapter and Deduplication.
"""

import asyncio
from app.streaming.adapter import LocalQueueAdapter


def test_local_queue_publish_and_consume():
    """Verify asynchronous event publish and subscriber reception using asyncio.run."""
    async def _test():
        adapter = LocalQueueAdapter()
        received = []

        async def _on_event(event):
            received.append(event)

        await adapter.subscribe(topic="test-topic", callback=_on_event)

        event = {"transaction_id": "TXN_QUEUE_1", "amount": 80.0}
        ok = await adapter.publish(topic="test-topic", event=event)
        assert ok is True

        # Allow async consumer loop to run
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0]["transaction_id"] == "TXN_QUEUE_1"
        await adapter.close()

    asyncio.run(_test())


def test_duplicate_transaction_rejected():
    """Verify deduplication engine rejects identical transaction_ids."""
    async def _test():
        adapter = LocalQueueAdapter()
        event = {"transaction_id": "TXN_DUP_100", "amount": 50.0}

        first_pub = await adapter.publish(topic="test-topic", event=event)
        second_pub = await adapter.publish(topic="test-topic", event=event)

        assert first_pub is True
        assert second_pub is False, "Duplicate transaction must be dropped"
        await adapter.close()

    asyncio.run(_test())
