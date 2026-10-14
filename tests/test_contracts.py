"""
Contract and Schema Tests for RoutePulse
Tests schemas, fixtures, and API endpoint contracts.
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from core.schemas import (
    Stop, Route, Vehicle, Trip, Plan, GpsPing, ApcRecord,
    DemandObs, Event, Transfer, ServiceRules, Scenario,
    Disruption, Recommendation, Violation, Alert,
    NetworkResponse, EtaResponse, VehicleEtaResponse,
    DemandResponse, PlanValidationResponse, ApplyRecommendationResponse,
    WhatIfResponse, ScenarioRunResponse, EvalResultsResponse,
    StudentRouteResponse, HealthResponse
)
from core.config import load_config, get_master_seed
from api.main import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT_DIR / "api" / "fixtures"


def test_master_seed():
    seed = get_master_seed()
    assert seed == 20261014


def test_config_rules():
    cfg = load_config()
    assert "rules" in cfg
    assert cfg["rules"]["min_headway"] == 3
    assert cfg["rules"]["min_layover"] == 4
    assert cfg["rules"]["max_continuous_drive_min"] == 210


def test_fixtures_against_schemas():
    # Network fixture
    with open(FIXTURES_DIR / "network.json", "r", encoding="utf-8") as f:
        net_data = json.load(f)
    net = NetworkResponse(**net_data)
    assert len(net.stops) == 14
    assert len(net.routes) == 4
    assert len(net.vehicles) == 10
    assert any(s.is_hub and s.stop_id == "S03" for s in net.stops)

    # Baseline plan fixture
    with open(FIXTURES_DIR / "baseline_plan.json", "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    plan = Plan(**plan_data)
    assert plan.plan_id.startswith("baseline")
    assert len(plan.trips) > 0

    # ETA fixture
    with open(FIXTURES_DIR / "eta_stop.json", "r", encoding="utf-8") as f:
        eta_data = json.load(f)
    eta = EtaResponse(**eta_data)
    assert len(eta.arrivals) > 0
    assert eta.arrivals[0].eta_p10_min <= eta.arrivals[0].eta_p50_min <= eta.arrivals[0].eta_p90_min

    # Alerts fixture
    with open(FIXTURES_DIR / "alerts.json", "r", encoding="utf-8") as f:
        alerts_data = json.load(f)
    alerts = [Alert(**a) for a in alerts_data]
    assert len(alerts) >= 2
    assert any(a.code == "A2" for a in alerts)

    # Recommendations fixture
    with open(FIXTURES_DIR / "recommendations.json", "r", encoding="utf-8") as f:
        recs_data = json.load(f)
    recs = [Recommendation(**r) for r in recs_data]
    assert len(recs) >= 1
    assert recs[0].type == "ADD_TRIP"
    assert recs[0].validated is True
    assert len(recs[0].violations) == 0

    # Health fixture
    with open(FIXTURES_DIR / "health.json", "r", encoding="utf-8") as f:
        health_data = json.load(f)
    h = HealthResponse(**health_data)
    assert h.status == "ok"


def test_api_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["master_seed"] == 20261014


def test_api_network_endpoint():
    res = client.get("/api/network")
    assert res.status_code == 200
    data = res.json()
    assert len(data["stops"]) == 14
    assert len(data["routes"]) == 4


def test_api_plans_endpoint():
    res = client.get("/api/plans/baseline_w1")
    assert res.status_code == 200
    plan = res.json()
    assert plan["plan_id"] == "baseline_w1"


def test_api_eta_endpoint():
    res = client.get("/api/eta?stop_id=S03&t=455")
    assert res.status_code == 200
    data = res.json()
    assert data["stop_id"] == "S03"
    assert len(data["arrivals"]) >= 1


def test_api_alerts_endpoint():
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)
    assert len(alerts) >= 1


def test_api_recommendations_endpoint():
    res = client.post("/api/recommendations", json={
        "scenario_id": "S0",
        "plan_id": "baseline_w1",
        "current_time_min": 455
    })
    assert res.status_code == 200
    data = res.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1


def test_api_student_route_endpoint():
    res = client.get("/api/student/route?from=S13&to=S04&t=460&accessible=true")
    assert res.status_code == 200
    data = res.json()
    assert data["from_stop"] == "S13"
    assert len(data["options"]) >= 1


def test_schema_rejection_invalid_capacity():
    with pytest.raises(Exception):
        Vehicle(
            vehicle_id="BAD",
            type="bus",
            capacity=-10,  # Invalid: capacity must be > 0
            seated=10,
            accessible=True
        )


def test_schema_rejection_invalid_route_speed():
    with pytest.raises(Exception):
        Route(
            route_id="R_BAD",
            name="Bad Route",
            type="linear",
            stop_sequence=["S01", "S02"],
            polyline=[[0, 0], [10, 10]],
            segment_lengths_m=[14.1],
            free_flow_speed_mps=-5.0 # Invalid: must be > 0
        )
