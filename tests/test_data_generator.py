"""
Unit and Property Tests for RoutePulse World and Data Generator.
Verifies determinism, dataset quality rules, corruption detection, and split integrity.
"""
from __future__ import annotations
import math
from pathlib import Path
import pytest
import pandas as pd

from core.config import get_master_seed
from core.schemas import NetworkResponse, Plan, Stop, Route, Vehicle
from core.io import load_json, load_parquet
from sim.generate_world import generate_world, compute_dataset_hash
from sim.topology import get_network
from sim.baseline import generate_baseline_plan
from data.validate_dataset import (
    validate_dataset,
    validate_stop_ids,
    validate_route_geometries,
    validate_capacities,
    validate_gps_pings,
    validate_apc_records,
)


def test_generator_determinism(tmp_path: Path):
    """Verifies running the generator with the same seed produces identical SHA-256 hashes."""
    seed = 20261014
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    res1 = generate_world(num_days=2, seed=seed, data_dir=dir1, config_dir=dir1, verbose=False)
    res2 = generate_world(num_days=2, seed=seed, data_dir=dir2, config_dir=dir2, verbose=False)

    assert res1["combined_hash"] == res2["combined_hash"]
    assert res1["per_file_hashes"] == res2["per_file_hashes"]

    # Different seed must yield different hash
    res3 = generate_world(num_days=2, seed=99999999, data_dir=tmp_path / "run3", config_dir=tmp_path / "run3", verbose=False)
    assert res1["combined_hash"] != res3["combined_hash"]


def test_dataset_validation_passes():
    """Verifies that the generated production dataset passes all quality rules with zero violations."""
    errors = validate_dataset("data")
    assert len(errors) == 0, f"Dataset validation failed: {errors}"


def test_network_schema_and_stops():
    """Verifies network topology contains 14 stops, 4 routes, 10 vehicles, and valid hub."""
    net = get_network()
    assert len(net.stops) == 14
    assert len(net.routes) == 4
    assert len(net.vehicles) == 10
    assert any(s.is_hub and s.stop_id == "S03" for s in net.stops)

    # 6 buses (B1, B2 accessible), 4 minibuses (M1 accessible)
    buses = [v for v in net.vehicles if v.type == "bus"]
    minibuses = [v for v in net.vehicles if v.type == "minibus"]
    assert len(buses) == 6
    assert len(minibuses) == 4
    assert {v.vehicle_id for v in net.vehicles if v.accessible} == {"B1", "B2", "M1"}


def test_baseline_plan_constraints():
    """Verifies baseline timetable properties."""
    plan = generate_baseline_plan()
    assert plan.plan_id.startswith("baseline")
    assert len(plan.trips) > 100

    # Operating hours 06:30 (390) to 22:00 (1320)
    for trip in plan.trips:
        assert 390 <= trip.departure_min <= 1320
        # Stop times must be monotonically non-decreasing
        arr_times = list(trip.scheduled_stop_times.values())
        assert all(arr_times[i] <= arr_times[i+1] for i in range(len(arr_times)-1))

    # Active fleet uses 8 vehicles, leaving >= 1 reserve
    active_vehs = set(plan.vehicle_blocks.keys())
    assert len(active_vehs) == 8
    assert "B6" not in active_vehs
    assert "M4" not in active_vehs

    # Layover between consecutive trips >= 4 min
    for vid, trip_ids in plan.vehicle_blocks.items():
        v_trips = [t for t in plan.trips if t.trip_id in trip_ids]
        v_trips.sort(key=lambda t: t.departure_min)
        for i in range(len(v_trips) - 1):
            prev_end = max(v_trips[i].scheduled_stop_times.values())
            next_start = v_trips[i+1].departure_min
            layover = next_start - prev_end
            assert layover >= 4, f"Vehicle {vid} layover between {v_trips[i].trip_id} and {v_trips[i+1].trip_id} is {layover}m (< 4m)"


def test_frozen_splits_integrity():
    """Verifies data splits: train (1-20), validation (21-25), test (26-30)."""
    df_demand = load_parquet("data/demand_obs.parquet")
    df_apc = load_parquet("data/apc_records.parquet")
    df_gps = load_parquet("data/gps_pings.parquet")

    train_days = set(range(1, 21))
    val_days = set(range(21, 26))
    test_days = set(range(26, 31))

    for df, name in [(df_demand, "demand"), (df_apc, "apc"), (df_gps, "gps")]:
        days_in_train = set(df[df["split"] == "train"]["day"].unique())
        days_in_val = set(df[df["split"] == "validation"]["day"].unique())
        days_in_test = set(df[df["split"] == "test"]["day"].unique())

        assert days_in_train == train_days, f"{name} train split days mismatch"
        assert days_in_val == val_days, f"{name} val split days mismatch"
        assert days_in_test == test_days, f"{name} test split days mismatch"

        # Splits must be mutually disjoint
        assert len(days_in_train & days_in_val) == 0
        assert len(days_in_val & days_in_test) == 0
        assert len(days_in_train & days_in_test) == 0


def test_r3_peak_capacity_overload():
    """Verifies that 15-25% of baseline peak trips on R3 exceed rated capacity (45)."""
    df_apc = load_parquet("data/apc_records.parquet")
    # Morning peak: 07:30 to 09:30 (TR3 trips between 450 and 570)
    # Check max load per trip on R3
    r3_apc = df_apc[df_apc["trip_id"].str.startswith("TR3")]
    max_loads = r3_apc.groupby(["day", "trip_id"])["load_after"].max()

    # R3 peak departures in schedule are in morning peak
    # From baseline plan, TR3 trip departures:
    plan = generate_baseline_plan()
    peak_trip_ids = {t.trip_id for t in plan.trips if t.route_id == "R3" and 450 <= t.departure_min <= 570}

    peak_loads = max_loads[max_loads.index.get_level_values("trip_id").isin(peak_trip_ids)]
    total_peak_trips = len(peak_loads)
    overloaded_trips = int((peak_loads >= 45).sum())
    overload_ratio = overloaded_trips / max(1, total_peak_trips)

    assert 0.15 <= overload_ratio <= 0.25, (
        f"R3 peak overload ratio {overload_ratio:.3f} ({overloaded_trips}/{total_peak_trips}) "
        f"outside required [0.15, 0.25] window"
    )


def test_validator_catches_invalid_stop_id():
    """Validator catches injected invalid stop ID."""
    stops = [{"stop_id": "S01"}, {"stop_id": "S02"}]
    routes = [{"route_id": "R1", "stop_sequence": ["S01", "S99"]}]
    errors = validate_stop_ids(stops, routes)
    assert len(errors) == 1
    assert "S99" in errors[0]


def test_validator_catches_geometry_violations():
    """Validator catches stops too far from polyline or segment length mismatch."""
    stops = [
        {"stop_id": "S01", "x": 0.0, "y": 0.0},
        {"stop_id": "S02", "x": 500.0, "y": 500.0},  # 500m away
    ]
    # Polyline does not pass near S02
    routes = [{
        "route_id": "R1",
        "stop_sequence": ["S01", "S02"],
        "polyline": [[0.0, 0.0], [100.0, 0.0]],
        "segment_lengths_m": [100.0],
    }]
    errors = validate_route_geometries(stops, routes)
    assert any("25m limit" in e for e in errors)

    # Segment length mismatch > 1%
    routes_bad_sum = [{
        "route_id": "R1",
        "stop_sequence": ["S01"],
        "polyline": [[0.0, 0.0], [100.0, 0.0]],
        "segment_lengths_m": [150.0],  # 50% discrepancy
    }]
    errors2 = validate_route_geometries([{"stop_id": "S01", "x": 0.0, "y": 0.0}], routes_bad_sum)
    assert any("tolerance" in e for e in errors2)


def test_validator_catches_negative_capacities():
    """Validator catches negative vehicle or stop capacities."""
    vehicles = [{"vehicle_id": "B1", "capacity": -10, "seated": 5}]
    stops = [{"stop_id": "S01", "capacity_waiting": 0}]
    errors = validate_capacities(vehicles, stops)
    assert any("capacity" in e for e in errors)
    assert any("capacity_waiting" in e for e in errors)


def test_validator_catches_gps_teleports_and_non_monotonic():
    """Validator catches non-monotonic timestamps and speeds > 40 m/s."""
    # Non-monotonic
    df_non_mono = pd.DataFrame({
        "vehicle_id": ["B1", "B1"],
        "day": [1, 1],
        "t_sec": [100, 90],
        "lat": [12.9716, 12.9717],
        "lon": [77.5946, 77.5947],
    })
    errors_mono = validate_gps_pings(df_non_mono)
    assert any("non-monotonic" in e for e in errors_mono)

    # Teleport > 40 m/s: 1000m in 10s = 100 m/s
    df_teleport = pd.DataFrame({
        "vehicle_id": ["B1", "B1"],
        "day": [1, 1],
        "t_sec": [100, 110],
        "lat": [12.9716, 12.9816],  # approx ~1113 meters in 10s
        "lon": [77.5946, 77.5946],
    })
    errors_teleport = validate_gps_pings(df_teleport)
    assert any("teleport detected" in e for e in errors_teleport)


def test_validator_catches_apc_inconsistencies():
    """Validator catches load_after mismatch with boardings and alightings."""
    df_apc_bad = pd.DataFrame({
        "trip_id": ["T1", "T1"],
        "stop_id": ["S01", "S02"],
        "boardings": [10, 5],
        "alightings": [0, 2],
        "load_after": [10, 20],  # expected 10 + 5 - 2 = 13 != 20
    })
    errors = validate_apc_records(df_apc_bad)
    assert any("load_after mismatch" in e for e in errors)
