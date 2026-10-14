"""
Dataset Quality Validation for RoutePulse.
Enforces all Section 6 dataset quality rules from docs/ARCHITECTURE.md:
  1. Referenced stop IDs exist.
  2. Route polylines pass within 25 m of their stops.
  3. Segment lengths sum to polyline length ±1%.
  4. Vehicle and stop capacities are positive.
  5. GPS timestamps are strictly monotonic per vehicle.
  6. No GPS ping teleports above 40 m/s.
  7. APC load_after is consistent with boardings and alightings.
"""
from __future__ import annotations
import csv
import json
import math
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Any, Optional
import pandas as pd

from core.geometry import polyline_length, project_point_to_polyline, latlon_to_xy

from core.io import load_json, load_parquet


class DatasetValidationError(Exception):
    """Raised when one or more dataset quality rules fail."""
    pass


def validate_stop_ids(
    stops_data: list[dict[str, Any]],
    routes_data: list[dict[str, Any]],
    plan_data: Optional[dict[str, Any]] = None,
    events_path: Optional[Path | str] = None,
    demand_df: Optional[pd.DataFrame] = None,
    apc_df: Optional[pd.DataFrame] = None,
) -> list[str]:
    errors: list[str] = []
    valid_stop_ids = {s["stop_id"] for s in stops_data}

    # 1. Routes
    for r in routes_data:
        for sid in r.get("stop_sequence", []):
            if sid not in valid_stop_ids:
                errors.append(f"Route {r.get('route_id')} references non-existent stop_id '{sid}'")

    # 2. Baseline Plan
    if plan_data and "trips" in plan_data:
        for t in plan_data["trips"]:
            for sid in t.get("scheduled_stop_times", {}).keys():
                if sid not in valid_stop_ids:
                    errors.append(f"Trip {t.get('trip_id')} references non-existent stop_id '{sid}'")

    # 3. Events
    if events_path and Path(events_path).exists():
        with open(events_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                venue_id = row.get("venue_stop_id")
                if venue_id and venue_id not in valid_stop_ids:
                    errors.append(f"Event {row.get('event_id')} references non-existent venue_stop_id '{venue_id}'")

    # 4. Demand
    if demand_df is not None and not demand_df.empty:
        if "stop_id" in demand_df.columns:
            invalid_stops = set(demand_df["stop_id"].unique()) - valid_stop_ids
            for sid in invalid_stops:
                errors.append(f"Demand data contains invalid stop_id '{sid}'")

    # 5. APC
    if apc_df is not None and not apc_df.empty:
        if "stop_id" in apc_df.columns:
            invalid_stops = set(apc_df["stop_id"].unique()) - valid_stop_ids
            for sid in invalid_stops:
                errors.append(f"APC data contains invalid stop_id '{sid}'")

    return errors


def validate_route_geometries(
    stops_data: list[dict[str, Any]],
    routes_data: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    stop_coords = {s["stop_id"]: (s["x"], s["y"]) for s in stops_data}

    for r in routes_data:
        rid = r.get("route_id", "unknown")
        polyline = r.get("polyline", [])
        if len(polyline) < 2:
            errors.append(f"Route {rid} polyline has fewer than 2 points")
            continue

        # Rule 2: Polyline passes within 25m of each stop
        for sid in r.get("stop_sequence", []):
            if sid in stop_coords:
                stop_pt = stop_coords[sid]
                _, dist = project_point_to_polyline(stop_pt, polyline)
                if dist > 25.0:
                    errors.append(
                        f"Route {rid} polyline is {dist:.1f}m away from stop {sid} (exceeds 25m limit)"
                    )

        # Rule 3: Segment lengths sum to polyline length ±1%
        seg_lengths = r.get("segment_lengths_m", [])
        sum_segs = sum(seg_lengths)
        true_len = polyline_length(polyline)
        if true_len > 0:
            diff_ratio = abs(sum_segs - true_len) / true_len
            if diff_ratio > 0.01:
                errors.append(
                    f"Route {rid} segment lengths sum ({sum_segs:.1f}m) differs from polyline length "
                    f"({true_len:.1f}m) by {diff_ratio*100:.2f}% (exceeds ±1% tolerance)"
                )

    return errors


def validate_capacities(
    vehicles_data: list[dict[str, Any]],
    stops_data: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []

    # Rule 4: Capacities positive
    for v in vehicles_data:
        vid = v.get("vehicle_id", "unknown")
        cap = v.get("capacity", 0)
        seated = v.get("seated", 0)
        if cap <= 0:
            errors.append(f"Vehicle {vid} has non-positive capacity: {cap}")
        if seated <= 0:
            errors.append(f"Vehicle {vid} has non-positive seated count: {seated}")
        if seated > cap:
            errors.append(f"Vehicle {vid} has seated ({seated}) > capacity ({cap})")

    for s in stops_data:
        sid = s.get("stop_id", "unknown")
        cap_w = s.get("capacity_waiting")
        if cap_w is not None and cap_w <= 0:
            errors.append(f"Stop {sid} has non-positive capacity_waiting: {cap_w}")

    return errors


def validate_gps_pings(gps_df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if gps_df.empty:
        return errors

    # Check required columns
    required_cols = {"vehicle_id", "t_sec", "lat", "lon"}
    if not required_cols.issubset(gps_df.columns):
        errors.append(f"GPS dataframe missing required columns: {required_cols - set(gps_df.columns)}")
        return errors

    # Degrees to meters constants
    origin_lat = 12.9716
    meters_per_deg_lat = 111320.0
    meters_per_deg_lon = 111320.0 * math.cos(math.radians(origin_lat))

    # Group by vehicle_id and day (if day column present)
    group_cols = ["vehicle_id", "day"] if "day" in gps_df.columns else ["vehicle_id"]

    for key, group in gps_df.groupby(group_cols):
        t_vals = group["t_sec"].to_numpy(dtype=float)
        lats = group["lat"].to_numpy(dtype=float)
        lons = group["lon"].to_numpy(dtype=float)

        if len(t_vals) < 2:
            continue

        # Rule 5: Timestamps monotonic per vehicle
        dt = t_vals[1:] - t_vals[:-1]
        if (dt <= 0).any():
            errors.append(f"Vehicle group {key} has non-monotonic or duplicate timestamps")

        # Rule 6: No ping teleports above 40 m/s
        valid_dt = dt > 0
        if valid_dt.any():
            dx = (lons[1:] - lons[:-1]) * meters_per_deg_lon
            dy = (lats[1:] - lats[:-1]) * meters_per_deg_lat
            dist = (dx * dx + dy * dy) ** 0.5
            speeds = dist[valid_dt] / dt[valid_dt]
            max_speed = float(speeds.max()) if len(speeds) > 0 else 0.0
            if max_speed > 40.0:
                errors.append(
                    f"Vehicle group {key} teleport detected: max speed {max_speed:.1f} m/s (limit 40 m/s)"
                )

    return errors



def validate_apc_records(apc_df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if apc_df.empty:
        return errors

    required_cols = {"trip_id", "stop_id", "boardings", "alightings", "load_after"}
    if not required_cols.issubset(apc_df.columns):
        errors.append(f"APC dataframe missing required columns: {required_cols - set(apc_df.columns)}")
        return errors

    # Rule 7: APC load_after consistent with boardings and alightings
    for trip_id, group in apc_df.groupby("trip_id"):
        expected_load = 0
        for idx, row in group.iterrows():
            b = row["boardings"]
            a = row["alightings"]
            load = row["load_after"]

            if b < 0 or a < 0:
                errors.append(f"Trip {trip_id} at stop {row['stop_id']} has negative boarding/alighting: b={b}, a={a}")
                break

            expected_load += (b - a)
            if expected_load < 0:
                errors.append(
                    f"Trip {trip_id} at stop {row['stop_id']} has negative expected load: {expected_load}"
                )
                break

            if load != expected_load:
                errors.append(
                    f"Trip {trip_id} at stop {row['stop_id']} load_after mismatch: "
                    f"recorded={load}, expected={expected_load} (b={b}, a={a})"
                )
                break

    return errors


def validate_dataset(data_dir: Path | str = "data") -> list[str]:
    """
    Validates all dataset quality rules across files in data_dir.
    Returns list of error messages (empty if valid).
    """
    dpath = Path(data_dir)
    errors: list[str] = []

    # 1. Network
    net_path = dpath / "network.json"
    if not net_path.exists():
        errors.append(f"Missing {net_path}")
        return errors

    net_data = load_json(net_path)
    stops = net_data.get("stops", [])
    routes = net_data.get("routes", [])
    vehicles = net_data.get("vehicles", [])

    # 2. Baseline Plan
    plan_path = dpath / "baseline_plan.json"
    plan_data = load_json(plan_path) if plan_path.exists() else None

    # 3. Events
    events_path = dpath / "events.csv"

    # 4. Parquet data
    demand_path = dpath / "demand_obs.parquet"
    demand_df = load_parquet(demand_path) if demand_path.exists() else None

    gps_path = dpath / "gps_pings.parquet"
    gps_df = load_parquet(gps_path) if gps_path.exists() else None

    apc_path = dpath / "apc_records.parquet"
    apc_df = load_parquet(apc_path) if apc_path.exists() else None

    # Run checks
    errors.extend(validate_stop_ids(stops, routes, plan_data, events_path, demand_df, apc_df))
    errors.extend(validate_route_geometries(stops, routes))
    errors.extend(validate_capacities(vehicles, stops))

    if gps_df is not None:
        errors.extend(validate_gps_pings(gps_df))

    if apc_df is not None:
        errors.extend(validate_apc_records(apc_df))

    return errors


def main() -> None:
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    print(f"Validating dataset in '{data_dir}'...")
    errors = validate_dataset(data_dir)
    if errors:
        print(f"\nFAILED: Found {len(errors)} dataset quality violation(s):")
        for e in errors:
            print(f"  [X] {e}")
        sys.exit(1)
    else:
        print("\nPASSED: All Section 6 dataset quality rules verified successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
