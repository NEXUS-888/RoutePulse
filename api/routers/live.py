"""
Live SSE Stream Router
Provides real-time accelerated replay of GPS pings, ETAs, and alerts.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from api.replayer import get_replayer

router = APIRouter(tags=["Live"])


@router.get("/live/stream")
async def live_stream(
    speed: int = Query(default=30, ge=1, le=120, description="Replay speed multiplier"),
    scenario_id: str = Query(default="S0", description="Scenario ID (S0, S1, S2, S3)"),
    start_time_min: int = Query(default=450, ge=0, le=1440, description="Start time in minutes from midnight (07:30 = 450)"),
    max_ticks: Optional[int] = Query(default=None, description="Optional limit of ticks (useful for tests/batch queries)")
):
    """
    SSE endpoint streaming live vehicle GPS pings, ETAs, and active alerts.
    Paces ticks with accelerated simulation time (e.g. 30x real-time).
    """
    replayer = get_replayer()
    replayer.reset(scenario_id=scenario_id, start_time_min=start_time_min, speed=speed)
    return EventSourceResponse(
        replayer.stream(speed=speed, scenario_id=scenario_id, start_time_min=start_time_min, interval_sec=0.1 if max_ticks else 1.0, max_ticks=max_ticks)
    )


@router.get("/live/status")
def get_live_status():
    """Return current replayer clock, scenario, and active fleet counts."""
    replayer = get_replayer()
    return {
        "current_time_sec": replayer.current_time_sec,
        "time_str": replayer.format_time(replayer.current_time_sec),
        "speed": replayer.speed,
        "scenario_id": replayer.scenario_id,
        "active_vehicles": sum(1 for s in replayer.vehicle_states.values() if s.get("status") == "in_transit"),
        "total_vehicles": len(replayer.vehicle_states)
    }


@router.post("/live/reset")
def reset_live(
    speed: int = Query(default=30),
    scenario_id: str = Query(default="S0"),
    start_time_min: int = Query(default=450)
):
    """Reset live replayer clock and scenario."""
    replayer = get_replayer()
    replayer.reset(scenario_id=scenario_id, start_time_min=start_time_min, speed=speed)
    return {"status": "reset", "scenario_id": scenario_id, "start_time_min": start_time_min}
