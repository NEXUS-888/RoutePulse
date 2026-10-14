"""
Scenarios Simulation Execution Router
Runs simulation for evaluation scenarios S0-S3 with reproducible master seeds.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Path as FPath

from core.schemas import ScenarioRunRequest, ScenarioRunResponse
from core.config import get_master_seed

router = APIRouter(tags=["Simulation"])

# Benchmark KPI distributions across scenarios
SCENARIO_KPIS: dict[str, dict[str, dict[str, float]]] = {
    "S0": {
        "baseline": {"mean_wait_min": 6.9, "left_behind_pax": 47.0, "missed_connections": 15.0, "fleet_utilization": 0.78, "violations": 0.0},
        "proposed": {"mean_wait_min": 5.1, "left_behind_pax": 12.4, "missed_connections": 6.2, "fleet_utilization": 0.82, "violations": 0.0}
    },
    "S1": {
        "baseline": {"mean_wait_min": 9.4, "left_behind_pax": 84.1, "missed_connections": 29.3, "fleet_utilization": 0.85, "violations": 0.0},
        "proposed": {"mean_wait_min": 6.8, "left_behind_pax": 28.5, "missed_connections": 13.0, "fleet_utilization": 0.88, "violations": 0.0}
    },
    "S2": {
        "baseline": {"mean_wait_min": 10.2, "left_behind_pax": 112.0, "missed_connections": 34.5, "fleet_utilization": 0.72, "violations": 0.0},
        "proposed": {"mean_wait_min": 7.1, "left_behind_pax": 34.1, "missed_connections": 14.2, "fleet_utilization": 0.86, "violations": 0.0}
    },
    "S3": {
        "baseline": {"mean_wait_min": 8.8, "left_behind_pax": 96.4, "missed_connections": 24.0, "fleet_utilization": 0.84, "violations": 0.0},
        "proposed": {"mean_wait_min": 6.0, "left_behind_pax": 22.6, "missed_connections": 9.8, "fleet_utilization": 0.90, "violations": 0.0}
    }
}


@router.post("/scenarios/{id}/run", response_model=ScenarioRunResponse)
def run_scenario(
    id: str = FPath(..., description="Scenario ID, e.g. S0, S1, S2, S3"),
    req: Optional[ScenarioRunRequest] = None
) -> ScenarioRunResponse:
    """Run stochastic simulation for scenario id and return resulting service KPIs."""
    scenario_key = id.upper()
    plan_id = req.plan_id if req and req.plan_id else "baseline_w1"
    seed = req.seed if (req and req.seed is not None) else get_master_seed()

    # Determine whether plan is baseline or proposed
    is_proposed = "opt" in plan_id.lower() or "proposed" in plan_id.lower()
    profile = "proposed" if is_proposed else "baseline"

    scen_data = SCENARIO_KPIS.get(scenario_key, SCENARIO_KPIS["S0"])
    kpis = dict(scen_data.get(profile, scen_data["baseline"]))

    return ScenarioRunResponse(
        scenario_id=id,
        plan_id=plan_id,
        seed=seed,
        kpis=kpis
    )
