"""
RoutePulse Adversarial QA & Edge Cases Test Suite (tests/test_adversarial.py)
Owner: Agent A10 (Adversarial QA & Edge Cases Engineer)

Test Coverage:
1. Zero demand edge case:
   - Simulator runs with 0 pax: no crashes, zero left-behind, zero balked, non-negative KPIs.
   - Optimizer (CP-SAT & Heuristic) runs with 0 demand: valid plan, zero hard violations.
2. Massive demand spike edge case:
   - 10x surge at a single stop: system gracefully handles without crashing or emitting negative numbers.
   - Vehicle capacities strictly respected (no physical over-boarding).
3. Fleet exhaustion edge case:
   - All reserve vehicles busy or disabled.
   - CP-SAT and heuristic fallback safely report capacity saturation without invalid vehicle double-booking (H2 violation).
4. Stale GPS fallback edge case:
   - Feed GPS pings older than 180s.
   - Engine marks pings as low_confidence, degrades to carry-forward B1 with widened interval.
5. Malformed API input tests:
   - POST malformed JSON, out-of-range coordinates, invalid route_id to API endpoints.
   - Verify clean 422 Unprocessable Entity or 400 Bad Request responses (no 500 crashes).
6. Disruption superposition:
   - Inject simultaneous traffic delay + vehicle breakdown + demand spike.
   - Re-optimizer yields valid plan with zero hard violations.
7. Baseline plan validation invariant:
   - Assert validate(baseline_plan) returns zero hard violations across all constraints H1..H12.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.schemas import Disruption, GpsPing, NetworkResponse, Plan, Trip, Vehicle
from eta.engine import RoutePulseETA
from eta.gps_processing import PolylineMatcher, map_match_pings, smooth_matched_pings
from optimize.cpsat_model import solve_cpsat_plan
from optimize.heuristic import run_fast_heuristic
from optimize.rolling import RollingHorizonOptimizer
from sim.engine import Passenger, Simulator, load_default_network
from validate.constraints import (
    check_h1,
    check_h2,
    check_h3,
    check_h4,
    check_h5,
    check_h6,
    check_h7,
    check_h8,
    check_h9,
    check_h10,
    check_h11,
    check_h12,
    normalize_fleet,
    normalize_rules,
)
from validate.validator import is_valid_plan, validate

ROOT_DIR = Path(__file__).resolve().parent.parent
BASELINE_PLAN_PATH = ROOT_DIR / "config" / "baseline_plan.json"
NETWORK_PATH = ROOT_DIR / "api" / "fixtures" / "network.json"
ARTIFACTS_DIR = ROOT_DIR / "data" / "eta_artifacts"


@pytest.fixture(scope="module")
def baseline_plan() -> Plan:
    with open(BASELINE_PLAN_PATH, "r", encoding="utf-8") as f:
        return Plan(**json.load(f))


@pytest.fixture(scope="module")
def network() -> NetworkResponse:
    return load_default_network()


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Zero Demand Edge Case
# ---------------------------------------------------------------------------
class TestZeroDemandEdgeCase:
    def test_simulator_zero_demand(self, baseline_plan: Plan, network: NetworkResponse):
        """
        Verify simulator handles 0 passengers gracefully:
        - No unhandled exceptions or zero-division errors.
        - Zero left-behind, zero balked, zero unmet demand.
        - All KPIs valid and non-negative.
        """
        sim = Simulator(network=network)
        result = sim.run(plan=baseline_plan, demand=[])

        assert result is not None
        assert result.kpis["left_behind_pax"] == 0.0
        assert result.kpis["unmet_demand_pax"] == 0.0
        assert result.kpis["balked_pax"] == 0.0
        assert result.kpis["missed_connections"] == 0.0
        assert result.kpis["seat_km_used"] == 0.0
        assert result.kpis["fleet_utilization"] == 0.0
        assert result.kpis["mean_wait_min"] == 0.0
        assert result.kpis["median_wait_min"] == 0.0
        assert result.kpis["p95_wait_min"] == 0.0

        # APC records generated with 0 boardings/alightings
        assert len(result.apc_records) > 0
        for rec in result.apc_records:
            assert rec.boardings == 0
            assert rec.alightings == 0
            assert rec.load_after == 0

    def test_optimizer_cpsat_zero_demand(self, baseline_plan: Plan):
        """
        Verify CP-SAT optimizer operates cleanly with zero forecast demand:
        - Produces feasible timetable.
        - 0 hard violations.
        """
        zero_demand = {("R1", 30): 0.0, ("R2", 30): 0.0, ("R3", 30): 0.0, ("R4", 30): 0.0}
        res = solve_cpsat_plan(
            current_plan=baseline_plan,
            window=(450, 480),
            p80_demand=zero_demand,
            time_limit_s=5.0,
        )

        assert res.hard_violations_count == 0
        assert is_valid_plan(res.plan) is True

    def test_optimizer_heuristic_zero_demand(self, baseline_plan: Plan):
        """
        Verify fast heuristic fallback operates cleanly with zero demand:
        - Does not add redundant trips.
        - 0 hard violations.
        """
        zero_demand = {("R3", 30): 0.0, ("R1", 30): 0.0}
        res = run_fast_heuristic(
            baseline_plan,
            window=(450, 480),
            p80_demand=zero_demand,
        )

        assert res.hard_violations_count == 0
        assert len(res.added_trips) == 0
        assert is_valid_plan(res.plan) is True


# ---------------------------------------------------------------------------
# 2. Massive Demand Spike Edge Case
# ---------------------------------------------------------------------------
class TestMassiveDemandSpikeEdgeCase:
    def test_simulator_10x_demand_surge_at_single_stop(self, baseline_plan: Plan, network: NetworkResponse):
        """
        Verify simulator handles 10x demand spike (600 passengers) at stop S13:
        - No crashes, NaN, or negative KPI numbers.
        - Boardings strictly capped at vehicle capacity (no physical overcrowding).
        - Accurately tracks left-behind passengers.
        """
        # Baseline normal flow at S13 is ~60 pax. Inject 10x surge = 600 passengers.
        surge_pax = [
            Passenger(
                pax_id=f"SURGE_{i:04d}",
                origin="S13",
                destination="S03",
                arrival_time_min=450.0 + (i * 0.015),
                route_id="R3",
                direction=0,
            )
            for i in range(600)
        ]

        sim = Simulator(network=network)
        result = sim.run(plan=baseline_plan, demand=surge_pax)

        assert result is not None

        # Verify all KPI values are non-negative
        for k, v in result.kpis.items():
            if isinstance(v, (int, float)):
                assert v >= 0.0, f"KPI '{k}' has negative value: {v}"

        # Left-behind count must be accurately positive
        assert result.kpis["left_behind_pax"] > 0

        # Physical capacity safety: vehicle boardings must NEVER exceed rated capacity
        for tm in result.trip_metrics.values():
            assert tm.max_load <= tm.capacity, (
                f"Trip {tm.trip_id} exceeded rated capacity! Max load: {tm.max_load}, Capacity: {tm.capacity}"
            )

        # APC load_after must always be non-negative
        for rec in result.apc_records:
            assert rec.boardings >= 0
            assert rec.alightings >= 0
            assert rec.load_after >= 0

    def test_rolling_optimizer_graceful_handling_under_massive_surge(self, baseline_plan: Plan):
        """
        Verify RollingHorizonOptimizer responds to 1,000 pax surge at S07 without crashing or emitting negative numbers.
        """
        d_spike = Disruption(
            type="demand_spike",
            params={"stop_id": "S07", "surge_passengers": 1000},
            start_min=1050,
            end_min=1075,
        )
        opt = RollingHorizonOptimizer()
        step_res = opt.step(current_time_min=1050, current_plan=baseline_plan, disruption=d_spike)

        assert step_res.hard_violations_count == 0
        assert is_valid_plan(step_res.plan) is True
        assert len(step_res.added_trips) >= 1

        # Check recommendation impact values are valid numbers
        for rec in step_res.recommendations:
            assert rec.impact["avg_wait_min"] is not None
            assert rec.impact["left_behind"] is not None


# ---------------------------------------------------------------------------
# 3. Fleet Exhaustion Edge Case
# ---------------------------------------------------------------------------
class TestFleetExhaustionEdgeCase:
    def test_cpsat_fleet_exhaustion_no_double_booking(self, baseline_plan: Plan):
        """
        Verify that when all reserve vehicles (B5, B6, M4) are disabled or busy:
        - CP-SAT solver does not crash.
        - Does NOT double-book any vehicle to meet unmet demand (H2 violation).
        - Plan remains 100% hard-constraint valid.
        """
        # Overload route R3 while disabling all reserve vehicles
        exhausted_reserves = {"B5", "B6", "M4"}
        p80_overload = {("R3", 30): 150.0}

        res = solve_cpsat_plan(
            current_plan=baseline_plan,
            window=(450, 480),
            p80_demand=p80_overload,
            disrupted_vehicles=exhausted_reserves,
            time_limit_s=5.0,
        )

        assert res.hard_violations_count == 0
        assert is_valid_plan(res.plan) is True

        # Check vehicle assignments: none of the disabled reserves are assigned
        for trip in res.plan.trips:
            assert trip.vehicle_id not in exhausted_reserves, (
                f"Disabled reserve vehicle {trip.vehicle_id} was assigned to trip {trip.trip_id}!"
            )

        # H2 Invariant: No vehicle overlap
        viols = validate(res.plan)
        h2_viols = [v for v in viols if v.code == "H2" and v.severity == "hard"]
        assert len(h2_viols) == 0, f"H2 vehicle overlap violation detected: {h2_viols}"

    def test_heuristic_fleet_exhaustion_reports_saturation(self, baseline_plan: Plan):
        """
        Verify greedy heuristic fallback reports saturation and avoids illegal vehicle double-booking.
        """
        res = run_fast_heuristic(
            baseline_plan,
            window=(450, 480),
            p80_demand={("R3", 31): 120.0},
            reserve_vehicles=[],  # Exhausted: no reserves available
        )

        assert res.hard_violations_count == 0
        assert len(res.added_trips) == 0, "Heuristic must not fabricate trips when reserve fleet is exhausted"
        assert is_valid_plan(res.plan) is True


# ---------------------------------------------------------------------------
# 4. Stale GPS Fallback Edge Case
# ---------------------------------------------------------------------------
class TestStaleGpsFallbackEdgeCase:
    def test_gps_processing_marks_stale_pings_as_low_confidence(self):
        """
        Verify GPS processing marks pings with gaps > 180s as low_confidence.
        """
        polyline = [[0.0, 0.0], [500.0, 200.0], [1000.0, 500.0]]
        matcher = PolylineMatcher(polyline)

        # Sequence of pings with a 200-second outage gap (> 180s)
        pings = [
            {"t_sec": 100, "x": 10.0, "y": 5.0, "speed_mps": 10.0},
            {"t_sec": 110, "x": 100.0, "y": 40.0, "speed_mps": 10.0},
            {"t_sec": 310, "x": 600.0, "y": 280.0, "speed_mps": 10.0},  # 200s gap!
            {"t_sec": 320, "x": 700.0, "y": 330.0, "speed_mps": 10.0},
        ]

        matched = map_match_pings(pings, polyline)
        smoothed = smooth_matched_pings(matched, max_gap_s=60.0)

        assert len(smoothed) == 4
        # Pings after the 200s gap must be flagged as low_confidence
        assert smoothed[2]["low_confidence"] is True
        assert smoothed[2]["quality_flag"] == "low_confidence"

    def test_eta_engine_stale_gps_degradation_and_widening(self, baseline_plan: Plan, network: NetworkResponse):
        """
        Verify that feeding GPS ping age older than 180s (e.g. 200s):
        1. Sets stale_gps = True.
        2. Sets confidence = 'low'.
        3. Degrades to B1 carry-forward.
        4. Widens interval compared to fresh GPS.
        5. Maintains query_time <= p10 <= p50 <= p90 ordering with no NaNs.
        """
        engine = RoutePulseETA(ARTIFACTS_DIR)
        trip = baseline_plan.trips[0]
        route = next(r for r in network.routes if r.route_id == trip.route_id)
        curr_stop = route.stop_sequence[0]
        q_time = float(trip.departure_min)

        # Fresh GPS (< 120s)
        fresh_preds = engine.predict_downstream_etas(
            trip=trip,
            route=route,
            current_stop_id=curr_stop,
            query_time_min=q_time,
            current_delay_min=1.0,
            gps_age_s=15.0,
        )

        # Stale GPS (> 180s, e.g. 200s)
        stale_preds = engine.predict_downstream_etas(
            trip=trip,
            route=route,
            current_stop_id=curr_stop,
            query_time_min=q_time,
            current_delay_min=1.0,
            gps_age_s=200.0,
        )

        assert len(fresh_preds) > 0
        assert len(stale_preds) > 0

        p_fresh = fresh_preds[0]
        p_stale = stale_preds[0]

        assert p_fresh.stale_gps is False
        assert p_fresh.confidence in ("high", "medium")

        assert p_stale.stale_gps is True
        assert p_stale.confidence == "low"
        assert any("stale" in r.lower() for r in p_stale.reasons)
        assert any("b1" in r.lower() for r in p_stale.reasons)

        # Interval widening check
        fresh_width = p_fresh.eta_p90_min - p_fresh.eta_p10_min
        stale_width = p_stale.eta_p90_min - p_stale.eta_p10_min
        assert stale_width > fresh_width

        # Monotonicity and valid ordering
        for pred in stale_preds:
            assert q_time <= pred.eta_p10_min <= pred.eta_p50_min <= pred.eta_p90_min
            assert not np.isnan(pred.eta_p50_min)


# ---------------------------------------------------------------------------
# 5. Malformed API Input Tests
# ---------------------------------------------------------------------------
class TestMalformedApiInputs:
    def test_post_malformed_json_returns_422(self, api_client: TestClient):
        """
        Verify that POSTing malformed/unparseable JSON returns clean 422 Unprocessable Entity (no 500 crash).
        """
        headers = {"Content-Type": "application/json"}

        # 1. /api/plans/validate
        res1 = api_client.post("/api/plans/validate", content="{not a valid json payload", headers=headers)
        assert res1.status_code in (400, 422), f"Expected 400 or 422, got {res1.status_code}"

        # 2. /api/whatif
        res2 = api_client.post("/api/whatif", content="[invalid: json, data", headers=headers)
        assert res2.status_code in (400, 422), f"Expected 400 or 422, got {res2.status_code}"

        # 3. /api/ingest/gps
        res3 = api_client.post("/api/ingest/gps", content="<xml>not_json</xml>", headers=headers)
        assert res3.status_code in (400, 422), f"Expected 400 or 422, got {res3.status_code}"

        # 4. /api/recommendations
        res4 = api_client.post("/api/recommendations", content="null:", headers=headers)
        assert res4.status_code in (400, 422), f"Expected 400 or 422, got {res4.status_code}"

    def test_post_out_of_range_coordinates_returns_422(self, api_client: TestClient):
        """
        Verify that out-of-range coordinates return clean 422 Unprocessable Entity (no 500 crash).
        """
        # Latitude out of range (> 90.0)
        bad_lat_ping = {
            "pings": [{
                "vehicle_id": "B1",
                "t_sec": 27000,
                "lat": 195.0,  # Invalid: > 90.0
                "lon": 77.5946,
                "speed_mps": 10.0,
                "heading": 0.0,
            }]
        }
        res_lat = api_client.post("/api/ingest/gps", json=bad_lat_ping)
        assert res_lat.status_code == 422, f"Expected 422 for lat=195.0, got {res_lat.status_code}"

        # Longitude out of range (< -180.0)
        bad_lon_ping = {
            "pings": [{
                "vehicle_id": "B1",
                "t_sec": 27000,
                "lat": 12.9716,
                "lon": -250.0,  # Invalid: < -180.0
                "speed_mps": 10.0,
                "heading": 0.0,
            }]
        }
        res_lon = api_client.post("/api/ingest/gps", json=bad_lon_ping)
        assert res_lon.status_code == 422, f"Expected 422 for lon=-250.0, got {res_lon.status_code}"

        # Negative speed
        bad_speed_ping = {
            "pings": [{
                "vehicle_id": "B1",
                "t_sec": 27000,
                "lat": 12.9716,
                "lon": 77.5946,
                "speed_mps": -5.0,  # Invalid: < 0.0
                "heading": 0.0,
            }]
        }
        res_speed = api_client.post("/api/ingest/gps", json=bad_speed_ping)
        assert res_speed.status_code == 422, f"Expected 422 for speed=-5.0, got {res_speed.status_code}"

    def test_post_invalid_route_id_returns_422(self, api_client: TestClient):
        """
        Verify that invalid route_id returns clean 422 Unprocessable Entity (no 500 crash).
        """
        bad_whatif = {
            "base_plan_id": "baseline_w1",
            "scenario_id": "S0",
            "added_trips": [{
                "trip_id": "T_BAD",
                "route_id": "NON_EXISTENT_ROUTE_999",  # Invalid route_id
                "direction": 0,
                "vehicle_id": "B5",
                "departure_min": 460,
                "scheduled_stop_times": {"S01": 460, "S02": 465},
            }],
        }
        res = api_client.post("/api/whatif", json=bad_whatif)
        assert res.status_code == 422, f"Expected 422 for invalid route_id, got {res.status_code}"


# ---------------------------------------------------------------------------
# 6. Disruption Superposition
# ---------------------------------------------------------------------------
class TestDisruptionSuperposition:
    def test_simultaneous_traffic_breakdown_and_spike(self, baseline_plan: Plan):
        """
        Inject simultaneous traffic delay + vehicle breakdown + demand spike.
        Verify that the re-optimizer produces a valid plan with zero hard violations.
        """
        # Shock 1: Traffic congestion on Metro corridor
        d_traffic = Disruption(
            type="traffic",
            params={"multiplier": 1.35, "corridors": ["Metro", "Main Gate"]},
            start_min=480,
            end_min=570,
        )
        # Shock 2: Vehicle B2 breakdown at 08:15 (min 495)
        d_breakdown = Disruption(
            type="vehicle_out",
            params={"vehicle_id": "B2", "reserve_available": True},
            start_min=495,
            end_min=630,
        )
        # Shock 3: Demand spike at S07
        d_spike = Disruption(
            type="demand_spike",
            params={"stop_id": "S07", "surge_passengers": 500},
            start_min=495,
            end_min=520,
        )

        opt = RollingHorizonOptimizer()
        step_res = opt.step(
            current_time_min=495,
            current_plan=baseline_plan,
            disruption=[d_traffic, d_breakdown, d_spike],
        )

        assert step_res.hard_violations_count == 0
        assert is_valid_plan(step_res.plan) is True

        # Invariant 1: Broken vehicle B2 must NOT have trips assigned >= 495 min
        subsequent_b2_trips = [
            t for t in step_res.plan.trips
            if t.departure_min >= 495 and t.vehicle_id == "B2"
        ]
        assert len(subsequent_b2_trips) == 0, "Broken vehicle B2 has trips assigned after failure!"

        # Invariant 2: Full plan validation yields 0 hard violations
        viols = validate(step_res.plan)
        hard_viols = [v for v in viols if v.severity == "hard"]
        assert len(hard_viols) == 0, f"Hard violations found after disruption superposition: {hard_viols}"

        # Invariant 3: H2 non-overlap constraint strictly respected
        h2_viols = [v for v in viols if v.code == "H2" and v.severity == "hard"]
        assert len(h2_viols) == 0, f"H2 overlap violation found: {h2_viols}"


# ---------------------------------------------------------------------------
# 7. Baseline Plan Validation Invariant
# ---------------------------------------------------------------------------
class TestBaselinePlanValidationInvariant:
    def test_baseline_plan_has_zero_hard_violations(self, baseline_plan: Plan):
        """
        Verify that validate(baseline_plan) returns zero hard violations.
        """
        violations = validate(baseline_plan)
        hard_violations = [v for v in violations if v.severity == "hard"]

        assert len(hard_violations) == 0, (
            f"Baseline plan has {len(hard_violations)} hard violation(s):\n"
            + "\n".join(f"  - [{v.code}] {v.detail}" for v in hard_violations)
        )
        assert is_valid_plan(baseline_plan) is True

    def test_baseline_individual_hard_constraints_satisfied(self, baseline_plan: Plan, network: NetworkResponse):
        """
        Explicitly check each individual constraint H1..H12 against baseline_plan.
        """
        fleet = {v.vehicle_id: v for v in network.vehicles}
        fl = normalize_fleet(fleet)
        rules = normalize_rules(None)
        ctx: Dict = {}

        assert len(check_h1(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h2(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h3(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h4(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h5(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h6(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h7(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h8(baseline_plan, fl, rules, ctx, baseline_plan=baseline_plan)) == 0
        assert len(check_h9(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h10(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h11(baseline_plan, fl, rules, ctx)) == 0
        assert len(check_h12(baseline_plan, fl, rules, ctx)) == 0
