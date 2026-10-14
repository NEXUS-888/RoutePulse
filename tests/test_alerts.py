"""
Unit tests for RoutePulse Conflict & Alert Detector (detect/alerts.py)
Tests all typed alert definitions A1 through A8:
- A1: Overcrowding (soft, load >= 85% of rated capacity)
- A2: Capacity violation (hard-risk, demand exceeds rated capacity, pax left behind)
- A3: Unmet demand (balked passengers > threshold)
- A4: Missed connection (transfer buffer < 4 min at hub S03)
- A5: Schedule conflict (overlapping trips or turnaround layover < 4 min)
- A6: Bunching / Headway Gap (< 40% or > 160% of planned headway)
- A7: Service gap (headway > max_headway or accessibility deficit in route-hour)
- A8: Vehicle unavailable (outside operating hours or active vehicle_out disruption)
- Schema validation against core.schemas.Alert
"""
import pytest
from core.schemas import (
    Alert,
    Plan,
    Trip,
    Vehicle,
    Disruption,
    ServiceRules,
    NetworkResponse,
)
from sim.engine import (
    Simulator,
    Passenger,
    load_default_network,
)
from detect.alerts import ConflictDetector, detect_conflicts


@pytest.fixture
def network() -> NetworkResponse:
    return load_default_network()


def test_alert_a1_overcrowding(network: NetworkResponse):
    """
    Test A1: Emitted when a trip reaches or exceeds 85% rated capacity.
    Vehicle B1 capacity = 45. 85% = 39 pax.
    When 40 passengers board, A1 alert should be emitted with soft severity.
    """
    pax = [
        Passenger(
            pax_id=f"PAX_{i:02d}",
            origin="S01",
            destination="S04",
            arrival_time_min=450.0,
            route_id="R1",
            direction=0,
            needs_transfer=False,
        )
        for i in range(40)
    ]

    trip = Trip(
        trip_id="T_R1_CROWD",
        route_id="R1",
        direction=0,
        vehicle_id="B1",  # Bus capacity 45
        departure_min=450,
        scheduled_stop_times={"S01": 450, "S02": 453, "S03": 456, "S04": 460},
    )

    plan = Plan(
        plan_id="test_a1",
        name="Test A1",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B1": ["T_R1_CROWD"]},
    )

    sim = Simulator(network=network)
    sim_res = sim.run(plan=plan, demand=pax)

    alerts = detect_conflicts(plan=plan, sim_result=sim_res, network=network)
    a1_alerts = [a for a in alerts if a.code == "A1"]

    assert len(a1_alerts) >= 1
    a1 = a1_alerts[0]
    assert a1.severity == "soft"
    assert a1.entity_type == "trip"
    assert a1.entity_id == "T_R1_CROWD"
    assert a1.pax_affected == 40
    # Schema validation
    assert isinstance(a1, Alert)


def test_alert_a2_capacity_violation(network: NetworkResponse):
    """
    Test A2: Emitted when demand exceeds rated capacity and passengers are left behind.
    Bus capacity = 45. 60 passengers arrive. 15 left behind.
    A2 alert should be emitted with hard-risk severity.
    """
    pax = [
        Passenger(
            pax_id=f"PAX_{i:02d}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(60)
    ]

    trip = Trip(
        trip_id="T_R3_OVERLOAD",
        route_id="R3",
        direction=0,
        vehicle_id="B3",  # Bus capacity 45
        departure_min=455,
        scheduled_stop_times={"S13": 455, "S01": 460, "S02": 463, "S03": 467},
    )

    plan = Plan(
        plan_id="test_a2",
        name="Test A2",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_OVERLOAD"]},
    )

    sim = Simulator(network=network)
    sim_res = sim.run(plan=plan, demand=pax)

    alerts = detect_conflicts(plan=plan, sim_result=sim_res, network=network)
    a2_alerts = [a for a in alerts if a.code == "A2"]

    assert len(a2_alerts) >= 1
    a2 = a2_alerts[0]
    assert a2.severity == "hard-risk"
    assert a2.entity_type == "trip"
    assert a2.entity_id == "T_R3_OVERLOAD"
    assert a2.pax_affected == 15
    assert "left behind" in a2.detail.lower()


def test_alert_a3_unmet_demand(network: NetworkResponse):
    """
    Test A3: Emitted when balked passengers exceed threshold at a stop.
    """
    # 5 passengers arrive at S13 and wait > 20 min without bus -> balk
    pax = [
        Passenger(
            pax_id=f"PAX_BALK_{i}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(5)
    ]

    # Trip scheduled at 480 min (30 min wait > 20 min patience)
    trip = Trip(
        trip_id="T_R3_VERY_LATE",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=480,
        scheduled_stop_times={"S13": 480, "S01": 485, "S02": 488, "S03": 492},
    )

    plan = Plan(
        plan_id="test_a3",
        name="Test A3",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_VERY_LATE"]},
    )

    sim = Simulator(network=network)
    sim_res = sim.run(plan=plan, demand=pax)

    detector = ConflictDetector(network=network, balk_threshold_per_hour=1)
    alerts = detector.detect(plan=plan, sim_result=sim_res)

    a3_alerts = [a for a in alerts if a.code == "A3"]
    assert len(a3_alerts) >= 1
    a3 = a3_alerts[0]
    assert a3.entity_type == "stop"
    assert a3.entity_id == "S13"
    assert a3.pax_affected == 5
    assert "balked" in a3.detail.lower()


def test_alert_a4_missed_connection(network: NetworkResponse):
    """
    Test A4: Emitted when transfer buffer at hub S03 is < 4 min.
    """
    pax = [
        Passenger(
            pax_id=f"PAX_TIGHT_{i}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=True,
            connecting_route_id="R2",
            connecting_direction=0,
            final_destination="S08",
        )
        for i in range(8)
    ]

    feeder = Trip(
        trip_id="T_FEEDER",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 454, "S02": 457, "S03": 460},
    )
    # Connecting trip departs at 458 min (buffer ~2.8 min < 4.0 min requirement)
    connecting = Trip(
        trip_id="T_CONNECTING",
        route_id="R2",
        direction=0,
        vehicle_id="M1",
        departure_min=458,
        scheduled_stop_times={"S03": 458, "S10": 461, "S08": 465, "S09": 468},
    )

    plan = Plan(
        plan_id="test_a4",
        name="Test A4",
        window=["07:30", "10:30"],
        trips=[feeder, connecting],
        vehicle_blocks={"B3": ["T_FEEDER"], "M1": ["T_CONNECTING"]},
    )

    sim = Simulator(network=network, min_transfer_min=4.0)
    sim_res = sim.run(plan=plan, demand=pax)

    alerts = detect_conflicts(plan=plan, sim_result=sim_res, network=network)
    a4_alerts = [a for a in alerts if a.code == "A4"]

    assert len(a4_alerts) >= 1
    a4 = a4_alerts[0]
    assert a4.entity_type == "trip"
    assert a4.entity_id == "T_CONNECTING"
    assert a4.pax_affected == 8
    assert "buffer" in a4.detail.lower() or "connection" in a4.detail.lower()


def test_alert_a5_schedule_conflict(network: NetworkResponse):
    """
    Test A5: Emitted when vehicle has overlapping trips or turnaround layover < 4 min.
    Vehicle B1 assigned to Trip 1 ending at 473 and Trip 2 starting at 475 (layover 2 min < 4 min).
    """
    trip1 = Trip(
        trip_id="T1",
        route_id="R1",
        direction=0,
        vehicle_id="B1",
        departure_min=450,
        scheduled_stop_times={"S01": 473, "S02": 453, "S03": 456, "S07": 470},
    )
    trip2 = Trip(
        trip_id="T2",
        route_id="R1",
        direction=0,
        vehicle_id="B1",
        departure_min=475,  # Only 2 min after T1 ends at 473!
        scheduled_stop_times={"S01": 498, "S02": 478, "S03": 481, "S07": 495},
    )

    plan = Plan(
        plan_id="test_a5",
        name="Test A5",
        window=["07:30", "10:30"],
        trips=[trip1, trip2],
        vehicle_blocks={"B1": ["T1", "T2"]},
    )

    detector = ConflictDetector(network=network, min_layover_min=4.0)
    alerts = detector.detect(plan=plan)

    a5_alerts = [a for a in alerts if a.code == "A5"]
    assert len(a5_alerts) >= 1
    a5 = a5_alerts[0]
    assert a5.severity == "hard-risk"
    assert a5.entity_type == "vehicle"
    assert a5.entity_id == "B1"
    assert "layover" in a5.detail.lower()


def test_alert_a6_bunching_and_gap(network: NetworkResponse):
    """
    Test A6: Emitted for bus bunching (< 40% planned headway) and headway gaps (> 160% planned headway).
    Planned headway on R1 is 12 min.
    40% of 12 = 4.8 min. Headway of 3 min triggers bunching alert.
    160% of 12 = 19.2 min. Headway of 22 min triggers gap alert.
    """
    # Trip 1 at 450, Trip 2 at 453 (headway 3 min < 4.8 min -> bunching!)
    # Trip 3 at 475 (headway 22 min > 19.2 min -> gap!)
    t1 = Trip(
        trip_id="T_R1_01",
        route_id="R1",
        direction=0,
        vehicle_id="B1",
        departure_min=450,
        scheduled_stop_times={"S01": 470},
    )
    t2 = Trip(
        trip_id="T_R1_02",
        route_id="R1",
        direction=0,
        vehicle_id="B2",
        departure_min=453,
        scheduled_stop_times={"S01": 473},
    )
    t3 = Trip(
        trip_id="T_R1_03",
        route_id="R1",
        direction=0,
        vehicle_id="B3",
        departure_min=475,
        scheduled_stop_times={"S01": 495},
    )

    plan = Plan(
        plan_id="test_a6",
        name="Test A6",
        window=["07:30", "10:30"],
        trips=[t1, t2, t3],
        vehicle_blocks={"B1": ["T_R1_01"], "B2": ["T_R1_02"], "B3": ["T_R1_03"]},
    )

    detector = ConflictDetector(network=network)
    alerts = detector.detect(plan=plan)

    a6_alerts = [a for a in alerts if a.code == "A6"]
    assert len(a6_alerts) >= 2
    bunching = [a for a in a6_alerts if "bunching" in a.title.lower()]
    gap = [a for a in a6_alerts if "gap" in a.title.lower()]
    assert len(bunching) >= 1
    assert len(gap) >= 1
    assert bunching[0].entity_type == "route"
    assert bunching[0].entity_id == "R1"


def test_alert_a7_service_gap_and_accessibility(network: NetworkResponse):
    """
    Test A7: Emitted when:
    1) Headway > max_headway (peak 12 min). e.g. headway 25 min.
    2) No accessible vehicle on route during a 1-hour window (e.g. only B3 and B4 used, both non-accessible).
    """
    # Route R1: B3 (accessible=False), B4 (accessible=False)
    # Headway is 25 min (> max_headway 12 min)
    t1 = Trip(
        trip_id="T_R1_01",
        route_id="R1",
        direction=0,
        vehicle_id="B3",  # accessible=False
        departure_min=450,
        scheduled_stop_times={"S01": 470},
    )
    t2 = Trip(
        trip_id="T_R1_02",
        route_id="R1",
        direction=0,
        vehicle_id="B4",  # accessible=False
        departure_min=475,  # headway 25 min
        scheduled_stop_times={"S01": 495},
    )

    plan = Plan(
        plan_id="test_a7",
        name="Test A7",
        window=["07:30", "10:30"],
        trips=[t1, t2],
        vehicle_blocks={"B3": ["T_R1_01"], "B4": ["T_R1_02"]},
    )

    rules = ServiceRules(max_headway_peak=12, accessible_min_per_route_hour=1)
    detector = ConflictDetector(network=network, rules=rules)
    alerts = detector.detect(plan=plan)

    a7_alerts = [a for a in alerts if a.code == "A7"]
    assert len(a7_alerts) >= 1
    # Check max headway alert
    headway_alerts = [a for a in a7_alerts if "service gap" in a.title.lower()]
    assert len(headway_alerts) >= 1
    assert headway_alerts[0].severity == "hard-risk"

    # Check accessibility alert
    access_alerts = [a for a in a7_alerts if "accessibility" in a.title.lower()]
    assert len(access_alerts) >= 1
    assert access_alerts[0].severity == "hard-risk"
    assert access_alerts[0].entity_type == "route"
    assert access_alerts[0].entity_id == "R1"


def test_alert_a8_vehicle_unavailable_disruption(network: NetworkResponse):
    """
    Test A8: Emitted when assigned vehicle is out of service during an active breakdown disruption,
    or scheduled outside its operating hours.
    """
    trip = Trip(
        trip_id="T_R1_DISRUPTED",
        route_id="R1",
        direction=0,
        vehicle_id="B2",
        departure_min=500,  # 08:20
        scheduled_stop_times={"S01": 520},
    )

    plan = Plan(
        plan_id="test_a8",
        name="Test A8",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B2": ["T_R1_DISRUPTED"]},
    )

    # Disruption: B2 out of service 495 - 630 min (08:15 - 10:30)
    disruptions = [
        Disruption(
            type="vehicle_out",
            params={"vehicle_id": "B2"},
            start_min=495,
            end_min=630,
        )
    ]

    detector = ConflictDetector(network=network)
    alerts = detector.detect(plan=plan, disruptions=disruptions)

    a8_alerts = [a for a in alerts if a.code == "A8"]
    assert len(a8_alerts) >= 1
    a8 = a8_alerts[0]
    assert a8.severity == "hard-risk"
    assert a8.entity_type == "vehicle"
    assert a8.entity_id == "B2"
    assert "disruption" in a8.detail.lower() or "out of service" in a8.detail.lower()
