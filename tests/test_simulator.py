"""
Unit tests for RoutePulse Discrete-Event Simulator (sim/engine.py)
Tests:
- FIFO queueing and boarding up to rated vehicle capacity
- Left-behind passengers continuing to wait for subsequent trips
- Patience limit (20 min) -> passenger balking (unmet demand)
- Dwell time formula: max(6, 5 + 1.4*boardings + 0.8*alightings) seconds
- Hub S03 transfer tracking with 4 min buffer requirement
- Missed connection detection when connecting vehicle departs before arrival + 4 min
- Fleet utilization, vehicle-km, seat-km offered and used
- Output conformity to schemas (ApcRecord, KPIs, etc.)
- Determinism under fixed seed
"""
import pytest
from core.schemas import Plan, Trip, ApcRecord, Stop, Route, Vehicle, Transfer, NetworkResponse
from sim.engine import (
    Simulator,
    SimulationResult,
    Passenger,
    TravelTimeModel,
    NetworkTopology,
    load_default_network,
    generate_peak_demand,
)


@pytest.fixture
def network() -> NetworkResponse:
    return load_default_network()


def test_fifo_queueing_and_capacity_limit(network: NetworkResponse):
    """
    Verify FIFO queueing and capacity limit:
    When 60 passengers arrive at S13 for R3, but vehicle B3 has capacity 45:
    First 45 board in FIFO order, 15 are left behind.
    """
    # 60 passengers arriving at S13 between 450.0 and 455.0
    passengers = [
        Passenger(
            pax_id=f"PAX_{i:03d}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0 + (i * 0.05),
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(60)
    ]

    trip = Trip(
        trip_id="T_R3_01",
        route_id="R3",
        direction=0,
        vehicle_id="B3",  # Bus capacity = 45
        departure_min=460,
        scheduled_stop_times={"S13": 460, "S01": 465, "S02": 468, "S03": 472},
    )

    plan = Plan(
        plan_id="test_fifo_cap",
        name="Test FIFO Capacity",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_01"]},
    )

    sim = Simulator(network=network)
    result = sim.run(plan=plan, demand=passengers)

    tm = result.trip_metrics["T_R3_01"]
    # Vehicle capacity is 45
    assert tm.capacity == 45
    assert tm.stop_boardings["S13"] == 45
    assert tm.max_load == 45
    assert tm.left_behind_count == 15

    # First 45 passengers boarded
    for p in passengers[:45]:
        assert p.status == "completed" or p.status == "boarded"
        assert p.board_time_min == 460.0
        assert p.left_behind_count == 0

    # Remaining 15 passengers were left behind
    for p in passengers[45:]:
        assert p.left_behind_count >= 1


def test_left_behind_passengers_board_subsequent_trip(network: NetworkResponse):
    """
    Verify left-behind passengers continue waiting in queue and board
    the next arriving trip if patience limit has not elapsed.
    """
    # 60 passengers at S13
    passengers = [
        Passenger(
            pax_id=f"PAX_{i:03d}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0 + (i * 0.05),
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(60)
    ]

    # Trip 1 departs at 455, Trip 2 departs at 465 (10 min later, well within 20 min patience)
    trip1 = Trip(
        trip_id="T_R3_01",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=455,
        scheduled_stop_times={"S13": 455, "S01": 460, "S02": 463, "S03": 467},
    )
    trip2 = Trip(
        trip_id="T_R3_02",
        route_id="R3",
        direction=0,
        vehicle_id="B4",
        departure_min=465,
        scheduled_stop_times={"S13": 465, "S01": 470, "S02": 473, "S03": 477},
    )

    plan = Plan(
        plan_id="test_subsequent_trip",
        name="Test Subsequent Trip",
        window=["07:30", "10:30"],
        trips=[trip1, trip2],
        vehicle_blocks={"B3": ["T_R3_01"], "B4": ["T_R3_02"]},
    )

    sim = Simulator(network=network)
    result = sim.run(plan=plan, demand=passengers)

    # Trip 1 took 45 pax
    assert result.trip_metrics["T_R3_01"].stop_boardings["S13"] == 45
    # Trip 2 took the remaining 15 left-behind pax
    assert result.trip_metrics["T_R3_02"].stop_boardings["S13"] == 15

    # All 60 passengers eventually boarded and completed
    for p in passengers:
        assert p.status in ["boarded", "completed"]

    # Exactly 15 passengers experienced a left-behind event
    left_behind_pax = [p for p in passengers if p.left_behind_count > 0]
    assert len(left_behind_pax) == 15
    assert result.kpis["left_behind_pax"] == 15.0
    assert result.kpis["balked_pax"] == 0.0


def test_patience_limit_balking(network: NetworkResponse):
    """
    Verify patience limit (20 min) -> balking (unmet demand):
    If no bus arrives within 20 min of passenger arrival, passenger balks.
    """
    pax = [
        Passenger(
            pax_id="PAX_BALK_1",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
    ]

    # Trip departs at 475 min (25 min after arrival > 20 min patience)
    trip = Trip(
        trip_id="T_R3_LATE",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=475,
        scheduled_stop_times={"S13": 475, "S01": 480, "S02": 483, "S03": 487},
    )

    plan = Plan(
        plan_id="test_balk",
        name="Test Balking",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_LATE"]},
    )

    sim = Simulator(network=network, patience_min=20.0)
    result = sim.run(plan=plan, demand=pax)

    # Passenger should have balked at 450 + 20 = 470 min
    assert pax[0].status == "balked"
    assert pax[0].balk_time_min == 470.0
    assert result.kpis["balked_pax"] == 1.0
    assert result.kpis["unmet_demand_pax"] == 1.0
    assert len(result.balked_passengers) == 1
    # Trip when it arrived at 475 had 0 passengers to board
    assert result.trip_metrics["T_R3_LATE"].stop_boardings["S13"] == 0


def test_dwell_time_calculation(network: NetworkResponse):
    """
    Verify dwell time: max(6, 5 + 1.4*boardings + 0.8*alightings) seconds.
    - Zero boardings/alightings: max(6, 5 + 0) = 6 seconds (0.1 min)
    - 10 boardings, 5 alightings: max(6, 5 + 1.4*10 + 0.8*5) = 23 seconds (23/60 min)
    """
    passengers = [
        Passenger(
            pax_id=f"PAX_{i:02d}",
            origin="S13",
            destination="S01",  # Alight at S01
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(10)
    ]
    # Plus 5 passengers boarding at S01
    passengers += [
        Passenger(
            pax_id=f"PAX_S01_{i:02d}",
            origin="S01",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(5)
    ]

    trip = Trip(
        trip_id="T_R3_DWELL",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 455, "S02": 458, "S03": 462},
    )

    plan = Plan(
        plan_id="test_dwell",
        name="Test Dwell",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_DWELL"]},
    )

    sim = Simulator(network=network)
    result = sim.run(plan=plan, demand=passengers)
    tm = result.trip_metrics["T_R3_DWELL"]

    # At S01: 10 alightings, 5 boardings
    # dwell = max(6, 5 + 1.4*5 + 0.8*10) = max(6, 5 + 7 + 8) = 20.0 seconds = 0.333 min
    arr_s01 = tm.stop_arrivals["S01"]
    dep_s01 = tm.stop_departures["S01"]
    dwell_s01_sec = (dep_s01 - arr_s01) * 60.0
    assert pytest.approx(dwell_s01_sec, abs=1e-2) == 20.0


def test_transfer_tracking_and_missed_connection(network: NetworkResponse):
    """
    Verify transfer tracking at Central Hub S03 with 4 min buffer:
    Feeder trip on R3 arrives at S03.
    Connecting trip on R2 departs S03.
    Case A: connecting trip departs < 4 min after feeder arrival -> Missed Connection detected!
    """
    # Passenger transferring from R3 to R2 at S03
    pax = [
        Passenger(
            pax_id="PAX_XFER_1",
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
    ]

    # Feeder trip departs S13 at 450, scheduled arrival at S03 at 460
    # Actual arrival will be ~463 min
    feeder_trip = Trip(
        trip_id="T_FEEDER",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 454, "S02": 457, "S03": 460},
    )

    # Connecting trip on R2 departs S03 at 458 (only ~2.8 min buffer vs arrival at 455.2 < 4 min requirement!)
    connecting_trip = Trip(
        trip_id="T_CONN",
        route_id="R2",
        direction=0,
        vehicle_id="M1",
        departure_min=458,
        scheduled_stop_times={"S03": 458, "S10": 461, "S08": 465, "S09": 468},
    )

    plan = Plan(
        plan_id="test_xfer_missed",
        name="Test Transfer Missed Connection",
        window=["07:30", "10:30"],
        trips=[feeder_trip, connecting_trip],
        vehicle_blocks={"B3": ["T_FEEDER"], "M1": ["T_CONN"]},
    )

    sim = Simulator(network=network, min_transfer_min=4.0)
    result = sim.run(plan=plan, demand=pax)

    # Feeder arrival at S03 is around ~458-463 min.
    # Connecting trip departs at 462 min.
    # Since connecting trip departs before feeder_arrival + 4 min buffer, missed connection must trigger!
    assert pax[0].missed_connection is True
    assert result.kpis["missed_connections"] == 1.0
    assert len(result.missed_connections) == 1
    assert result.missed_connections[0]["feeder_trip_id"] == "T_FEEDER"
    assert result.missed_connections[0]["connecting_trip_id"] == "T_CONN"


def test_transfer_success_with_sufficient_buffer(network: NetworkResponse):
    """
    Verify that when transfer buffer >= 4 min, the connection is successful and passenger completes journey.
    """
    pax = [
        Passenger(
            pax_id="PAX_XFER_OK",
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
    ]

    feeder = Trip(
        trip_id="T_FEEDER_OK",
        route_id="R3",
        direction=0,
        vehicle_id="B3",
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 454, "S02": 457, "S03": 460},
    )

    # Connecting trip departs at 470 min (10 min after scheduled arrival > 4 min buffer)
    connecting = Trip(
        trip_id="T_CONN_OK",
        route_id="R2",
        direction=0,
        vehicle_id="M1",
        departure_min=470,
        scheduled_stop_times={"S03": 470, "S10": 473, "S08": 477, "S09": 480},
    )

    plan = Plan(
        plan_id="test_xfer_ok",
        name="Test Transfer OK",
        window=["07:30", "10:30"],
        trips=[feeder, connecting],
        vehicle_blocks={"B3": ["T_FEEDER_OK"], "M1": ["T_CONN_OK"]},
    )

    sim = Simulator(network=network)
    result = sim.run(plan=plan, demand=pax)

    assert pax[0].missed_connection is False
    assert pax[0].status == "completed"
    assert result.kpis["missed_connections"] == 0.0


def test_vehicle_km_and_fleet_utilization(network: NetworkResponse):
    """
    Verify vehicle-km, seat-km offered, seat-km used, and fleet utilization calculations.
    """
    trip = Trip(
        trip_id="T_R3_KM",
        route_id="R3",
        direction=0,
        vehicle_id="B3",  # capacity 45
        departure_min=450,
        scheduled_stop_times={"S13": 450, "S01": 454, "S02": 457, "S03": 460},
    )

    # 10 passengers traveling full length S13 -> S03
    pax = [
        Passenger(
            pax_id=f"PAX_{i}",
            origin="S13",
            destination="S03",
            arrival_time_min=450.0,
            route_id="R3",
            direction=0,
            needs_transfer=False,
        )
        for i in range(10)
    ]

    plan = Plan(
        plan_id="test_km",
        name="Test KM",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B3": ["T_R3_KM"]},
    )

    sim = Simulator(network=network)
    result = sim.run(plan=plan, demand=pax)

    # Route R3 segments: 1615.5m + 380.8m + 353.6m = 2349.9m = ~2.35 km
    assert result.vehicle_km > 2.0
    assert result.seat_km_offered > 0.0
    assert result.seat_km_used > 0.0
    # 10 pax on 45-capacity bus -> fleet utilization is 10/45 = ~0.222
    assert pytest.approx(result.fleet_utilization, rel=1e-2) == (10.0 / 45.0)


def test_simulation_determinism(network: NetworkResponse):
    """
    Verify determinism: running simulation twice with the same seed produces identical KPIs.
    """
    trip = Trip(
        trip_id="T_R1_01",
        route_id="R1",
        direction=0,
        vehicle_id="B1",
        departure_min=450,
        scheduled_stop_times={"S01": 450, "S02": 453, "S03": 456, "S04": 460, "S05": 464, "S06": 467, "S07": 470},
    )
    plan = Plan(
        plan_id="test_det",
        name="Test Determinism",
        window=["07:30", "10:30"],
        trips=[trip],
        vehicle_blocks={"B1": ["T_R1_01"]},
    )

    sim1 = Simulator(network=network)
    res1 = sim1.run(plan=plan, seed=20261014)

    sim2 = Simulator(network=network)
    res2 = sim2.run(plan=plan, seed=20261014)

    assert res1.kpis == res2.kpis
    assert len(res1.apc_records) == len(res2.apc_records)
    for a1, a2 in zip(res1.apc_records, res2.apc_records):
        assert a1.boardings == a2.boardings
        assert a1.alightings == a2.alightings
        assert a1.load_after == a2.load_after
