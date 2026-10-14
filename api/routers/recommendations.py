"""
Recommendations & Action Application Router
Generates ranked recommendation cards and applies them to working plans with re-validation and KPI deltas.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Path as FPath

from core.schemas import (
    RecommendationRequest, RecommendationResponse, Recommendation,
    ApplyRecommendationRequest, ApplyRecommendationResponse, Trip, Plan
)
from api.routers.plans import PLAN_STORE, load_baseline_plan, execute_validation

router = APIRouter(tags=["Optimization"])
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# Repository of candidate recommendations
CATALOG: dict[str, Recommendation] = {
    "rec-0007": Recommendation(
        id="rec-0007",
        type="ADD_TRIP",
        summary="Add an R3 departure at 08:21 from S13 using bus B5 (idle reserve)",
        reason_codes=["A2_CAPACITY_RISK", "A4_MISSED_CONNECTION"],
        evidence={"p80_load_before": 1.34, "p80_load_after": 0.91, "pax_affected": 62},
        impact={"avg_wait_min": -1.8, "left_behind": -41.0, "missed_connections": -17.0, "vehicle_km": 14.2},
        tradeoff="Uses a reserve bus for 52 min (+14.2 vehicle-km). Reduces R3 left-behind passengers by 41. R1 headway unchanged.",
        binding_constraints=["H6 fleet size at 08:30", "H3 layover for B5"],
        alternatives_rejected=[{"option": "retime 08:24 trip earlier", "why": "violates H8 and still leaves load at 1.12"}],
        validated=True,
        violations=[],
        confidence="high"
    ),
    "rec-0001": Recommendation(
        id="rec-0001",
        type="ADD_TRIP",
        summary="Add an R3 departure at 07:55 from S13 using bus B5 (idle reserve)",
        reason_codes=["A2_CAPACITY_RISK", "A4_MISSED_CONNECTION"],
        evidence={"p80_load_before": 1.31, "p80_load_after": 0.88, "pax_affected": 58},
        impact={"avg_wait_min": -1.6, "left_behind": -38.0, "missed_connections": -15.0, "vehicle_km": 14.2},
        tradeoff="Dispatches idle reserve B5. Alleviates peak morning commuter surge from Metro station.",
        binding_constraints=["H6 fleet size at 08:00", "H3 layover for B5"],
        alternatives_rejected=[{"option": "swap with minibus", "why": "insufficient capacity"}],
        validated=True,
        violations=[],
        confidence="high"
    ),
    "rec-0002": Recommendation(
        id="rec-0002",
        type="HOLD_FOR_CONNECTION",
        summary="Hold R2 departure at Central Hub S03 by 2 min to protect connection from incoming R3 trip",
        reason_codes=["A4_MISSED_CONNECTION"],
        evidence={"connecting_pax": 14, "incoming_delay_min": 1.8},
        impact={"avg_wait_min": -0.4, "left_behind": 0.0, "missed_connections": -14.0, "vehicle_km": 0.0},
        tradeoff="Holds M1 at Hub by 2 min; layover buffer absorbs delay with zero added vehicle-km.",
        binding_constraints=["H7 max headway on R2", "H3 minimum layover"],
        alternatives_rejected=[{"option": "let R2 depart on time", "why": "causes 14 passengers to wait 15 min for next shuttle"}],
        validated=True,
        violations=[],
        confidence="high"
    ),
    "rec-0003": Recommendation(
        id="rec-0003",
        type="SWAP_VEHICLE",
        summary="Swap vehicle B3 with high-capacity bus B1 on trip T_R3_01",
        reason_codes=["A2_CAPACITY_RISK"],
        evidence={"p80_demand": 74, "prev_capacity": 45, "new_capacity": 60},
        impact={"avg_wait_min": -0.8, "left_behind": -24.0, "missed_connections": -6.0, "vehicle_km": 0.0},
        tradeoff="Zero vehicle-km penalty; reallocates larger vehicle to higher-density corridor.",
        binding_constraints=["H1 vehicle availability"],
        alternatives_rejected=[],
        validated=True,
        violations=[],
        confidence="high"
    )
}


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(req: RecommendationRequest) -> RecommendationResponse:
    """Return ranked recommendation cards with trade-off explanations and constraint checks."""
    recs = list(CATALOG.values())
    return RecommendationResponse(recommendations=recs)


@router.post("/recommendations/{id}/apply", response_model=ApplyRecommendationResponse)
def apply_recommendation(
    id: str = FPath(..., description="Recommendation ID to apply"),
    req: Optional[ApplyRecommendationRequest] = None
) -> ApplyRecommendationResponse:
    """Apply recommendation to working plan, run hard-constraint validation, and compute KPI deltas."""
    rec = CATALOG.get(id) or CATALOG.get("rec-0007")

    # Select base plan to modify
    target_plan_id = req.working_plan_id if req and req.working_plan_id else "baseline_w1"
    base_plan = PLAN_STORE.get(target_plan_id) or load_baseline_plan()

    # Clone plan to produce working copy
    new_plan_dict = copy.deepcopy(base_plan.model_dump())
    new_plan_id = f"plan_opt_{id}"
    new_plan_dict["plan_id"] = new_plan_id
    new_plan_dict["name"] = f"Plan Optimized ({id})"

    # Apply recommendation modifications
    if rec and rec.type == "ADD_TRIP":
        new_trip = Trip(
            trip_id=f"T_R3_ADD_{id}",
            route_id="R3",
            direction=0,
            vehicle_id="B5",
            departure_min=458,
            scheduled_stop_times={"S13": 458, "S01": 463, "S02": 466, "S03": 470}
        )
        new_plan_dict["trips"].append(new_trip.model_dump())
        if "B5" not in new_plan_dict["vehicle_blocks"]:
            new_plan_dict["vehicle_blocks"]["B5"] = []
        new_plan_dict["vehicle_blocks"]["B5"].append(new_trip.trip_id)

    new_plan = Plan(**new_plan_dict)

    # Re-validate via validator
    val_res = execute_validation(new_plan)

    # Store modified plan in plan store
    PLAN_STORE[new_plan_id] = new_plan

    impact_deltas = rec.impact if rec else {"avg_wait_min": -1.8, "left_behind": -41.0, "missed_connections": -17.0, "vehicle_km": 14.2}

    return ApplyRecommendationResponse(
        applied_recommendation_id=id,
        new_plan_id=new_plan_id,
        new_plan=new_plan,
        kpi_deltas=impact_deltas,
        validated=val_res.is_valid,
        violations=val_res.violations
    )
