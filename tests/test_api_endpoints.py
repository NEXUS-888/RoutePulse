"""
Comprehensive API Endpoints & Live SSE Replayer Tests
Verifies all Section 10 REST endpoints, SSE stream, CORS headers, and live replayer capabilities.
"""
from __future__ import annotations
import json
import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.schemas import Plan, Trip, GpsPing, ApcRecord
from api.replayer import get_replayer, Replayer

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Health & System
# ---------------------------------------------------------------------------
def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["master_seed"] == 20261014
    assert data["model_hash"] == "models-v1"
    assert "uptime_s" in data
    assert data["uptime_s"] >= 0


# ---------------------------------------------------------------------------
# 2. Network Topology
# ---------------------------------------------------------------------------
def test_network_endpoint():
    res = client.get("/api/network")
    assert res.status_code == 200
    data = res.json()
    assert len(data["stops"]) == 14
    assert len(data["routes"]) == 4
    assert len(data["vehicles"]) == 10
    assert len(data["transfers"]) >= 6

    # Verify Central Hub S03
    hubs = [s for s in data["stops"] if s["is_hub"]]
    assert len(hubs) == 1
    assert hubs[0]["stop_id"] == "S03"

    # Verify linear and loop routes
    route_types = {r["route_id"]: r["type"] for r in data["routes"]}
    assert route_types["R1"] == "loop"
    assert route_types["R2"] == "loop"
    assert route_types["R3"] == "linear"
    assert route_types["R4"] == "linear"


# ---------------------------------------------------------------------------
# 3. Plans & Validation
# ---------------------------------------------------------------------------
def test_plans_get_baseline():
    res = client.get("/api/plans/baseline_w1")
    assert res.status_code == 200
    plan = res.json()
    assert plan["plan_id"] == "baseline_w1"
    assert "trips" in plan
    assert len(plan["trips"]) >= 4
    assert "vehicle_blocks" in plan


def test_plans_validate_valid_plan():
    res_plan = client.get("/api/plans/baseline_w1")
    plan_data = res_plan.json()

    res = client.post("/api/plans/validate", json=plan_data)
    assert res.status_code == 200
    val = res.json()
    assert val["is_valid"] is True
    assert val["hard_violations_count"] == 0


def test_plans_validate_detects_overlapping_trips():
    # Construct invalid plan where vehicle B1 is assigned to two overlapping trips
    bad_plan = {
        "plan_id": "plan_invalid_overlap",
        "name": "Invalid Overlapping Plan",
        "window": ["07:30", "10:30"],
        "trips": [
            {
                "trip_id": "T1",
                "route_id": "R1",
                "direction": 0,
                "vehicle_id": "B1",
                "departure_min": 450,
                "scheduled_stop_times": {"S01": 450, "S02": 455, "S03": 470}
            },
            {
                "trip_id": "T2",
                "route_id": "R1",
                "direction": 0,
                "vehicle_id": "B1",
                "departure_min": 460, # Starts while T1 still in transit!
                "scheduled_stop_times": {"S01": 460, "S02": 465, "S03": 480}
            }
        ],
        "vehicle_blocks": {
            "B1": ["T1", "T2"]
        },
        "metadata": {}
    }

    res = client.post("/api/plans/validate", json=bad_plan)
    assert res.status_code == 200
    val = res.json()
    assert val["is_valid"] is False
    assert val["hard_violations_count"] >= 1
    codes = [v["code"] for v in val["violations"]]
    assert "H2" in codes


# ---------------------------------------------------------------------------
# 4. Live SSE Stream & Status
# ---------------------------------------------------------------------------
def test_live_stream_sse():
    res = client.get("/api/live/stream?speed=60&max_ticks=2")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "event: tick" in text
    assert "data:" in text

    # Parse first data payload
    for line in text.splitlines():
        if line.startswith("data:"):
            payload_str = line.replace("data:", "").strip()
            payload = json.loads(payload_str)
            assert "t_sec" in payload
            assert "time_str" in payload
            assert "active_vehicles" in payload
            assert payload["active_vehicles"] >= 4
            assert "pings" in payload
            assert len(payload["pings"]) >= 4
            break


def test_live_status_and_reset():
    # Status
    res = client.get("/api/live/status")
    assert res.status_code == 200
    st = res.json()
    assert "current_time_sec" in st
    assert "active_vehicles" in st
    assert st["active_vehicles"] >= 4

    # Reset with S1
    res_reset = client.post("/api/live/reset?scenario_id=S1&speed=45")
    assert res_reset.status_code == 200
    assert res_reset.json()["scenario_id"] == "S1"

    # Verify status reflects S1
    st2 = client.get("/api/live/status").json()
    assert st2["scenario_id"] == "S1"
    assert st2["speed"] == 45

    # Reset back to S0
    client.post("/api/live/reset?scenario_id=S0&speed=30")


# ---------------------------------------------------------------------------
# 5. ETA (Stop & Vehicle)
# ---------------------------------------------------------------------------
def test_eta_stop_endpoint():
    res = client.get("/api/eta?stop_id=S03&t=455")
    assert res.status_code == 200
    data = res.json()
    assert data["stop_id"] == "S03"
    assert len(data["arrivals"]) >= 1

    arr0 = data["arrivals"][0]
    assert arr0["eta_p10_min"] <= arr0["eta_p50_min"] <= arr0["eta_p90_min"]
    assert arr0["confidence"] in ("high", "medium", "low")
    assert isinstance(arr0["reasons"], list)


def test_eta_vehicle_endpoint():
    res = client.get("/api/eta/vehicle/B1")
    assert res.status_code == 200
    data = res.json()
    assert data["vehicle_id"] == "B1"
    assert "current_progress_m" in data
    assert "speed_mps" in data
    assert len(data["downstream_stops"]) >= 1
    ds = data["downstream_stops"][0]
    assert ds["eta_p10_min"] <= ds["eta_p50_min"] <= ds["eta_p90_min"]


# ---------------------------------------------------------------------------
# 6. Demand Forecast Bands
# ---------------------------------------------------------------------------
def test_demand_endpoint():
    res = client.get("/api/demand?stop_id=S13&date=2026-10-14")
    assert res.status_code == 200
    data = res.json()
    assert data["stop_id"] == "S13"
    assert data["date"] == "2026-10-14"
    assert len(data["slots"]) >= 8

    # Verify quantile ordering P50 <= P80 <= P90
    for slot in data["slots"]:
        assert slot["p50_arrivals"] <= slot["p80_arrivals"] <= slot["p90_arrivals"]


# ---------------------------------------------------------------------------
# 7. Alerts
# ---------------------------------------------------------------------------
def test_alerts_endpoint():
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)
    assert len(alerts) >= 1

    valid_codes = {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"}
    for a in alerts:
        assert a["code"] in valid_codes
        assert a["severity"] in ("hard-risk", "soft")
        assert a["pax_affected"] >= 0


def test_alerts_filter_by_severity():
    res = client.get("/api/alerts?severity=hard-risk")
    assert res.status_code == 200
    for a in res.json():
        assert a["severity"] == "hard-risk"


# ---------------------------------------------------------------------------
# 8. Recommendations & Apply Action
# ---------------------------------------------------------------------------
def test_recommendations_endpoint():
    res = client.post("/api/recommendations", json={
        "scenario_id": "S0",
        "plan_id": "baseline_w1",
        "current_time_min": 455
    })
    assert res.status_code == 200
    data = res.json()
    recs = data["recommendations"]
    assert len(recs) >= 1

    rec0 = recs[0]
    assert rec0["type"] in ["ADD_TRIP", "RETIME_TRIP", "SWAP_VEHICLE", "HOLD_FOR_CONNECTION"]
    assert "evidence" in rec0
    assert "impact" in rec0
    assert "tradeoff" in rec0
    assert rec0["validated"] is True


def test_apply_recommendation_endpoint():
    res = client.post("/api/recommendations/rec-0007/apply", json={
        "working_plan_id": "baseline_w1"
    })
    assert res.status_code == 200
    applied = res.json()
    assert applied["applied_recommendation_id"] == "rec-0007"
    assert applied["new_plan_id"] == "plan_opt_rec-0007"
    assert applied["validated"] is True
    assert "kpi_deltas" in applied
    assert applied["kpi_deltas"]["left_behind"] < 0 # Proves reduction in left behind

    # Verify newly saved plan can be retrieved
    res_plan = client.get("/api/plans/plan_opt_rec-0007")
    assert res_plan.status_code == 200
    new_plan = res_plan.json()
    assert new_plan["plan_id"] == "plan_opt_rec-0007"
    assert len(new_plan["trips"]) > len(client.get("/api/plans/baseline_w1").json()["trips"])


# ---------------------------------------------------------------------------
# 9. What-If Simulation
# ---------------------------------------------------------------------------
def test_whatif_endpoint():
    req_body = {
        "base_plan_id": "baseline_w1",
        "scenario_id": "S0",
        "added_trips": [
            {
                "trip_id": "T_WHATIF_01",
                "route_id": "R3",
                "direction": 0,
                "vehicle_id": "B5",
                "departure_min": 458,
                "scheduled_stop_times": {"S13": 458, "S01": 463, "S02": 466, "S03": 470}
            }
        ],
        "retimed_trips": {"T_R2_01": 2},
        "vehicle_swaps": {"T_R3_01": "B6"}
    }
    res = client.post("/api/whatif", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["validated"] is True
    assert "simulated_kpis" in data
    assert "delta_vs_base" in data
    assert data["delta_vs_base"]["left_behind_pax"] < 0

    # Also verify that assigning a busy vehicle triggers H2 violation
    conflict_body = dict(req_body)
    conflict_body["vehicle_swaps"] = {"T_R3_01": "B1"} # B1 is already busy running T_R1_01
    res_conflict = client.post("/api/whatif", json=conflict_body)
    assert res_conflict.status_code == 200
    assert res_conflict.json()["validated"] is False
    assert any(v["code"] == "H2" for v in res_conflict.json()["violations"])


# ---------------------------------------------------------------------------
# 10. Scenario Runs
# ---------------------------------------------------------------------------
def test_scenarios_run_endpoints():
    for sid in ("S0", "S1", "S2", "S3"):
        res = client.post(f"/api/scenarios/{sid}/run", json={
            "plan_id": "baseline_w1",
            "seed": 20261014
        })
        assert res.status_code == 200
        data = res.json()
        assert data["scenario_id"] == sid
        assert data["seed"] == 20261014
        assert "kpis" in data
        assert "mean_wait_min" in data["kpis"]
        assert "left_behind_pax" in data["kpis"]


# ---------------------------------------------------------------------------
# 11. Evaluation Results
# ---------------------------------------------------------------------------
def test_eval_results_endpoint():
    res = client.get("/api/eval/results")
    assert res.status_code == 200
    data = res.json()
    assert "summary_table" in data
    assert len(data["summary_table"]) >= 4
    assert "scenarios" in data
    assert "chart_paths" in data
    assert len(data["chart_paths"]) >= 2


# ---------------------------------------------------------------------------
# 12. Ingest Feeds (GPS & APC)
# ---------------------------------------------------------------------------
def test_ingest_gps_endpoint():
    body = {
        "pings": [
            {
                "vehicle_id": "B1",
                "t_sec": 27100,
                "lat": 12.9722,
                "lon": 77.5952,
                "speed_mps": 7.8,
                "heading": 85.0
            },
            {
                "vehicle_id": "B3",
                "t_sec": 27100,
                "lat": 12.9692,
                "lon": 77.5902,
                "speed_mps": 6.9,
                "heading": 175.0
            }
        ]
    }
    res = client.post("/api/ingest/gps", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert data["count"] == 2


def test_ingest_apc_endpoint():
    body = {
        "records": [
            {
                "trip_id": "T_R1_01",
                "stop_id": "S03",
                "boardings": 12,
                "alightings": 4,
                "load_after": 36
            }
        ]
    }
    res = client.post("/api/ingest/apc", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert data["count"] == 1


# ---------------------------------------------------------------------------
# 13. Student Route Journey Planner
# ---------------------------------------------------------------------------
def test_student_route_endpoint():
    res = client.get("/api/student/route?from=S13&to=S04&t=460&accessible=true")
    assert res.status_code == 200
    data = res.json()
    assert data["from_stop"] == "S13"
    assert data["to_stop"] == "S04"
    assert len(data["options"]) >= 1

    opt0 = data["options"][0]
    assert opt0["is_transfer"] is True
    assert opt0["transfer_stop"] == "S03"
    assert opt0["transfer_safe_prob"] >= 0.90
    assert opt0["eta_p10_min"] <= opt0["eta_p50_min"] <= opt0["eta_p90_min"]


# ---------------------------------------------------------------------------
# 14. CORS Headers
# ---------------------------------------------------------------------------
def test_cors_headers_present():
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    }
    res = client.options("/api/health", headers=headers)
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers


# ---------------------------------------------------------------------------
# 15. Standalone Replayer Unit Tests
# ---------------------------------------------------------------------------
def test_replayer_unit():
    replayer = Replayer()
    replayer.reset(scenario_id="S0", start_time_min=450, speed=30)
    frame = replayer.step(dt_sec=1.0)
    assert frame["active_vehicles"] >= 4
    assert len(frame["pings"]) >= 4

    # Test stop ETA query
    eta_stop = replayer.get_stop_eta("S03", t_min=455)
    assert len(eta_stop.arrivals) >= 1

    # Test vehicle ETA query
    eta_veh = replayer.get_vehicle_eta("B1", t_min=455)
    assert eta_veh.vehicle_id == "B1"
    assert len(eta_veh.downstream_stops) >= 1
