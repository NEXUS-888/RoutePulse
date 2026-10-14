"""
RoutePulse Server-Sent Events (SSE) Utilities
Provides helpers for event formatting, connection management, and broadcasting.
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, AsyncGenerator, Optional
from sse_starlette.sse import EventSourceResponse


def format_sse_payload(data: Any, event: Optional[str] = None, event_id: Optional[str] = None) -> dict:
    """Format an event dictionary compatible with EventSourceResponse."""
    if isinstance(data, (dict, list)):
        payload_str = json.dumps(data)
    elif isinstance(data, str):
        payload_str = data
    else:
        payload_str = json.dumps(data, default=str)

    msg: dict[str, Any] = {"data": payload_str}
    if event:
        msg["event"] = event
    if event_id:
        msg["id"] = event_id
    return msg


class SSEBroadcaster:
    """
    In-memory pub/sub broker for SSE clients.
    Allows replayers or real-feed ingest endpoints to broadcast live updates to all connected frontends.
    """
    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def broadcast(self, data: Any, event: Optional[str] = "tick", event_id: Optional[str] = None) -> None:
        payload = format_sse_payload(data, event=event, event_id=event_id)
        async with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    if q.full():
                        # Drop oldest item to keep queue real-time
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    q.put_nowait(payload)
                except Exception:
                    dead_queues.append(q)
            for dq in dead_queues:
                self._subscribers.discard(dq)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Global broadcaster instance for live feed updates
broadcaster = SSEBroadcaster()
