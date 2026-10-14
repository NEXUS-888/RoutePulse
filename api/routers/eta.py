"""
ETA Prediction Router
Provides stop-level and vehicle-level ETA predictions with P10/P50/P90 windows, confidence, and reasons.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query, Path as FPath

from core.schemas import EtaResponse, VehicleEtaResponse
from api.replayer import get_replayer

router = APIRouter(tags=["ETA"])
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@router.get("/eta", response_model=EtaResponse)
def get_stop_eta(
    stop_id: str = Query(..., description="Stop identifier, e.g. S03"),
    t: Optional[int] = Query(default=455, description="Query time in minutes from midnight")
) -> EtaResponse:
    """Return next arriving vehicles at stop_id with P10/P50/P90 arrival windows and reasoning."""
    replayer = get_replayer()
    eta_res = replayer.get_stop_eta(stop_id, t_min=t)

    # If replayer yields arrivals, return them
    if eta_res.arrivals:
        return eta_res

    # Otherwise fallback to fixture if stop matches S03
    p = FIXTURES_DIR / "eta_stop.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["stop_id"] = stop_id
        data["query_time_min"] = t or 455
        return EtaResponse(**data)

    return eta_res


@router.get("/eta/vehicle/{vehicle_id}", response_model=VehicleEtaResponse)
def get_vehicle_eta(
    vehicle_id: str = FPath(..., description="Vehicle identifier, e.g. B1"),
    t: Optional[int] = Query(default=None, description="Query time in minutes from midnight")
) -> VehicleEtaResponse:
    """Return downstream stop arrivals and current progress for vehicle_id."""
    replayer = get_replayer()
    veh_res = replayer.get_vehicle_eta(vehicle_id, t_min=t)
    if veh_res.downstream_stops:
        return veh_res

    # Fallback to fixture
    p = FIXTURES_DIR / "eta_vehicle.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["vehicle_id"] = vehicle_id
        return VehicleEtaResponse(**data)

    return veh_res
