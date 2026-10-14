"""
Test Suite for RoutePulse Hard-Constraint Validator
Tests all 12 hard constraints (H1..H12), soft checks (A1, A4, A6),
baseline plan compliance, boundary conditions, and property-based tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from hypothesis import given, strategies as st, settings

from core.schemas import Plan, Trip, Vehicle, ServiceRules, Violation, PlanValidationResponse
from validate.validator import (
    validate,
    validate_plan_response,
    is_valid_plan,
    get_hard_violations,
    get_soft_violations,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
BASELINE_PLAN_PATH = ROOT_DIR / "config" / "baseline_plan.json"
NETWORK_PATH = ROOT_DIR / "api" / "fixtures" / "network.json"


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

def load_standard_fleet() -> Dict[str, Vehicle]:
    """Load default 10-vehicle fleet from fixtures."""
    with open(NETWORK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {v["vehicle_id"]: Vehicle(**v) for v in data["vehicles"]}


@pytest.fixture
def fleet() -> Dict[str, Vehicle]:
    return load_standard_fleet()


@pytest.fixture
def rules() -> ServiceRules:
    return ServiceRules()


def make_clean_trip(
    trip_id: str = "T1",
    route_id: str = "R1",
    direction: int = 0,
    vehicle_id: str = "B1",
    departure_min: int = 450,
    duration_min: int = 20,
    start_stop: str = "S01",
    end_stop: str = "S01",
) -> Trip:
    """Helper to construct a valid trip with realistic stop times."""
    arr_time = departure_min + duration_min
    if start_stop == end_stop:
        sched = {start_stop: arr_time, "S02": departure_min + 3, "S03": departure_min + 6}
    else:
        sched = {start_stop: departure_min, end_stop: arr_time}
    return Trip(
        trip_id=trip_id,
        route_id=route_id,
        direction=direction,
        vehicle_id=vehicle_id,
        departure_min=departure_min,
        scheduled_stop_times=sched,
    )


# ---------------------------------------------------------------------------
# 1. Baseline Plan Verification (Mandatory)
# ---------------------------------------------------------------------------

def test_baseline_plan_has_zero_hard_violations():
    """Verify that config/baseline_plan.json passes with 0 hard violations."""
    assert BASELINE_PLAN_PATH.exists(), "config/baseline_plan.json must exist"
    with open(BASELINE_PLAN_PATH, "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    plan = Plan(**plan_data)
    violations = validate(plan)
    hard_violations = [v for v in violations if v.severity == "hard"]
    assert len(hard_violations) == 0, f"Expected 0 hard violations, got {hard_violations}"


def test_baseline_plan_validation_response():
    """Verify PlanValidationResponse helper on baseline plan."""
    with open(BASELINE_PLAN_PATH, "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    plan = Plan(**plan_data)
    res = validate_plan_response(plan)
    assert res.is_valid is True
    assert res.hard_violations_count == 0


def test_is_valid_plan_on_baseline():
    """Verify is_valid_plan predicate returns True for baseline."""
    with open(BASELINE_PLAN_PATH, "r", encoding="utf-8") as f:
        plan = Plan(**json.load(f))
    assert is_valid_plan(plan) is True


# ---------------------------------------------------------------------------
# 2. H1: Vehicle Assignment & Availability
# ---------------------------------------------------------------------------

def test_h1_unassigned_vehicle(fleet, rules):
    """H1: Trip assigned to a vehicle not in the fleet."""
    t = make_clean_trip(trip_id="T_H1_1", vehicle_id="GHOST_BUS")
    plan = Plan(plan_id="p_h1_1", name="H1 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H1" and "GHOST_BUS" in v.detail for v in viols)


def test_h1_empty_vehicle_id(fleet, rules):
    """H1: Trip assigned to an empty string vehicle ID."""
    t = make_clean_trip(trip_id="T_H1_2", vehicle_id="")
    plan = Plan(plan_id="p_h1_2", name="H1 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H1" for v in viols)


def test_h1_departure_before_vehicle_available(fleet, rules):
    """H1: Trip departs before vehicle available_from (390)."""
    # Create vehicle available from 500
    custom_fleet = dict(fleet)
    custom_fleet["B1"] = Vehicle(
        vehicle_id="B1", type="bus", capacity=45, seated=30, accessible=True,
        available_from=500, available_to=1320
    )
    t = make_clean_trip(trip_id="T_H1_3", vehicle_id="B1", departure_min=450)
    plan = Plan(plan_id="p_h1_3", name="H1 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=custom_fleet, rules=rules)
    assert any(v.code == "H1" and "available_from" in v.detail for v in viols)


def test_h1_trip_ends_after_vehicle_available_to(fleet, rules):
    """H1: Trip ends after vehicle available_to."""
    custom_fleet = dict(fleet)
    custom_fleet["B1"] = Vehicle(
        vehicle_id="B1", type="bus", capacity=45, seated=30, accessible=True,
        available_from=390, available_to=500
    )
    # Trip ends at 510
    t = make_clean_trip(trip_id="T_H1_4", vehicle_id="B1", departure_min=490, duration_min=20)
    plan = Plan(plan_id="p_h1_4", name="H1 Test", window=["07:30", "09:00"], trips=[t])
    viols = validate(plan, fleet=custom_fleet, rules=rules)
    assert any(v.code == "H1" and "available_to" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 3. H2: Vehicle Overlapping Trips
# ---------------------------------------------------------------------------

def test_h2_exact_same_departure(fleet, rules):
    """H2: Same vehicle assigned to two trips departing at the same minute."""
    t1 = make_clean_trip(trip_id="T_H2_1a", vehicle_id="B1", departure_min=450, duration_min=15)
    t2 = make_clean_trip(trip_id="T_H2_1b", vehicle_id="B1", departure_min=450, duration_min=15)
    plan = Plan(plan_id="p_h2_1", name="H2 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H2" for v in viols)


def test_h2_partial_trip_overlap(fleet, rules):
    """H2: Trip B departs while Trip A is still in transit."""
    t1 = make_clean_trip(trip_id="T_H2_2a", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_H2_2b", vehicle_id="B1", departure_min=465, duration_min=20) # starts 465 < 470
    plan = Plan(plan_id="p_h2_2", name="H2 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H2" for v in viols)


def test_h2_enveloped_trip_overlap(fleet, rules):
    """H2: Trip B is entirely contained within Trip A time window."""
    t1 = make_clean_trip(trip_id="T_H2_3a", vehicle_id="B1", departure_min=450, duration_min=30) # ends 480
    t2 = make_clean_trip(trip_id="T_H2_3b", vehicle_id="B1", departure_min=460, duration_min=10) # ends 470 < 480
    plan = Plan(plan_id="p_h2_3", name="H2 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H2" for v in viols)


def test_h2_multiple_consecutive_overlaps(fleet, rules):
    """H2: Chain of three overlapping trips on the same vehicle."""
    t1 = make_clean_trip(trip_id="T_H2_4a", vehicle_id="B1", departure_min=450, duration_min=20)
    t2 = make_clean_trip(trip_id="T_H2_4b", vehicle_id="B1", departure_min=460, duration_min=20)
    t3 = make_clean_trip(trip_id="T_H2_4c", vehicle_id="B1", departure_min=470, duration_min=20)
    plan = Plan(plan_id="p_h2_4", name="H2 Test", window=["07:30", "08:30"], trips=[t1, t2, t3])
    viols = validate(plan, fleet=fleet, rules=rules)
    h2_viols = [v for v in viols if v.code == "H2"]
    assert len(h2_viols) >= 2


# ---------------------------------------------------------------------------
# 4. H3: Minimum Layover (>= 4 min)
# ---------------------------------------------------------------------------

def test_h3_zero_minute_layover(fleet, rules):
    """H3: Next trip starts immediately when previous ends (layover 0 min)."""
    t1 = make_clean_trip(trip_id="T_H3_1a", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_H3_1b", vehicle_id="B1", departure_min=470, duration_min=20) # starts 470, layover=0
    plan = Plan(plan_id="p_h3_1", name="H3 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H3" and "0 min" in v.detail for v in viols)


def test_h3_one_minute_layover(fleet, rules):
    """H3: Layover is 1 min (< 4 min)."""
    t1 = make_clean_trip(trip_id="T_H3_2a", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_H3_2b", vehicle_id="B1", departure_min=471, duration_min=20) # layover=1
    plan = Plan(plan_id="p_h3_2", name="H3 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H3" and "1 min" in v.detail for v in viols)


def test_h3_two_minute_layover(fleet, rules):
    """H3: Layover is 2 min (< 4 min)."""
    t1 = make_clean_trip(trip_id="T_H3_3a", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_H3_3b", vehicle_id="B1", departure_min=472, duration_min=20) # layover=2
    plan = Plan(plan_id="p_h3_3", name="H3 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H3" and "2 min" in v.detail for v in viols)


def test_h3_three_minute_layover(fleet, rules):
    """H3: Layover is 3 min (< 4 min)."""
    t1 = make_clean_trip(trip_id="T_H3_4a", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_H3_4b", vehicle_id="B1", departure_min=473, duration_min=20) # layover=3
    plan = Plan(plan_id="p_h3_4", name="H3 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H3" and "3 min" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 5. H4: Vehicle Continuity & Deadhead Feasibility
# ---------------------------------------------------------------------------

def test_h4_different_stop_zero_deadhead_time(fleet, rules):
    """H4: Vehicle ends at S03, next trip starts at distant S13 with 1 min available."""
    # S03 is (600, 400), S13 is (-1500, -600); distance ~2300m, free-flow deadhead ~4.8 min
    t1 = Trip(
        trip_id="T_H4_1a", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 450, "S03": 470}
    )
    t2 = Trip(
        trip_id="T_H4_1b", route_id="R3", direction=0, vehicle_id="B1",
        departure_min=471, scheduled_stop_times={"S13": 471, "S03": 485}
    )
    plan = Plan(plan_id="p_h4_1", name="H4 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H4" for v in viols)


def test_h4_infeasible_deadhead_s01_to_s11(fleet, rules):
    """H4: S01 to S11 (Sports Complex) requires > 2.5 min; only 1 min given."""
    t1 = Trip(
        trip_id="T_H4_2a", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 465}
    )
    t2 = Trip(
        trip_id="T_H4_2b", route_id="R4", direction=0, vehicle_id="B1",
        departure_min=466, scheduled_stop_times={"S11": 466, "S03": 480}
    )
    plan = Plan(plan_id="p_h4_2", name="H4 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H4" for v in viols)


def test_h4_custom_travel_time_model_deadhead(fleet, rules):
    """H4: Custom travel time model requires 15 min deadhead; only 5 min given."""
    class StrictTravelTimeModel:
        def get_deadhead_time(self, s1: str, s2: str) -> float:
            return 15.0

    t1 = Trip(
        trip_id="T_H4_3a", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 460}
    )
    t2 = Trip(
        trip_id="T_H4_3b", route_id="R2", direction=0, vehicle_id="B1",
        departure_min=465, scheduled_stop_times={"S03": 465, "S10": 480}
    )
    plan = Plan(plan_id="p_h4_3", name="H4 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules, travel_time_model=StrictTravelTimeModel())
    assert any(v.code == "H4" for v in viols)


def test_h4_callable_travel_time_model(fleet, rules):
    """H4: Callable travel time model reporting infeasible deadhead."""
    def model(from_s: str, to_s: str) -> float:
        return 20.0

    t1 = Trip(
        trip_id="T_H4_4a", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 460}
    )
    t2 = Trip(
        trip_id="T_H4_4b", route_id="R2", direction=0, vehicle_id="B1",
        departure_min=466, scheduled_stop_times={"S03": 466, "S10": 480}
    )
    plan = Plan(plan_id="p_h4_4", name="H4 Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules, travel_time_model=model)
    assert any(v.code == "H4" for v in viols)


# ---------------------------------------------------------------------------
# 6. H5: Operating Hours (390..1320 / 06:30..22:00)
# ---------------------------------------------------------------------------

def test_h5_departure_at_06_29(fleet, rules):
    """H5: Trip departs at 389 (06:29, 1 min before start)."""
    t = make_clean_trip(trip_id="T_H5_1", departure_min=389)
    plan = Plan(plan_id="p_h5_1", name="H5 Test", window=["06:00", "08:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H5" and "389" in v.detail for v in viols)


def test_h5_departure_at_midnight(fleet, rules):
    """H5: Trip departs at 0 (00:00)."""
    t = make_clean_trip(trip_id="T_H5_2", departure_min=0)
    plan = Plan(plan_id="p_h5_2", name="H5 Test", window=["00:00", "02:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H5" for v in viols)


def test_h5_departure_at_22_01(fleet, rules):
    """H5: Trip departs at 1321 (22:01, 1 min after end)."""
    t = make_clean_trip(trip_id="T_H5_3", departure_min=1321)
    plan = Plan(plan_id="p_h5_3", name="H5 Test", window=["21:00", "23:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H5" and "1321" in v.detail for v in viols)


def test_h5_departure_late_night_1400(fleet, rules):
    """H5: Trip departs at 1400 (23:20)."""
    t = make_clean_trip(trip_id="T_H5_4", departure_min=1400)
    plan = Plan(plan_id="p_h5_4", name="H5 Test", window=["22:00", "24:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H5" for v in viols)


# ---------------------------------------------------------------------------
# 7. H6: Fleet Size (Concurrent Vehicles in Use)
# ---------------------------------------------------------------------------

def test_h6_eleven_concurrent_buses(fleet, rules):
    """H6: 11 vehicles active concurrently when fleet only has 10."""
    trips = []
    # Create 11 vehicles in custom fleet or use 11 trips with fake vehicle IDs
    custom_fleet = {f"V{i}": Vehicle(vehicle_id=f"V{i}", type="bus", capacity=45, seated=30) for i in range(1, 11)}
    for i in range(1, 12):
        vid = f"V{i}"
        trips.append(make_clean_trip(trip_id=f"T_H6_{i}", vehicle_id=vid, departure_min=450, duration_min=20))
    # Add V11 to custom fleet so H1 doesn't fire, but fleet has 10 vehicles originally
    # Concurrency check evaluates len(active_vehicles) > len(fleet)
    plan = Plan(plan_id="p_h6_1", name="H6 Test", window=["07:30", "08:30"], trips=trips)
    # Pass fleet of size 10
    viols = validate(plan, fleet=custom_fleet, rules=rules)
    assert any(v.code == "H6" for v in viols)


def test_h6_small_fleet_limit_exceeded(fleet, rules):
    """H6: Custom fleet of 2 vehicles, 3 active at same time."""
    two_fleet = {
        "B1": fleet["B1"],
        "B2": fleet["B2"],
        "B3": fleet["B3"],
    }
    # Pass 2-vehicle fleet dict to validator
    limit_fleet = {"B1": fleet["B1"], "B2": fleet["B2"]}
    trips = [
        make_clean_trip(trip_id="T_H6_2a", vehicle_id="B1", departure_min=450, duration_min=30),
        make_clean_trip(trip_id="T_H6_2b", vehicle_id="B2", departure_min=455, duration_min=30),
        make_clean_trip(trip_id="T_H6_2c", vehicle_id="B3", departure_min=460, duration_min=30),
    ]
    plan = Plan(plan_id="p_h6_2", name="H6 Test", window=["07:30", "08:30"], trips=trips)
    viols = validate(plan, fleet=limit_fleet, rules=rules)
    assert any(v.code == "H6" for v in viols)


def test_h6_single_vehicle_fleet_with_concurrency(fleet, rules):
    """H6: 1 vehicle fleet with 2 simultaneous trips."""
    one_fleet = {"B1": fleet["B1"]}
    trips = [
        make_clean_trip(trip_id="T_H6_3a", vehicle_id="B1", departure_min=450, duration_min=20),
        make_clean_trip(trip_id="T_H6_3b", vehicle_id="B2", departure_min=450, duration_min=20),
    ]
    plan = Plan(plan_id="p_h6_3", name="H6 Test", window=["07:30", "08:30"], trips=trips)
    viols = validate(plan, fleet=one_fleet, rules=rules)
    assert any(v.code == "H6" for v in viols)


def test_h6_massive_concurrency_surge(fleet, rules):
    """H6: 20 simultaneous departures."""
    surplus_fleet = {f"B{i}": Vehicle(vehicle_id=f"B{i}", type="bus", capacity=45, seated=30) for i in range(1, 21)}
    trips = [make_clean_trip(trip_id=f"T_H6_4_{i}", vehicle_id=f"B{i}", departure_min=500, duration_min=20) for i in range(1, 21)]
    plan = Plan(plan_id="p_h6_4", name="H6 Test", window=["07:30", "09:00"], trips=trips)
    # Standard fleet has 10 vehicles
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H6" for v in viols)


# ---------------------------------------------------------------------------
# 8. H7: Headway (Min >= 3 min, Max <= 12 peak / 20 off-peak)
# ---------------------------------------------------------------------------

def test_h7_headway_too_short_1min(fleet, rules):
    """H7: Headway of 1 min on route R1 dir 0 (min is 3 min)."""
    t1 = make_clean_trip(trip_id="T_H7_1a", route_id="R1", direction=0, vehicle_id="B1", departure_min=450)
    t2 = make_clean_trip(trip_id="T_H7_1b", route_id="R1", direction=0, vehicle_id="B2", departure_min=451)
    plan = Plan(plan_id="p_h7_1", name="H7 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H7" and "below min headway" in v.detail for v in viols)


def test_h7_headway_too_short_2min(fleet, rules):
    """H7: Headway of 2 min on route R1 dir 0 (min is 3 min)."""
    t1 = make_clean_trip(trip_id="T_H7_2a", route_id="R1", direction=0, vehicle_id="B1", departure_min=450)
    t2 = make_clean_trip(trip_id="T_H7_2b", route_id="R1", direction=0, vehicle_id="B2", departure_min=452)
    plan = Plan(plan_id="p_h7_2", name="H7 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H7" and "below min headway" in v.detail for v in viols)


def test_h7_peak_headway_exceeds_12min(fleet, rules):
    """H7: Headway of 15 min during morning peak (07:30, 450 min) on R1 (max is 12)."""
    t1 = make_clean_trip(trip_id="T_H7_3a", route_id="R1", direction=0, vehicle_id="B1", departure_min=450)
    t2 = make_clean_trip(trip_id="T_H7_3b", route_id="R1", direction=0, vehicle_id="B2", departure_min=465)
    plan = Plan(plan_id="p_h7_3", name="H7 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H7" and "exceeds max headway" in v.detail for v in viols)


def test_h7_offpeak_headway_exceeds_20min(fleet, rules):
    """H7: Headway of 25 min during off-peak (13:00, 780 min) on R1 (max is 20)."""
    t1 = make_clean_trip(trip_id="T_H7_4a", route_id="R1", direction=0, vehicle_id="B1", departure_min=780)
    t2 = make_clean_trip(trip_id="T_H7_4b", route_id="R1", direction=0, vehicle_id="B2", departure_min=805)
    plan = Plan(plan_id="p_h7_4", name="H7 Test", window=["13:00", "14:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H7" and "exceeds max headway" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 9. H8: Departure Shift from Baseline (<= 5 min)
# ---------------------------------------------------------------------------

def test_h8_retimed_trip_shifted_forward_6min(fleet, rules):
    """H8: Retimed trip shifted by +6 min (from 450 to 456)."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="opt_1", name="Opt", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=456)]
    )
    viols = validate(cand_plan, fleet=fleet, rules=rules, baseline_plan=base_plan)
    assert any(v.code == "H8" and "shifted by 6 min" in v.detail for v in viols)


def test_h8_retimed_trip_shifted_backward_6min(fleet, rules):
    """H8: Retimed trip shifted by -6 min (from 450 to 444)."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="opt_2", name="Opt", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=444)]
    )
    viols = validate(cand_plan, fleet=fleet, rules=rules, baseline_plan=base_plan)
    assert any(v.code == "H8" and "shifted by 6 min" in v.detail for v in viols)


def test_h8_retimed_trip_shifted_15min(fleet, rules):
    """H8: Retimed trip shifted by +15 min."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="opt_3", name="Opt", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=465)]
    )
    viols = validate(cand_plan, fleet=fleet, rules=rules, baseline_plan=base_plan)
    assert any(v.code == "H8" and "shifted by 15 min" in v.detail for v in viols)


def test_h8_retimed_trip_shifted_backward_10min(fleet, rules):
    """H8: Retimed trip shifted by -10 min."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="opt_4", name="Opt", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=440)]
    )
    viols = validate(cand_plan, fleet=fleet, rules=rules, baseline_plan=base_plan)
    assert any(v.code == "H8" and "shifted by 10 min" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 10. H9: Driver Rules (<= 210 min Continuous Driving, then >= 20 min Break)
# ---------------------------------------------------------------------------

def test_h9_continuous_driving_215min(fleet, rules):
    """H9: 10 consecutive trips with 4 min layovers totaling 215 min continuous driving."""
    trips = []
    t_start = 450
    # 10 trips of 18 min + 4 min layover = 22 min cycle. 10 * 22 - 4 = 216 min
    for i in range(1, 11):
        trips.append(make_clean_trip(trip_id=f"T_H9_1_{i}", vehicle_id="B1", departure_min=t_start, duration_min=18))
        t_start += 22
    plan = Plan(plan_id="p_h9_1", name="H9 Test", window=["07:30", "12:00"], trips=trips)
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H9" and "Continuous driving reached" in v.detail for v in viols)


def test_h9_continuous_driving_with_10min_breaks_only(fleet, rules):
    """H9: Driver takes 10 min breaks (< 20 min required break), driving 240 min."""
    trips = []
    t_start = 450
    # 8 trips of 20 min + 10 min gap = 30 min cycle. 8 * 30 - 10 = 230 min
    for i in range(1, 9):
        trips.append(make_clean_trip(trip_id=f"T_H9_2_{i}", vehicle_id="B1", departure_min=t_start, duration_min=20))
        t_start += 30
    plan = Plan(plan_id="p_h9_2", name="H9 Test", window=["07:30", "12:00"], trips=trips)
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H9" for v in viols)


def test_h9_single_marathon_trip_220min(fleet, rules):
    """H9: A single trip scheduled for 220 min (> 210 min)."""
    t = make_clean_trip(trip_id="T_H9_3", vehicle_id="B1", departure_min=450, duration_min=220)
    plan = Plan(plan_id="p_h9_3", name="H9 Test", window=["07:30", "12:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H9" for v in viols)


def test_h9_massive_chain_without_break(fleet, rules):
    """H9: 12 consecutive trips totaling 250 min without qualifying break."""
    trips = []
    t_start = 450
    for i in range(1, 13):
        trips.append(make_clean_trip(trip_id=f"T_H9_4_{i}", vehicle_id="B1", departure_min=t_start, duration_min=17))
        t_start += 21
    plan = Plan(plan_id="p_h9_4", name="H9 Test", window=["07:30", "12:00"], trips=trips)
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H9" for v in viols)


# ---------------------------------------------------------------------------
# 11. H10: Accessible Vehicle on Each Route at Least Once per Hour
# ---------------------------------------------------------------------------

def test_h10_route_r1_missing_accessible_vehicle(fleet, rules):
    """H10: Route R1 has 2 departures in hour 7 (450, 462) using non-accessible B3."""
    t1 = make_clean_trip(trip_id="T_H10_1a", route_id="R1", vehicle_id="B3", departure_min=450) # B3 not accessible
    t2 = make_clean_trip(trip_id="T_H10_1b", route_id="R1", vehicle_id="B3", departure_min=462)
    plan = Plan(plan_id="p_h10_1", name="H10 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H10" and "Route R1" in v.detail for v in viols)


def test_h10_route_r2_missing_accessible_vehicle(fleet, rules):
    """H10: Route R2 has 2 departures in hour 8 using non-accessible M2."""
    t1 = make_clean_trip(trip_id="T_H10_2a", route_id="R2", vehicle_id="M2", departure_min=480) # M2 not accessible
    t2 = make_clean_trip(trip_id="T_H10_2b", route_id="R2", vehicle_id="M2", departure_min=495)
    plan = Plan(plan_id="p_h10_2", name="H10 Test", window=["08:00", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H10" and "Route R2" in v.detail for v in viols)


def test_h10_route_r3_missing_accessible_vehicle(fleet, rules):
    """H10: Route R3 has 2 departures in hour 9 using non-accessible B4."""
    t1 = make_clean_trip(trip_id="T_H10_3a", route_id="R3", vehicle_id="B4", departure_min=540) # B4 not accessible
    t2 = make_clean_trip(trip_id="T_H10_3b", route_id="R3", vehicle_id="B4", departure_min=552)
    plan = Plan(plan_id="p_h10_3", name="H10 Test", window=["09:00", "10:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H10" and "Route R3" in v.detail for v in viols)


def test_h10_route_r4_missing_accessible_vehicle(fleet, rules):
    """H10: Route R4 has 2 departures in hour 10 using non-accessible M3."""
    t1 = make_clean_trip(trip_id="T_H10_4a", route_id="R4", vehicle_id="M3", departure_min=600) # M3 not accessible
    t2 = make_clean_trip(trip_id="T_H10_4b", route_id="R4", vehicle_id="M3", departure_min=630)
    plan = Plan(plan_id="p_h10_4", name="H10 Test", window=["10:00", "11:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H10" and "Route R4" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 12. H11: Trip Duration Feasible (>= Free-Flow Travel Time)
# ---------------------------------------------------------------------------

def test_h11_trip_duration_faster_than_free_flow(fleet, rules):
    """H11: R1 scheduled for 2 min duration (free-flow requires ~6.4 min)."""
    t = Trip(
        trip_id="T_H11_1", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 452}
    )
    plan = Plan(plan_id="p_h11_1", name="H11 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H11" and "less than free-flow" in v.detail for v in viols)


def test_h11_zero_minute_duration(fleet, rules):
    """H11: Scheduled duration is 0 min (instantaneous travel)."""
    t = Trip(
        trip_id="T_H11_2", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S01": 450}
    )
    plan = Plan(plan_id="p_h11_2", name="H11 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H11" for v in viols)


def test_h11_stop_scheduled_before_departure(fleet, rules):
    """H11: Stop scheduled at 448 when departure is 450 (time travel)."""
    t = Trip(
        trip_id="T_H11_3", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S02": 448, "S01": 470}
    )
    plan = Plan(plan_id="p_h11_3", name="H11 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H11" and "before departure" in v.detail for v in viols)


def test_h11_empty_scheduled_stop_times(fleet, rules):
    """H11: Scheduled stop times dictionary is completely empty."""
    t = Trip(
        trip_id="T_H11_4", route_id="R1", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={}
    )
    plan = Plan(plan_id="p_h11_4", name="H11 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H11" and "no scheduled stop times" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 13. H12: Forecast P80 Load <= Rated Vehicle Capacity & Route Compatibility
# ---------------------------------------------------------------------------

def test_h12_p80_load_exceeds_bus_capacity(fleet, rules):
    """H12: Forecast P80 load of 55 pax exceeds bus capacity (45 pax)."""
    t = make_clean_trip(trip_id="T_H12_1", vehicle_id="B1")
    plan = Plan(plan_id="p_h12_1", name="H12 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules, p80_loads={"T_H12_1": 55})
    assert any(v.code == "H12" and "exceeds rated vehicle capacity" in v.detail for v in viols)


def test_h12_p80_load_exceeds_minibus_capacity(fleet, rules):
    """H12: Forecast P80 load of 25 pax exceeds minibus capacity (22 pax)."""
    t = make_clean_trip(trip_id="T_H12_2", vehicle_id="M1")
    plan = Plan(plan_id="p_h12_2", name="H12 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules, p80_loads={"T_H12_2": 25})
    assert any(v.code == "H12" and "exceeds rated vehicle capacity" in v.detail for v in viols)


def test_h12_extreme_surge_overload(fleet, rules):
    """H12: Extreme demand surge of 90 pax assigned to standard bus."""
    t = make_clean_trip(trip_id="T_H12_3", vehicle_id="B2")
    plan = Plan(plan_id="p_h12_3", name="H12 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules, p80_loads={"T_H12_3": 90})
    assert any(v.code == "H12" and "90 pax" in v.detail for v in viols)


def test_h12_p80_load_in_plan_metadata(fleet, rules):
    """H12: P80 load stored in plan.metadata['p80_loads']."""
    t = make_clean_trip(trip_id="T_H12_4", vehicle_id="M2")
    plan = Plan(
        plan_id="p_h12_4", name="H12 Test", window=["07:30", "08:30"],
        trips=[t], metadata={"p80_loads": {"T_H12_4": 30}}
    )
    viols = validate(plan, fleet=fleet, rules=rules)
    assert any(v.code == "H12" and "30 pax" in v.detail for v in viols)


# ---------------------------------------------------------------------------
# 14. Soft Checks: A1 (Overcrowding), A4 (Missed Conn), A6 (Bunching/Gap)
# ---------------------------------------------------------------------------

def test_a1_soft_overcrowding_88_percent(fleet, rules):
    """A1: Load at 88% capacity (40 pax on capacity 45) -> soft alert."""
    t = make_clean_trip(trip_id="T_A1_1", vehicle_id="B1")
    plan = Plan(plan_id="p_a1_1", name="A1 Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules, p80_loads={"T_A1_1": 40})
    a1_viols = [v for v in viols if v.code == "A1"]
    assert len(a1_viols) == 1
    assert a1_viols[0].severity == "soft"
    assert "89% rated capacity" in a1_viols[0].detail


def test_a4_soft_tight_connection_at_hub(fleet, rules):
    """A4: Feeder arrives S03 at 460, connecting departs at 462 (buffer 2 < 4 min)."""
    t_feeder = Trip(
        trip_id="T_feed", route_id="R3", direction=0, vehicle_id="B1",
        departure_min=450, scheduled_stop_times={"S13": 450, "S03": 460}
    )
    t_conn = Trip(
        trip_id="T_conn", route_id="R1", direction=0, vehicle_id="B2",
        departure_min=462, scheduled_stop_times={"S01": 455, "S03": 462}
    )
    plan = Plan(plan_id="p_a4_1", name="A4 Test", window=["07:30", "08:30"], trips=[t_feeder, t_conn])
    transfers = [{"from_route": "R3", "to_route": "R1", "min_transfer_min": 4}]
    viols = validate(plan, fleet=fleet, rules=rules, transfers=transfers)
    a4_viols = [v for v in viols if v.code == "A4"]
    assert len(a4_viols) == 1
    assert a4_viols[0].severity == "soft"


def test_a6_soft_bunching_detected(fleet, rules):
    """A6: Headway 4 min is < 40% of planned headway (12 min)."""
    t1 = make_clean_trip(trip_id="T_A6_1a", route_id="R1", direction=0, vehicle_id="B1", departure_min=450)
    t2 = make_clean_trip(trip_id="T_A6_1b", route_id="R1", direction=0, vehicle_id="B2", departure_min=454)
    plan = Plan(plan_id="p_a6_1", name="A6 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules, planned_headways={"R1": 12})
    a6_viols = [v for v in viols if v.code == "A6" and "Bunching" in v.detail]
    assert len(a6_viols) == 1
    assert a6_viols[0].severity == "soft"


def test_a6_soft_service_gap_detected(fleet, rules):
    """A6: Headway 22 min is > 160% of planned headway (12 min)."""
    t1 = make_clean_trip(trip_id="T_A6_2a", route_id="R1", direction=0, vehicle_id="B1", departure_min=450)
    t2 = make_clean_trip(trip_id="T_A6_2b", route_id="R1", direction=0, vehicle_id="B2", departure_min=472)
    plan = Plan(plan_id="p_a6_2", name="A6 Test", window=["07:30", "08:30"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules, planned_headways={"R1": 12})
    a6_viols = [v for v in viols if v.code == "A6" and "Service gap" in v.detail]
    assert len(a6_viols) == 1
    assert a6_viols[0].severity == "soft"


# ---------------------------------------------------------------------------
# 15. Boundary Condition Tests
# ---------------------------------------------------------------------------

def test_boundary_layover_exact_4min_passes(fleet, rules):
    """Exact 4 min layover passes H3 without violation."""
    t1 = make_clean_trip(trip_id="T_B1", vehicle_id="B1", departure_min=450, duration_min=20) # ends 470
    t2 = make_clean_trip(trip_id="T_B2", vehicle_id="B1", departure_min=474, duration_min=20) # starts 474, layover=4
    plan = Plan(plan_id="p_b1", name="Boundary Test", window=["07:30", "09:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert not any(v.code == "H3" for v in viols)


def test_boundary_departure_shift_exact_5min_passes(fleet, rules):
    """Exact 5 min departure shift from baseline passes H8."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="cand", name="Cand", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T_R1_01", departure_min=455)]
    )
    viols = validate(cand_plan, fleet=fleet, rules=rules, baseline_plan=base_plan)
    assert not any(v.code == "H8" for v in viols)


def test_boundary_continuous_driving_exact_210min_passes(fleet, rules):
    """Exact 210 min continuous driving passes H9."""
    t = make_clean_trip(trip_id="T_B3", vehicle_id="B1", departure_min=450, duration_min=210)
    plan = Plan(plan_id="p_b3", name="Boundary Test", window=["07:30", "12:00"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert not any(v.code == "H9" for v in viols)


def test_boundary_operating_hours_390_and_1320_pass(fleet, rules):
    """Departures at exactly 390 (06:30) and 1320 (22:00) pass H5."""
    t1 = make_clean_trip(trip_id="T_B4a", departure_min=390)
    t2 = make_clean_trip(trip_id="T_B4b", departure_min=1320)
    plan = Plan(plan_id="p_b4", name="Boundary Test", window=["06:30", "22:00"], trips=[t1, t2])
    viols = validate(plan, fleet=fleet, rules=rules)
    assert not any(v.code == "H5" for v in viols)


def test_boundary_capacity_exact_rated_capacity_passes(fleet, rules):
    """P80 load equal to vehicle capacity (45 on 45) passes H12."""
    t = make_clean_trip(trip_id="T_B5", vehicle_id="B1")
    plan = Plan(plan_id="p_b5", name="Boundary Test", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, fleet=fleet, rules=rules, p80_loads={"T_B5": 45})
    assert not any(v.code == "H12" for v in viols)


# ---------------------------------------------------------------------------
# 16. Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

@given(departure_min=st.integers(min_value=390, max_value=1320))
@settings(max_examples=30)
def test_property_valid_operating_hours(departure_min):
    """Any departure between 390 and 1320 raises no H5 violation."""
    t = make_clean_trip(trip_id="T_prop", departure_min=departure_min)
    plan = Plan(plan_id="p_prop", name="Prop", window=["06:30", "22:00"], trips=[t])
    viols = validate(plan)
    assert not any(v.code == "H5" for v in viols)


@given(departure_min=st.one_of(st.integers(min_value=-1000, max_value=389), st.integers(min_value=1321, max_value=2500)))
@settings(max_examples=30)
def test_property_invalid_operating_hours(departure_min):
    """Any departure outside 390..1320 raises an H5 violation."""
    t = make_clean_trip(trip_id="T_prop", departure_min=departure_min)
    plan = Plan(plan_id="p_prop", name="Prop", window=["00:00", "24:00"], trips=[t])
    viols = validate(plan)
    assert any(v.code == "H5" for v in viols)


@given(shift=st.integers(min_value=0, max_value=5))
@settings(max_examples=15)
def test_property_valid_departure_shifts(shift):
    """Shifts <= 5 min raise no H8 violation."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T1", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="cand", name="Cand", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T1", departure_min=450 + shift)]
    )
    viols = validate(cand_plan, baseline_plan=base_plan)
    assert not any(v.code == "H8" for v in viols)


@given(shift=st.integers(min_value=6, max_value=60))
@settings(max_examples=15)
def test_property_invalid_departure_shifts(shift):
    """Shifts > 5 min always raise an H8 violation."""
    base_plan = Plan(
        plan_id="base", name="Base", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T1", departure_min=450)]
    )
    cand_plan = Plan(
        plan_id="cand", name="Cand", window=["07:30", "08:30"],
        trips=[make_clean_trip(trip_id="T1", departure_min=450 + shift)]
    )
    viols = validate(cand_plan, baseline_plan=base_plan)
    assert any(v.code == "H8" for v in viols)


@given(load=st.integers(min_value=46, max_value=200))
@settings(max_examples=15)
def test_property_overload_raises_h12(load):
    """Load exceeding rated capacity (45) always triggers H12."""
    t = make_clean_trip(trip_id="T_load", vehicle_id="B1")
    plan = Plan(plan_id="p_load", name="Load Prop", window=["07:30", "08:30"], trips=[t])
    viols = validate(plan, p80_loads={"T_load": load})
    assert any(v.code == "H12" for v in viols)
