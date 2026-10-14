"""
Demand Forecast Router
Provides 15-minute slot forecast bands (P50/P80/P90) vs actual arrivals.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

from core.schemas import DemandResponse, DemandSlot

router = APIRouter(tags=["Demand"])
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@router.get("/demand", response_model=DemandResponse)
def get_demand(
    stop_id: str = Query(..., description="Stop identifier, e.g. S13"),
    date: Optional[str] = Query(default="2026-10-14", description="Date string YYYY-MM-DD")
) -> DemandResponse:
    """Return demand forecast bands (P50, P80, P90) and actual counts for stop_id across morning peak slots."""
    query_date = date or "2026-10-14"

    # Base scale depending on stop type
    if stop_id == "S13": # Metro Station (primary ingress hub)
        base_demand = 60.0
    elif stop_id == "S03": # Central Hub
        base_demand = 45.0
    elif stop_id in ("S08", "S09"): # Hostels
        base_demand = 35.0
    else:
        base_demand = 20.0

    slots: list[DemandSlot] = []
    for slot_start in range(450, 630, 15):
        slot_end = slot_start + 15
        # Morning peak profile peaking around 08:15 (495 min)
        peak_factor = math.exp(-((slot_start - 495.0) ** 2) / (2 * (35.0 ** 2)))
        p50 = round(base_demand * (0.6 + 0.8 * peak_factor), 1)
        p80 = round(p50 * 1.30, 1)
        p90 = round(p50 * 1.45, 1)
        actual = round(p50 * 1.15, 1) if slot_start < 510 else None

        slots.append(DemandSlot(
            slot_start_min=slot_start,
            slot_end_min=slot_end,
            p50_arrivals=p50,
            p80_arrivals=p80,
            p90_arrivals=p90,
            actual_arrivals=actual
        ))

    return DemandResponse(
        stop_id=stop_id,
        date=query_date,
        slots=slots
    )
