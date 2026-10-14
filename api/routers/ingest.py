"""
Real-Feed Ingest Adapters Router
Accepts GPS pings and APC passenger count records from field devices or simulator feeds.
"""
from __future__ import annotations
from fastapi import APIRouter

from core.schemas import IngestGpsRequest, IngestApcRequest, IngestResponse
from api.replayer import get_replayer
from api.sse import broadcaster

router = APIRouter(tags=["Ingest"])


@router.post("/ingest/gps", response_model=IngestResponse)
async def ingest_gps(req: IngestGpsRequest) -> IngestResponse:
    """Ingest external GPS pings, update live vehicle tracking state, and broadcast to stream."""
    replayer = get_replayer()
    replayer.ingest_gps(req.pings)

    # Broadcast ingested pings to active SSE clients
    if broadcaster.subscriber_count > 0:
        await broadcaster.broadcast({
            "event_type": "gps_ingest",
            "count": len(req.pings),
            "pings": [p.model_dump() for p in req.pings]
        }, event="ingest")

    return IngestResponse(status="accepted", count=len(req.pings))


@router.post("/ingest/apc", response_model=IngestResponse)
async def ingest_apc(req: IngestApcRequest) -> IngestResponse:
    """Ingest automated passenger count (APC) records, update vehicle occupancy, and trigger capacity alerts."""
    replayer = get_replayer()
    replayer.ingest_apc(req.records)

    if broadcaster.subscriber_count > 0:
        await broadcaster.broadcast({
            "event_type": "apc_ingest",
            "count": len(req.records),
            "records": [r.model_dump() for r in req.records]
        }, event="ingest")

    return IngestResponse(status="accepted", count=len(req.records))
