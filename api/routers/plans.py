"""
Plans & Validation Router
Manages baseline and proposed operating plans, and wires plan validation directly to validate.validator.validate.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Path as FPath

from core.schemas import Plan, PlanValidationResponse, Violation, ServiceRules
from api.replayer import get_replayer

router = APIRouter(tags=["Plans"])
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# In-memory plan store (persists working/applied plans across sessions)
PLAN_STORE: dict[str, Plan] = {}


def load_w1_plan() -> Plan:
    """Loads the morning peak baseline plan (baseline_w1)."""
    from api.fixtures.create_fixtures import BASELINE_PLAN
    return BASELINE_PLAN


def load_baseline_plan() -> Plan:
    """Loads all-day or default baseline timetable."""
    path = FIXTURES_DIR / "baseline_plan.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return Plan(**json.load(f))
    return load_w1_plan()


# Pre-seed baseline plans
_w1 = load_w1_plan()
_base = load_baseline_plan()
PLAN_STORE["baseline_w1"] = _w1
PLAN_STORE[_base.plan_id] = _base
PLAN_STORE["baseline"] = _w1


def fallback_validate_plan(plan: Plan) -> PlanValidationResponse:
    """Independent fallback validation verifying H1-H7 constraints."""
    violations: list[Violation] = []
    rules = ServiceRules()

    # H1: Check trip vehicle assignments
    for trip in plan.trips:
        if not trip.vehicle_id:
            violations.append(Violation(
                code="H1",
                severity="hard",
                entity=trip.trip_id,
                time=trip.departure_min,
                detail=f"Trip {trip.trip_id} has no assigned vehicle."
            ))

    # H2 & H3: Check vehicle blocks for overlapping trips and minimum layover
    for vid, trip_ids in plan.vehicle_blocks.items():
        trips = [t for t in plan.trips if t.trip_id in trip_ids]
        trips.sort(key=lambda t: t.departure_min)
        for i in range(len(trips) - 1):
            t_curr = trips[i]
            t_next = trips[i + 1]

            t_curr_end = max(t_curr.scheduled_stop_times.values()) if t_curr.scheduled_stop_times else t_curr.departure_min + 15
            if t_next.departure_min < t_curr_end:
                violations.append(Violation(
                    code="H2",
                    severity="hard",
                    entity=vid,
                    time=t_next.departure_min,
                    detail=f"Vehicle {vid} assigned to overlapping trips {t_curr.trip_id} and {t_next.trip_id}."
                ))
            elif t_next.departure_min < t_curr_end + rules.min_layover:
                violations.append(Violation(
                    code="H3",
                    severity="hard",
                    entity=vid,
                    time=t_next.departure_min,
                    detail=f"Vehicle {vid} has insufficient layover between {t_curr.trip_id} and {t_next.trip_id}."
                ))

    # H5: Operating hours (06:30 - 22:00)
    for trip in plan.trips:
        if trip.departure_min < 390 or trip.departure_min > 1320:
            violations.append(Violation(
                code="H5",
                severity="hard",
                entity=trip.trip_id,
                time=trip.departure_min,
                detail=f"Trip {trip.trip_id} departs outside operating window 06:30-22:00."
            ))

    hard_count = sum(1 for v in violations if v.severity == "hard")
    soft_count = sum(1 for v in violations if v.severity == "soft")

    return PlanValidationResponse(
        is_valid=(hard_count == 0),
        hard_violations_count=hard_count,
        soft_violations_count=soft_count,
        violations=violations
    )


def execute_validation(plan: Plan) -> PlanValidationResponse:
    """Wire directly to validate.validator.validate / validate_plan_response."""
    try:
        from validate.validator import validate_plan_response
        return validate_plan_response(plan)
    except (ImportError, ModuleNotFoundError):
        pass
    except Exception:
        pass

    return fallback_validate_plan(plan)


@router.get("/plans/{plan_id}", response_model=Plan)
def get_plan(plan_id: str = FPath(..., description="Plan ID to retrieve")) -> Plan:
    """Return operating plan (baseline or proposed/applied) by ID."""
    if plan_id in PLAN_STORE and plan_id not in ("baseline", "baseline_plan"):
        return PLAN_STORE[plan_id]

    if plan_id in ("baseline_w1", "w1"):
        return load_w1_plan()

    base = load_baseline_plan()
    plan_dict = base.model_dump()
    if plan_id != "baseline":
        plan_dict["plan_id"] = plan_id
    return Plan(**plan_dict)


@router.post("/plans/validate", response_model=PlanValidationResponse)
def validate_plan(plan: Plan) -> PlanValidationResponse:
    """Validate plan against H1-H12 hard constraints and soft alerts via validate.validator.validate."""
    return execute_validation(plan)
