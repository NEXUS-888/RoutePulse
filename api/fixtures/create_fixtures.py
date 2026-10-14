"""
Generates initial frozen JSON fixtures that validate against core/schemas.py
"""
import json
from pathlib import Path
from core.schemas import (
    Stop, Route, Vehicle, Transfer, Trip, Plan, GpsPing, ApcRecord,
    Violation, Recommendation, Alert, EtaPrediction, EtaResponse,
    VehicleEtaResponse, DemandSlot, DemandResponse, PlanValidationResponse,
    ApplyRecommendationResponse, WhatIfResponse, ScenarioRunResponse,
    EvalResultsResponse, StudentRouteOption, StudentRouteResponse,
    HealthResponse, NetworkResponse
)
from core.geometry import xy_to_latlon

FIXTURES_DIR = Path(__file__).resolve().parent

# 14 stops
STOPS_DATA = [
    ("S01", "Main Gate", 0.0, 0.0, False, True),
    ("S02", "Admin Block", 350.0, 150.0, False, True),
    ("S03", "Central Hub", 600.0, 400.0, True, True),
    ("S04", "Library", 850.0, 450.0, False, True),
    ("S05", "Engineering", 1100.0, 600.0, False, True),
    ("S06", "Science", 1000.0, 900.0, False, True),
    ("S07", "Auditorium", 550.0, 850.0, False, True),
    ("S08", "Hostel A", 400.0, 1200.0, False, True),
    ("S09", "Hostel B", 650.0, 1300.0, False, True),
    ("S10", "Food Court", 500.0, 700.0, False, True),
    ("S11", "Sports Complex", 1400.0, 300.0, False, True),
    ("S12", "Research Park", 1200.0, 200.0, False, True),
    ("S13", "Metro Station", -1500.0, -600.0, False, True),
    ("S14", "Medical Centre", 800.0, 250.0, False, True),
]

STOPS = []
STOP_MAP = {}
for sid, name, x, y, is_hub, accessible in STOPS_DATA:
    lat, lon = xy_to_latlon(x, y)
    s = Stop(
        stop_id=sid,
        name=name,
        x=x,
        y=y,
        lat=lat,
        lon=lon,
        is_hub=is_hub,
        accessible=accessible,
        capacity_waiting=100 if is_hub else 40
    )
    STOPS.append(s)
    STOP_MAP[sid] = s

# 4 routes
def make_route(rid: str, name: str, rtype: str, seq: list[str], speed: float = 8.0) -> Route:
    polyline = [[STOP_MAP[sid].x, STOP_MAP[sid].y] for sid in seq]
    seg_lengths = []
    for i in range(len(polyline) - 1):
        x1, y1 = polyline[i]
        x2, y2 = polyline[i+1]
        dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
        seg_lengths.append(round(dist, 1))
    return Route(
        route_id=rid,
        name=name,
        type=rtype, # type: ignore
        stop_sequence=seq,
        polyline=polyline,
        segment_lengths_m=seg_lengths,
        free_flow_speed_mps=speed
    )

ROUTES = [
    make_route("R1", "Main Loop", "loop", ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S01"]),
    make_route("R2", "Hostel Express", "loop", ["S03", "S10", "S08", "S09", "S03"]),
    make_route("R3", "Metro Connector", "linear", ["S13", "S01", "S02", "S03"]),
    make_route("R4", "Research/Sports Shuttle", "linear", ["S03", "S14", "S12", "S11"]),
]

# 10 vehicles
VEHICLES = []
for i in range(1, 7):
    vid = f"B{i}"
    VEHICLES.append(Vehicle(
        vehicle_id=vid,
        type="bus",
        capacity=45,
        seated=30,
        accessible=(vid in ["B1", "B2"]),
        depot_stop="S01",
        available_from=390,
        available_to=1320
    ))
for j in range(1, 5):
    vid = f"M{j}"
    VEHICLES.append(Vehicle(
        vehicle_id=vid,
        type="minibus",
        capacity=22,
        seated=16,
        accessible=(vid == "M1"),
        depot_stop="S01",
        available_from=390,
        available_to=1320
    ))

TRANSFERS = [
    Transfer(from_route="R1", to_route="R2", hub_stop_id="S03", min_transfer_min=4),
    Transfer(from_route="R2", to_route="R1", hub_stop_id="S03", min_transfer_min=4),
    Transfer(from_route="R3", to_route="R1", hub_stop_id="S03", min_transfer_min=4),
    Transfer(from_route="R1", to_route="R3", hub_stop_id="S03", min_transfer_min=4),
    Transfer(from_route="R3", to_route="R2", hub_stop_id="S03", min_transfer_min=4),
    Transfer(from_route="R4", to_route="R1", hub_stop_id="S03", min_transfer_min=4),
]

NETWORK = NetworkResponse(
    stops=STOPS,
    routes=ROUTES,
    vehicles=VEHICLES,
    transfers=TRANSFERS
)

# Sample Trips for Baseline Plan (W1: 07:30-10:30, i.e. 450 to 630 min)
SAMPLE_TRIPS = [
    Trip(
        trip_id="T_R1_01",
        route_id="R1",
        direction=0,
        vehicle_id="B1",
        departure_min=450,
        scheduled_stop_times={"S01": 450, "S02": 453, "S03": 456, "S04": 460, "S05": 464, "S06": 467, "S07": 470, "S01": 473}
    ),
    Trip(
        trip_id="T_R3_01",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 455, "S02": 458, "S03": 462}
    ),
    Trip(
        trip_id="T_R2_01",
        route_id="R2",
        direction=0,
        vehicle_id="M1",
        departure_min=465,
        scheduled_stop_times={"S03": 465, "S10": 468, "S08": 472, "S09": 475, "S03": 479}
    ),
    Trip(
        trip_id="T_R4_01",
        route_id="R4",
        direction=0,
        vehicle_id="M2",
        departure_min=460,
        scheduled_stop_times={"S03": 460, "S14": 464, "S12": 468, "S11": 473}
    )
]

BASELINE_PLAN = Plan(
    plan_id="baseline_w1",
    name="Baseline Morning Peak Plan",
    window=["07:30", "10:30"],
    trips=SAMPLE_TRIPS,
    vehicle_blocks={
        "B1": ["T_R1_01"],
        "B3": ["T_R3_01"],
        "M1": ["T_R2_01"],
        "M2": ["T_R4_01"]
    },
    metadata={"status": "frozen", "hash": "baseline-v0"}
)

# ETA Fixture
ETA_RESPONSE = EtaResponse(
    stop_id="S03",
    query_time_min=455,
    arrivals=[
        EtaPrediction(
            stop_id="S03",
            route_id="R1",
            vehicle_id="B1",
            trip_id="T_R1_01",
            scheduled_time_min=456,
            eta_p10_min=455.5,
            eta_p50_min=457.0,
            eta_p90_min=459.2,
            confidence="high",
            reasons=["Normal traffic", "Low boarding dwell observed"],
            stale_gps=False
        ),
        EtaPrediction(
            stop_id="S03",
            route_id="R3",
            vehicle_id="B3",
            trip_id="T_R3_01",
            scheduled_time_min=462,
            eta_p10_min=462.5,
            eta_p50_min=464.5,
            eta_p90_min=468.0,
            confidence="medium",
            reasons=["Congestion multiplier 1.35x near Main Gate"],
            stale_gps=False
        )
    ]
)

VEHICLE_ETA = VehicleEtaResponse(
    vehicle_id="B1",
    trip_id="T_R1_01",
    current_progress_m=950.0,
    speed_mps=7.8,
    downstream_stops=[
        EtaPrediction(
            stop_id="S03",
            route_id="R1",
            vehicle_id="B1",
            trip_id="T_R1_01",
            scheduled_time_min=456,
            eta_p10_min=455.5,
            eta_p50_min=457.0,
            eta_p90_min=459.2,
            confidence="high",
            reasons=["On-time"],
            stale_gps=False
        ),
        EtaPrediction(
            stop_id="S04",
            route_id="R1",
            vehicle_id="B1",
            trip_id="T_R1_01",
            scheduled_time_min=460,
            eta_p10_min=459.5,
            eta_p50_min=461.2,
            eta_p90_min=463.8,
            confidence="high",
            reasons=["Smooth corridor"],
            stale_gps=False
        )
    ]
)

# Demand Fixture
DEMAND_RESPONSE = DemandResponse(
    stop_id="S13",
    date="2026-10-14",
    slots=[
        DemandSlot(
            slot_start_min=450,
            slot_end_min=465,
            p50_arrivals=52.0,
            p80_arrivals=68.0,
            p90_arrivals=75.0,
            actual_arrivals=64.0
        ),
        DemandSlot(
            slot_start_min=465,
            slot_end_min=480,
            p50_arrivals=58.0,
            p80_arrivals=74.0,
            p90_arrivals=82.0,
            actual_arrivals=71.0
        )
    ]
)

# Alerts Fixture
ALERTS = [
    Alert(
        alert_id="ALT-001",
        code="A2",
        severity="hard-risk",
        title="Capacity Risk on Route R3",
        detail="P80 demand (74 pax) exceeds bus capacity (45 pax) on trip T_R3_01 departing 07:45.",
        entity_type="trip",
        entity_id="T_R3_01",
        time_min=465,
        pax_affected=29
    ),
    Alert(
        alert_id="ALT-002",
        code="A4",
        severity="soft",
        title="Tight Connection at Hub",
        detail="Feeder trip T_R3_01 projected to arrive S03 at 07:44:30; connecting trip T_R2_01 departs 07:45.",
        entity_type="trip",
        entity_id="T_R2_01",
        time_min=465,
        pax_affected=14
    )
]

# Recommendations Fixture
RECOMMENDATION = Recommendation(
    id="rec-0007",
    type="ADD_TRIP",
    summary="Add an R3 departure at 08:21 from S13 using bus B5 (idle reserve)",
    reason_codes=["A2_CAPACITY_RISK", "A4_MISSED_CONNECTION"],
    evidence={"p80_load_before": 1.34, "p80_load_after": 0.91, "pax_affected": 62},
    impact={"avg_wait_min": -1.8, "left_behind": -41, "missed_connections": -17, "vehicle_km": 14.2},
    tradeoff="Uses a reserve bus for 52 min (+14.2 vehicle-km). Reduces R3 left-behind passengers by 41. R1 headway unchanged.",
    binding_constraints=["H6 fleet size at 08:30", "H3 layover for B5"],
    alternatives_rejected=[{"option": "retime 08:24 trip earlier", "why": "violates H8 and still leaves load at 1.12"}],
    validated=True,
    violations=[],
    confidence="high"
)

APPLY_REC = ApplyRecommendationResponse(
    applied_recommendation_id="rec-0007",
    new_plan_id="plan_opt_rec0007",
    new_plan=BASELINE_PLAN,
    kpi_deltas={"avg_wait_min": -1.8, "left_behind": -41, "missed_connections": -17, "vehicle_km": 14.2},
    validated=True,
    violations=[]
)

PLAN_VALIDATION = PlanValidationResponse(
    is_valid=True,
    hard_violations_count=0,
    soft_violations_count=1,
    violations=[
        Violation(
            code="A1",
            severity="soft",
            entity="T_R3_01",
            time=465,
            detail="Peak departure load projected at 88% rated capacity."
        )
    ]
)

WHATIF = WhatIfResponse(
    validated=True,
    violations=[],
    simulated_kpis={"avg_wait_min": 5.4, "left_behind_pax": 12, "missed_connections": 3, "vehicle_km": 112.4},
    delta_vs_base={"avg_wait_min": -1.5, "left_behind_pax": -35, "missed_connections": -12, "vehicle_km": 12.0}
)

SCENARIO_RUN = ScenarioRunResponse(
    scenario_id="S0",
    plan_id="baseline_w1",
    seed=20261014,
    kpis={"mean_wait_min": 6.9, "left_behind_pax": 47.0, "missed_connections": 15.0, "fleet_utilization": 0.78, "violations": 0.0}
)

EVAL_RESULTS = EvalResultsResponse(
    summary_table=[
        {"system": "Baseline-0", "scenario": "S0 (Normal)", "wait_min": "6.9 ± 0.4", "left_behind": "47.2 ± 3.1", "missed_conn": "15.1 ± 1.2", "hard_violations": 0},
        {"system": "Baseline-1", "scenario": "S0 (Normal)", "wait_min": "6.1 ± 0.3", "left_behind": "32.0 ± 2.8", "missed_conn": "11.4 ± 1.0", "hard_violations": 0},
        {"system": "RoutePulse", "scenario": "S0 (Normal)", "wait_min": "5.1 ± 0.2", "left_behind": "12.4 ± 1.5", "missed_conn": "6.2 ± 0.7", "hard_violations": 0},
        {"system": "Baseline-0", "scenario": "S1 (Traffic)", "wait_min": "9.4 ± 0.6", "left_behind": "84.1 ± 5.2", "missed_conn": "29.3 ± 2.1", "hard_violations": 0},
        {"system": "RoutePulse", "scenario": "S1 (Traffic)", "wait_min": "6.8 ± 0.3", "left_behind": "28.5 ± 2.6", "missed_conn": "13.0 ± 1.1", "hard_violations": 0},
        {"system": "Baseline-0", "scenario": "S2 (Vehicle Out)", "wait_min": "10.2 ± 0.7", "left_behind": "112.0 ± 7.0", "missed_conn": "34.5 ± 2.4", "hard_violations": 0},
        {"system": "RoutePulse", "scenario": "S2 (Vehicle Out)", "wait_min": "7.1 ± 0.4", "left_behind": "34.1 ± 3.0", "missed_conn": "14.2 ± 1.2", "hard_violations": 0},
        {"system": "Baseline-0", "scenario": "S3 (Demand Surge)", "wait_min": "8.8 ± 0.5", "left_behind": "96.4 ± 6.1", "missed_conn": "24.0 ± 1.8", "hard_violations": 0},
        {"system": "RoutePulse", "scenario": "S3 (Demand Surge)", "wait_min": "6.0 ± 0.3", "left_behind": "22.6 ± 2.1", "missed_conn": "9.8 ± 0.9", "hard_violations": 0}
    ],
    scenarios={"S0": "Normal", "S1": "Traffic Delay", "S2": "Vehicle Breakdown", "S3": "Auditorium Demand Surge"},
    chart_paths=["results/wait_by_scenario.png", "results/load_profile_R3.png", "results/eta_error_by_horizon.png", "results/coverage.png"],
    timestamp="2026-10-14T12:00:00Z"
)

STUDENT_ROUTE = StudentRouteResponse(
    from_stop="S13",
    to_stop="S04",
    query_time_min=460,
    options=[
        StudentRouteOption(
            itinerary_id="ITIN-01",
            route_id="R3",
            from_stop="S13",
            to_stop="S04",
            departure_min=465,
            eta_p10_min=479.0,
            eta_p50_min=482.0,
            eta_p90_min=485.0,
            is_transfer=True,
            transfer_stop="S03",
            transfer_safe_prob=0.94,
            accessible=True,
            crowding_level="moderate",
            recommendation_note="Transfer at Central Hub S03 to Route R1 (4 min connection buffer)"
        ),
        StudentRouteOption(
            itinerary_id="ITIN-02",
            route_id="R3",
            from_stop="S13",
            to_stop="S04",
            departure_min=477,
            eta_p10_min=491.0,
            eta_p50_min=494.0,
            eta_p90_min=497.0,
            is_transfer=True,
            transfer_stop="S03",
            transfer_safe_prob=0.98,
            accessible=True,
            crowding_level="low",
            recommendation_note="Less crowded departure; highly reliable transfer"
        )
    ]
)

HEALTH = HealthResponse(
    status="ok",
    version="0.1.0",
    data_hash="data-seed-20261014-v1",
    model_hash="models-v1",
    master_seed=20261014,
    uptime_s=120.0
)

def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "network.json": NETWORK.model_dump(),
        "baseline_plan.json": BASELINE_PLAN.model_dump(),
        "eta_stop.json": ETA_RESPONSE.model_dump(),
        "eta_vehicle.json": VEHICLE_ETA.model_dump(),
        "demand.json": DEMAND_RESPONSE.model_dump(),
        "alerts.json": [a.model_dump() for a in ALERTS],
        "recommendations.json": [RECOMMENDATION.model_dump()],
        "applied_recommendation.json": APPLY_REC.model_dump(),
        "plan_validation.json": PLAN_VALIDATION.model_dump(),
        "whatif.json": WHATIF.model_dump(),
        "scenario_run.json": SCENARIO_RUN.model_dump(),
        "eval_results.json": EVAL_RESULTS.model_dump(),
        "student_route.json": STUDENT_ROUTE.model_dump(),
        "health.json": HEALTH.model_dump(),
    }
    for fname, data in fixtures.items():
        p = FIXTURES_DIR / fname
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Generated {p.name}")

    # Also save config/baseline_plan.json
    config_plan = FIXTURES_DIR.parent.parent / "config" / "baseline_plan.json"
    with open(config_plan, "w", encoding="utf-8") as f:
        json.dump(BASELINE_PLAN.model_dump(), f, indent=2)
    print(f"Generated {config_plan}")

if __name__ == "__main__":
    main()
