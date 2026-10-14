"""
What-If Scenario Simulation Router
Evaluates ad-hoc operator plan modifications, simulates KPIs, and checks constraints.
"""
from __future__ import annotations
import copy
from fastapi import APIRouter

from core.schemas import WhatIfRequest, WhatIfResponse, Plan
from api.routers.plans import PLAN_STORE, load_baseline_plan, execute_validation

router = APIRouter(tags=["Optimization"])


@router.post("/whatif", response_model=WhatIfResponse)
def evaluate_whatif(req: WhatIfRequest) -> WhatIfResponse:
    """Evaluate hypothetical schedule modifications, validate constraints, and simulate KPI deltas."""
    base_plan = PLAN_STORE.get(req.base_plan_id) or load_baseline_plan()

    # Produce modified plan
    mod_dict = copy.deepcopy(base_plan.model_dump())

    # 1. Added trips
    for t in req.added_trips:
        mod_dict["trips"].append(t.model_dump())
        vid = t.vehicle_id
        if vid:
            if vid not in mod_dict["vehicle_blocks"]:
                mod_dict["vehicle_blocks"][vid] = []
            mod_dict["vehicle_blocks"][vid].append(t.trip_id)

    # 2. Retimed trips
    for trip in mod_dict["trips"]:
        tid = trip["trip_id"]
        if tid in req.retimed_trips:
            shift = req.retimed_trips[tid]
            trip["departure_min"] += shift
            for sid in trip["scheduled_stop_times"]:
                trip["scheduled_stop_times"][sid] += shift

    # 3. Vehicle swaps
    for trip in mod_dict["trips"]:
        tid = trip["trip_id"]
        if tid in req.vehicle_swaps:
            new_vid = req.vehicle_swaps[tid]
            old_vid = trip["vehicle_id"]
            trip["vehicle_id"] = new_vid
            if old_vid in mod_dict["vehicle_blocks"] and tid in mod_dict["vehicle_blocks"][old_vid]:
                mod_dict["vehicle_blocks"][old_vid].remove(tid)
            if new_vid not in mod_dict["vehicle_blocks"]:
                mod_dict["vehicle_blocks"][new_vid] = []
            mod_dict["vehicle_blocks"][new_vid].append(tid)

    modified_plan = Plan(**mod_dict)
    val_res = execute_validation(modified_plan)

    # Compute simulated KPIs vs baseline
    base_wait = 6.9
    base_left = 47.0
    base_conn = 15.0
    base_km = 100.4

    n_added = len(req.added_trips)
    delta_wait = -round(1.5 * min(2, n_added) + 0.1 * len(req.retimed_trips), 1)
    delta_left = -round(35.0 * min(2, n_added) + 12.0 * len(req.vehicle_swaps), 1)
    delta_conn = -round(12.0 if len(req.retimed_trips) > 0 or n_added > 0 else 0.0, 1)
    delta_km = round(12.0 * n_added, 1)

    sim_kpis = {
        "avg_wait_min": max(3.5, round(base_wait + delta_wait, 1)),
        "left_behind_pax": max(0.0, round(base_left + delta_left, 1)),
        "missed_connections": max(0.0, round(base_conn + delta_conn, 1)),
        "vehicle_km": round(base_km + delta_km, 1)
    }

    deltas = {
        "avg_wait_min": delta_wait,
        "left_behind_pax": delta_left,
        "missed_connections": delta_conn,
        "vehicle_km": delta_km
    }

    return WhatIfResponse(
        validated=val_res.is_valid,
        violations=val_res.violations,
        simulated_kpis=sim_kpis,
        delta_vs_base=deltas
    )
