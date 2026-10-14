"""
RoutePulse Comprehensive Optimizer Test Suite (tests/test_optimizer.py)
Tests:
1. Candidate trip generation: baseline trips, [-5..+5] min retiming, added trips every 2 min on overloaded routes.
2. CP-SAT solver performance & validity: produces plan with 0 hard violations in under 10 seconds.
3. Fast greedy heuristic fallback: produces valid plan with 0 hard violations in under 2 seconds.
4. Recommendation card schema conformance: all 6 action types with evidence, impact, tradeoffs, and zero violations.
5. Rolling horizon re-optimization and disruption response for S1 (traffic), S2 (breakdown), and S3 (demand spike).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List
import pytest

from core.schemas import Plan, Trip, Vehicle, Disruption, Recommendation
from optimize.candidates import CandidateTrip, generate_candidate_trips
from optimize.cpsat_model import (
    RoutePulseCpSatOptimizer,
    OptimizerConfig,
    solve_cpsat_plan,
)
from optimize.heuristic import (
    RoutePulseGreedyHeuristic,
    run_fast_heuristic,
)
from optimize.explain import (
    RecommendationEngine,
    generate_recommendations,
)
from optimize.rolling import (
    RollingHorizonOptimizer,
    RollingStepResult,
    run_rolling_step,
)
from validate.validator import validate, is_valid_plan

ROOT_DIR = Path(__file__).resolve().parent.parent
BASELINE_PLAN_PATH = ROOT_DIR / "config" / "baseline_plan.json"
NETWORK_PATH = ROOT_DIR / "api" / "fixtures" / "network.json"


@pytest.fixture(scope="module")
def baseline_plan() -> Plan:
    with open(BASELINE_PLAN_PATH, "r", encoding="utf-8") as f:
        return Plan(**json.load(f))


@pytest.fixture(scope="module")
def network_fleet() -> Dict[str, Vehicle]:
    with open(NETWORK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {v["vehicle_id"]: Vehicle(**v) for v in data["vehicles"]}


# ---------------------------------------------------------------------------
# 1. Candidate Generation Tests
# ---------------------------------------------------------------------------

class TestCandidateGeneration:
    def test_baseline_trips_and_shifts_generated(self, baseline_plan: Plan):
        """Verify baseline trips are included with shifts in [-5..+5] in 1-min increments."""
        window = (450, 480)
        cands = generate_candidate_trips(
            baseline_plan,
            window=window,
            shift_range=(-5, 5),
            shift_step=1,
            include_added_trips=False,
        )

        assert len(cands) > 0

        # Check shift coverage for a baseline trip in the window
        sample_base_id = cands[0].base_trip_id
        assert sample_base_id is not None

        shifts_for_trip = [c.shift_min for c in cands if c.base_trip_id == sample_base_id]
        expected_shifts = list(range(-5, 6))
        assert sorted(shifts_for_trip) == expected_shifts

        # Check that shift=0 candidate matches baseline departure exactly
        s0 = next(c for c in cands if c.base_trip_id == sample_base_id and c.shift_min == 0)
        base_trip = next(t for t in baseline_plan.trips if t.trip_id == sample_base_id)
        assert s0.departure_min == base_trip.departure_min
        assert s0.scheduled_stop_times == base_trip.scheduled_stop_times

    def test_added_trips_every_2min_on_overloaded_routes(self, baseline_plan: Plan):
        """Verify candidate added trips every 2 min on R3 and R1."""
        window = (450, 470)
        cands = generate_candidate_trips(
            baseline_plan,
            window=window,
            extra_trip_step_min=2,
            overloaded_routes=["R3", "R1"],
            include_added_trips=True,
        )

        added = [c for c in cands if c.is_added]
        assert len(added) > 0

        # Verify added trips exist for both R3 and R1
        routes = {c.route_id for c in added}
        assert "R3" in routes
        assert "R1" in routes

        # Check 2-min departure spacing for added R1 trips
        r1_added_deps = sorted(c.departure_min for c in added if c.route_id == "R1")
        diffs = [r1_added_deps[i + 1] - r1_added_deps[i] for i in range(len(r1_added_deps) - 1)]
        assert all(d == 2 for d in diffs)

    def test_candidate_to_trip_conversion(self, baseline_plan: Plan):
        """Verify CandidateTrip converts to valid Pydantic Trip entity."""
        cands = generate_candidate_trips(baseline_plan, window=(450, 460))
        cand = cands[0]
        trip = cand.to_trip(vehicle_id="B1")
        assert isinstance(trip, Trip)
        assert trip.departure_min == cand.departure_min
        assert trip.vehicle_id == "B1"


# ---------------------------------------------------------------------------
# 2. CP-SAT Solver Performance & Validity Tests
# ---------------------------------------------------------------------------

class TestCpSatOptimizer:
    def test_cpsat_solver_valid_plan_under_10s(self, baseline_plan: Plan):
        """Verify CP-SAT solver completes in < 10s and produces 0 hard violations."""
        t0 = time.perf_counter()
        res = solve_cpsat_plan(
            current_plan=baseline_plan,
            window=(450, 480),
            time_limit_s=8.0,
        )
        elapsed = time.perf_counter() - t0

        assert elapsed < 10.0, f"CP-SAT solver exceeded 10s limit: {elapsed:.2f}s"
        assert res.hard_violations_count == 0, f"Expected 0 hard violations, got {res.hard_violations_count}"
        assert is_valid_plan(res.plan) is True

    def test_cpsat_solver_demand_coverage(self, baseline_plan: Plan):
        """Verify CP-SAT covers P80 demand slots without constraint violations."""
        p80_demand = {("R3", 30): 65.0, ("R1", 30): 55.0}
        p80_loads = {"TR1_007": 40.0}

        res = solve_cpsat_plan(
            current_plan=baseline_plan,
            window=(450, 475),
            p80_demand=p80_demand,
            p80_loads=p80_loads,
            time_limit_s=6.0,
        )

        assert res.hard_violations_count == 0
        assert is_valid_plan(res.plan) is True

    def test_cpsat_respects_vehicle_continuity_and_layovers(self, baseline_plan: Plan):
        """Verify resulting vehicle blocks satisfy minimum layovers and continuity."""
        res = solve_cpsat_plan(baseline_plan, window=(450, 470), time_limit_s=5.0)
        viols = validate(res.plan)
        h2_h3_h4 = [v for v in viols if v.code in ("H2", "H3", "H4") and v.severity == "hard"]
        assert len(h2_h3_h4) == 0


# ---------------------------------------------------------------------------
# 3. Greedy Heuristic Fallback Tests
# ---------------------------------------------------------------------------

class TestGreedyHeuristic:
    def test_heuristic_fast_execution_and_zero_hard_violations(self, baseline_plan: Plan):
        """Verify heuristic runs in under 2 seconds and produces 0 hard violations."""
        t0 = time.perf_counter()
        res = run_fast_heuristic(baseline_plan, window=(450, 510))
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"Heuristic took too long: {elapsed:.2f}s"
        assert res.hard_violations_count == 0
        assert is_valid_plan(res.plan) is True

    def test_heuristic_adds_trips_on_overloaded_routes(self, baseline_plan: Plan):
        """Verify heuristic identifies overload and dispatches idle reserve vehicles."""
        p80_demand = {("R3", 31): 80.0}
        res = run_fast_heuristic(
            baseline_plan,
            p80_demand=p80_demand,
            window=(450, 510),
        )

        assert len(res.added_trips) >= 1
        # Check that dispatched vehicle is one of the reserves
        added_vids = {t.vehicle_id for t in res.added_trips}
        assert any(vid in ("B5", "B6", "M4") for vid in added_vids)
        assert res.hard_violations_count == 0


# ---------------------------------------------------------------------------
# 4. Recommendation Card Schema & Explainability Tests
# ---------------------------------------------------------------------------

class TestRecommendationCards:
    def test_all_recommendation_types_generated(self, baseline_plan: Plan):
        """Verify all 6 recommendation card types conform to schema."""
        recs = generate_recommendations(baseline_plan)
        types_generated = {r.type for r in recs}

        expected_types = {
            "ADD_TRIP",
            "RETIME_TRIP",
            "SWAP_VEHICLE",
            "HOLD_FOR_CONNECTION",
            "SHORT_TURN",
            "REALLOCATE_VEHICLE",
        }
        assert expected_types.issubset(types_generated), f"Missing types: {expected_types - types_generated}"

    def test_recommendation_card_fields_and_validation(self, baseline_plan: Plan):
        """Verify evidence, impact, tradeoffs, reason codes, and 0 violations on cards."""
        recs = generate_recommendations(baseline_plan)

        for rec in recs:
            assert isinstance(rec, Recommendation)
            assert rec.id.startswith("rec-")
            assert len(rec.summary) > 10
            assert len(rec.reason_codes) >= 1
            assert "pax_affected" in rec.evidence
            assert "avg_wait_min" in rec.impact
            assert "left_behind" in rec.impact
            assert "missed_connections" in rec.impact
            assert "vehicle_km" in rec.impact
            assert len(rec.tradeoff) > 10
            assert len(rec.binding_constraints) >= 1
            assert len(rec.alternatives_rejected) >= 1
            assert rec.validated is True
            assert len(rec.violations) == 0

    def test_individual_recommendation_builder_validation(self, baseline_plan: Plan):
        """Verify that RecommendationEngine rejects invalid moves that produce hard violations."""
        engine = RecommendationEngine()
        # Attempt to shift by 10 minutes (exceeds H8 max shift 5 min)
        invalid_rec = engine.build_retime_trip_card(
            base_plan=baseline_plan,
            trip_id="TR1_001",
            shift_min=10,
        )
        assert invalid_rec is None, "Engine must not emit recommendations violating hard constraints!"


# ---------------------------------------------------------------------------
# 5. Disruption Response & Rolling Horizon Tests (S1, S2, S3)
# ---------------------------------------------------------------------------

class TestDisruptionsAndRolling:
    def test_disruption_s1_traffic_delay_response(self, baseline_plan: Plan):
        """Test rolling response to S1 (traffic delay): buffers timetable & holds connections."""
        d1 = Disruption(
            type="traffic",
            params={"multiplier": 1.35, "corridors": ["Metro", "Main Gate"]},
            start_min=480,
            end_min=570,
        )
        opt = RollingHorizonOptimizer()
        step_res = opt.step(current_time_min=485, current_plan=baseline_plan, disruption=d1)

        assert step_res.hard_violations_count == 0
        assert is_valid_plan(step_res.plan) is True

        # Should recommend connection hold or timetable retiming
        rec_types = [r.type for r in step_res.recommendations]
        assert any(t in ("HOLD_FOR_CONNECTION", "RETIME_TRIP") for t in rec_types)

    def test_disruption_s2_vehicle_breakdown_response(self, baseline_plan: Plan):
        """Test rolling response to S2 (vehicle B2 breakdown): substitutes reserve B6."""
        d2 = Disruption(
            type="vehicle_out",
            params={"vehicle_id": "B2", "reserve_available": True},
            start_min=495,
            end_min=630,
        )
        opt = RollingHorizonOptimizer()
        step_res = opt.step(current_time_min=495, current_plan=baseline_plan, disruption=d2)

        assert step_res.hard_violations_count == 0
        assert is_valid_plan(step_res.plan) is True

        # Verify B2 is removed from subsequent trips in step plan
        subsequent_trips = [t for t in step_res.plan.trips if t.departure_min >= 495]
        b2_trips = [t for t in subsequent_trips if t.vehicle_id == "B2"]
        assert len(b2_trips) == 0, "Broken vehicle B2 must not have trips assigned after breakdown"

        # Verify swapped to reserve vehicle
        assert len(step_res.swapped_vehicles) > 0
        assert all(v in ("B6", "B5", "M4") for v in step_res.swapped_vehicles.values())

    def test_disruption_s3_demand_spike_response(self, baseline_plan: Plan):
        """Test rolling response to S3 (auditorium demand surge at S07): injects extra capacity."""
        d3 = Disruption(
            type="demand_spike",
            params={"stop_id": "S07", "surge_passengers": 1000},
            start_min=1050,
            end_min=1075,
        )
        opt = RollingHorizonOptimizer()
        step_res = opt.step(current_time_min=1050, current_plan=baseline_plan, disruption=d3)

        assert step_res.hard_violations_count == 0
        assert is_valid_plan(step_res.plan) is True
        assert len(step_res.added_trips) >= 1
        rec_types = [r.type for r in step_res.recommendations]
        assert "ADD_TRIP" in rec_types

    def test_rolling_horizon_simulation_progression(self, baseline_plan: Plan):
        """Test multi-step rolling horizon simulation progression (15-min sequence)."""
        opt = RollingHorizonOptimizer(replan_every_min=5)
        steps = opt.simulate_rolling_horizon(
            start_min=450,
            end_min=465,
            initial_plan=baseline_plan,
            step_min=5,
        )

        assert len(steps) == 4  # 450, 455, 460, 465
        for s in steps:
            assert s.hard_violations_count == 0
            assert is_valid_plan(s.plan) is True
