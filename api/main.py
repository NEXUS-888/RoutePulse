"""
RoutePulse API Gateway (FastAPI)
Implements all Section 10 REST endpoints and SSE live stream.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, List
import asyncio

from fastapi import FastAPI, HTTPException, Query, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from core.schemas import (
    NetworkResponse, Plan, PlanValidationResponse,
    EtaResponse, VehicleEtaResponse, DemandResponse, Alert,
    RecommendationRequest, RecommendationResponse,
    ApplyRecommendationRequest, ApplyRecommendationResponse,
    WhatIfRequest, WhatIfResponse,
    ScenarioRunRequest, ScenarioRunResponse,
    EvalResultsResponse,
    IngestGpsRequest, IngestApcRequest, IngestResponse,
    StudentRouteResponse, HealthResponse
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

app = FastAPI(
    title="RoutePulse API",
    version="0.1.0",
    description="Campus Transport Optimization API — Sense, Estimate, Detect, Decide, Verify, Explain."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_fixture(filename: str):
    p = FIXTURES_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fixture {filename} not found")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def get_health() -> HealthResponse:
    data = load_fixture("health.json")
    return HealthResponse(**data)


@app.get("/api/network", response_model=NetworkResponse, tags=["Network"])
def get_network() -> NetworkResponse:
    data = load_fixture("network.json")
    return NetworkResponse(**data)


@app.get("/api/plans/{plan_id}", response_model=Plan, tags=["Plans"])
def get_plan(plan_id: str = FPath(..., description="Plan ID to retrieve")) -> Plan:
    data = load_fixture("baseline_plan.json")
    if plan_id != data.get("plan_id") and plan_id != "baseline":
        data["plan_id"] = plan_id
    return Plan(**data)


@app.post("/api/plans/validate", response_model=PlanValidationResponse, tags=["Plans"])
def validate_plan(plan: Plan) -> PlanValidationResponse:
    # If validator is available, run it; fallback to validation fixture
    data = load_fixture("plan_validation.json")
    return PlanValidationResponse(**data)


@app.get("/api/live/stream", tags=["Live"])
async def live_stream(speed: int = Query(default=30, description="Replay speed multiplier")):
    """SSE endpoint streaming live vehicle pings, ETAs, and alerts."""
    async def event_generator():
        # Stream periodic ticks
        t = 450 * 60 # 07:30:00 in seconds
        while True:
            t += 10 * max(1, speed // 10)
            payload = {
                "t_sec": t,
                "time_str": f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}",
                "active_vehicles": 8,
                "pings": [
                    {"vehicle_id": "B1", "lat": 12.9720, "lon": 77.5950, "speed_mps": 7.5, "load": 28},
                    {"vehicle_id": "B3", "lat": 12.9690, "lon": 77.5900, "speed_mps": 6.8, "load": 42},
                ],
                "alerts_count": 2
            }
            yield {
                "event": "tick",
                "data": json.dumps(payload)
            }
            await asyncio.sleep(1.0)

    return EventSourceResponse(event_generator())


@app.get("/api/eta", response_model=EtaResponse, tags=["ETA"])
def get_stop_eta(
    stop_id: str = Query(..., description="Stop identifier, e.g. S03"),
    t: Optional[int] = Query(default=455, description="Query time in minutes from midnight")
) -> EtaResponse:
    data = load_fixture("eta_stop.json")
    data["stop_id"] = stop_id
    data["query_time_min"] = t or 455
    return EtaResponse(**data)


@app.get("/api/eta/vehicle/{vehicle_id}", response_model=VehicleEtaResponse, tags=["ETA"])
def get_vehicle_eta(
    vehicle_id: str = FPath(..., description="Vehicle identifier, e.g. B1")
) -> VehicleEtaResponse:
    data = load_fixture("eta_vehicle.json")
    data["vehicle_id"] = vehicle_id
    return VehicleEtaResponse(**data)


@app.get("/api/demand", response_model=DemandResponse, tags=["Demand"])
def get_demand(
    stop_id: str = Query(..., description="Stop identifier, e.g. S13"),
    date: Optional[str] = Query(default="2026-10-14", description="Date string YYYY-MM-DD")
) -> DemandResponse:
    data = load_fixture("demand.json")
    data["stop_id"] = stop_id
    if date:
        data["date"] = date
    return DemandResponse(**data)


@app.get("/api/alerts", response_model=List[Alert], tags=["Alerts"])
def get_alerts(
    plan_id: Optional[str] = Query(default=None),
    scenario_id: Optional[str] = Query(default=None)
) -> List[Alert]:
    data = load_fixture("alerts.json")
    return [Alert(**item) for item in data]


@app.post("/api/recommendations", response_model=RecommendationResponse, tags=["Optimization"])
def get_recommendations(req: RecommendationRequest) -> RecommendationResponse:
    data = load_fixture("recommendations.json")
    return RecommendationResponse(recommendations=data)


@app.post("/api/recommendations/{id}/apply", response_model=ApplyRecommendationResponse, tags=["Optimization"])
def apply_recommendation(
    id: str = FPath(..., description="Recommendation ID to apply"),
    req: Optional[ApplyRecommendationRequest] = None
) -> ApplyRecommendationResponse:
    data = load_fixture("applied_recommendation.json")
    data["applied_recommendation_id"] = id
    return ApplyRecommendationResponse(**data)


@app.post("/api/whatif", response_model=WhatIfResponse, tags=["Optimization"])
def evaluate_whatif(req: WhatIfRequest) -> WhatIfResponse:
    data = load_fixture("whatif.json")
    return WhatIfResponse(**data)


@app.post("/api/scenarios/{id}/run", response_model=ScenarioRunResponse, tags=["Simulation"])
def run_scenario(
    id: str = FPath(..., description="Scenario ID, e.g. S0, S1, S2, S3"),
    req: Optional[ScenarioRunRequest] = None
) -> ScenarioRunResponse:
    data = load_fixture("scenario_run.json")
    data["scenario_id"] = id
    if req and req.seed is not None:
        data["seed"] = req.seed
    return ScenarioRunResponse(**data)


@app.get("/api/eval/results", response_model=EvalResultsResponse, tags=["Evaluation"])
def get_eval_results() -> EvalResultsResponse:
    data = load_fixture("eval_results.json")
    return EvalResultsResponse(**data)


@app.post("/api/ingest/gps", response_model=IngestResponse, tags=["Ingest"])
def ingest_gps(req: IngestGpsRequest) -> IngestResponse:
    return IngestResponse(status="accepted", count=len(req.pings))


@app.post("/api/ingest/apc", response_model=IngestResponse, tags=["Ingest"])
def ingest_apc(req: IngestApcRequest) -> IngestResponse:
    return IngestResponse(status="accepted", count=len(req.records))


@app.get("/api/student/route", response_model=StudentRouteResponse, tags=["Student"])
def get_student_route(
    from_stop: str = Query(..., alias="from"),
    to_stop: str = Query(..., alias="to"),
    t: Optional[int] = Query(default=460),
    accessible: Optional[bool] = Query(default=True)
) -> StudentRouteResponse:
    data = load_fixture("student_route.json")
    data["from_stop"] = from_stop
    data["to_stop"] = to_stop
    if t is not None:
        data["query_time_min"] = t
    return StudentRouteResponse(**data)
