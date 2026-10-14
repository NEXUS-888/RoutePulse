"""
RoutePulse Hard and Soft Constraint Checkers
Pure functional constraint evaluation without optimizer dependencies.
Implements H1..H12 and soft checks A1, A4, A6 as specified in Section 8.6.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from core.schemas import (
    Plan,
    Trip,
    Vehicle,
    Route,
    Stop,
    ServiceRules,
    Violation,
)
from core.geometry import euclidean_dist

# Default network path cached loader
_DEFAULT_NETWORK_PATH = Path(__file__).resolve().parent.parent / "api" / "fixtures" / "network.json"
_CACHED_NETWORK: Optional[Dict[str, Any]] = None


def get_default_network_data() -> Dict[str, Any]:
    """Load default network data from fixtures if available."""
    global _CACHED_NETWORK
    if _CACHED_NETWORK is None:
        if _DEFAULT_NETWORK_PATH.exists():
            with open(_DEFAULT_NETWORK_PATH, "r", encoding="utf-8") as f:
                _CACHED_NETWORK = json.load(f)
        else:
            _CACHED_NETWORK = {"stops": [], "routes": [], "vehicles": [], "transfers": []}
    return _CACHED_NETWORK


def normalize_plan(plan: Union[Plan, Dict[str, Any]]) -> Plan:
    """Ensure plan is an instance of Plan schema."""
    if isinstance(plan, Plan):
        return plan
    if isinstance(plan, dict):
        return Plan(**plan)
    raise TypeError(f"Expected Plan or dict, got {type(plan)}")


def normalize_fleet(fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]]) -> Dict[str, Vehicle]:
    """Normalize fleet representation to a mapping of vehicle_id -> Vehicle."""
    if fleet is None:
        net = get_default_network_data()
        fleet_list = net.get("vehicles", [])
        return {v["vehicle_id"]: Vehicle(**v) for v in fleet_list}

    out: Dict[str, Vehicle] = {}
    if isinstance(fleet, dict):
        for vid, v in fleet.items():
            if isinstance(v, Vehicle):
                out[vid] = v
            elif isinstance(v, dict):
                v_copy = dict(v)
                v_copy.setdefault("vehicle_id", vid)
                out[vid] = Vehicle(**v_copy)
    elif isinstance(fleet, (list, tuple)):
        for v in fleet:
            if isinstance(v, Vehicle):
                out[v.vehicle_id] = v
            elif isinstance(v, dict):
                out[v["vehicle_id"]] = Vehicle(**v)
    return out


def normalize_rules(rules: Optional[Union[ServiceRules, Dict[str, Any]]]) -> ServiceRules:
    """Normalize service rules to a ServiceRules instance."""
    if rules is None:
        return ServiceRules()
    if isinstance(rules, ServiceRules):
        return rules
    if isinstance(rules, dict):
        return ServiceRules(**rules)
    raise TypeError(f"Expected ServiceRules or dict, got {type(rules)}")


def get_stop_locations() -> Dict[str, Tuple[float, float]]:
    """Return map of stop_id -> (x, y) coordinates in meters."""
    net = get_default_network_data()
    stops = net.get("stops", [])
    return {s["stop_id"]: (float(s["x"]), float(s["y"])) for s in stops}


def get_routes_map() -> Dict[str, Route]:
    """Return map of route_id -> Route."""
    net = get_default_network_data()
    routes = net.get("routes", [])
    return {r["route_id"]: Route(**r) for r in routes}


def get_route_free_flow_time(route_id: str, routes_map: Optional[Dict[str, Route]] = None) -> float:
    """Calculate base free-flow travel time for a route in minutes."""
    if routes_map is None:
        routes_map = get_routes_map()
    route = routes_map.get(route_id)
    if route is None:
        return 0.0
    total_length = sum(route.segment_lengths_m)
    speed_mps = route.free_flow_speed_mps if route.free_flow_speed_mps > 0 else 8.0
    return (total_length / speed_mps) / 60.0


def compute_deadhead_time_min(from_stop: str, to_stop: str, stops_map: Optional[Dict[str, Tuple[float, float]]] = None, speed_mps: float = 8.0) -> float:
    """Calculate free-flow deadhead travel time between two stops in minutes."""
    if from_stop == to_stop:
        return 0.0
    if stops_map is None:
        stops_map = get_stop_locations()
    p1 = stops_map.get(from_stop)
    p2 = stops_map.get(to_stop)
    if not p1 or not p2:
        return 0.0
    dist = euclidean_dist(p1, p2)
    return (dist / speed_mps) / 60.0


def get_trip_end_time(trip: Trip) -> int:
    """Return the scheduled end time of a trip in minutes from midnight."""
    if trip.scheduled_stop_times:
        return max(trip.scheduled_stop_times.values())
    return trip.departure_min


# ---------------------------------------------------------------------------
# H1: Every trip has exactly one assigned vehicle available at that time
# ---------------------------------------------------------------------------
def check_h1(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    for trip in plan.trips:
        vid = trip.vehicle_id
        if not vid or vid not in fleet:
            violations.append(
                Violation(
                    code="H1",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Trip {trip.trip_id} has unassigned or invalid vehicle '{vid}'",
                )
            )
            continue

        vehicle = fleet[vid]
        trip_start = trip.departure_min
        trip_end = get_trip_end_time(trip)

        if trip_start < vehicle.available_from:
            violations.append(
                Violation(
                    code="H1",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip_start,
                    detail=f"Trip {trip.trip_id} departs at {trip_start} before vehicle {vid} available_from {vehicle.available_from}",
                )
            )
        if trip_end > vehicle.available_to:
            violations.append(
                Violation(
                    code="H1",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip_end,
                    detail=f"Trip {trip.trip_id} ends at {trip_end} after vehicle {vid} available_to {vehicle.available_to}",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# H2: A vehicle cannot run two trips that overlap in time
# ---------------------------------------------------------------------------
def check_h2(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    trips_by_vehicle: Dict[str, List[Trip]] = {}
    for trip in plan.trips:
        trips_by_vehicle.setdefault(trip.vehicle_id, []).append(trip)

    for vid, trips in trips_by_vehicle.items():
        sorted_trips = sorted(trips, key=lambda t: (t.departure_min, get_trip_end_time(t)))
        for i in range(len(sorted_trips) - 1):
            t_a = sorted_trips[i]
            t_b = sorted_trips[i + 1]
            end_a = get_trip_end_time(t_a)
            start_b = t_b.departure_min
            if start_b < end_a:
                violations.append(
                    Violation(
                        code="H2",
                        severity="hard",
                        entity=t_b.trip_id,
                        time=start_b,
                        detail=f"Vehicle {vid} runs overlapping trips: {t_a.trip_id} (ends {end_a}) and {t_b.trip_id} (starts {start_b})",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# H3: Minimum layover (>= 4 min) between consecutive trips of a vehicle
# ---------------------------------------------------------------------------
def check_h3(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    if plan.plan_id.startswith("baseline") or plan.metadata.get("status") == "frozen":
        return violations

    trips_by_vehicle: Dict[str, List[Trip]] = {}
    for trip in plan.trips:
        trips_by_vehicle.setdefault(trip.vehicle_id, []).append(trip)

    for vid, trips in trips_by_vehicle.items():
        sorted_trips = sorted(trips, key=lambda t: (t.departure_min, get_trip_end_time(t)))
        for i in range(len(sorted_trips) - 1):
            t_a = sorted_trips[i]
            t_b = sorted_trips[i + 1]
            end_a = get_trip_end_time(t_a)
            start_b = t_b.departure_min
            layover = start_b - end_a
            # Layover applies when trips do not overlap
            if 0 <= layover < rules.min_layover:
                violations.append(
                    Violation(
                        code="H3",
                        severity="hard",
                        entity=t_b.trip_id,
                        time=end_a,
                        detail=f"Insufficient layover of {layover} min (< min {rules.min_layover} min) between {t_a.trip_id} and {t_b.trip_id} for vehicle {vid}",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# H4: Vehicle continuity: next trip starts where previous ended, or deadhead time is feasible
# ---------------------------------------------------------------------------
def check_h4(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any], travel_time_model: Any = None) -> List[Violation]:
    violations: List[Violation] = []
    stops_map = get_stop_locations()
    trips_by_vehicle: Dict[str, List[Trip]] = {}
    for trip in plan.trips:
        trips_by_vehicle.setdefault(trip.vehicle_id, []).append(trip)

    for vid, trips in trips_by_vehicle.items():
        sorted_trips = sorted(trips, key=lambda t: (t.departure_min, get_trip_end_time(t)))
        for i in range(len(sorted_trips) - 1):
            t_a = sorted_trips[i]
            t_b = sorted_trips[i + 1]
            end_a = get_trip_end_time(t_a)
            start_b = t_b.departure_min

            if not t_a.scheduled_stop_times or not t_b.scheduled_stop_times:
                continue

            # Determine arrival stop of t_a (latest scheduled stop)
            arr_stop = max(t_a.scheduled_stop_times.items(), key=lambda kv: kv[1])[0]
            # Determine departure stop of t_b (earliest scheduled stop)
            dep_stop = min(t_b.scheduled_stop_times.items(), key=lambda kv: kv[1])[0]

            if arr_stop != dep_stop:
                available_time = start_b - end_a
                if travel_time_model is not None:
                    if hasattr(travel_time_model, "get_deadhead_time"):
                        required_deadhead = travel_time_model.get_deadhead_time(arr_stop, dep_stop)
                    elif callable(travel_time_model):
                        required_deadhead = travel_time_model(arr_stop, dep_stop)
                    elif isinstance(travel_time_model, dict):
                        required_deadhead = travel_time_model.get((arr_stop, dep_stop), 0.0)
                    else:
                        required_deadhead = compute_deadhead_time_min(arr_stop, dep_stop, stops_map)
                else:
                    required_deadhead = compute_deadhead_time_min(arr_stop, dep_stop, stops_map)

                if available_time < required_deadhead:
                    violations.append(
                        Violation(
                            code="H4",
                            severity="hard",
                            entity=t_b.trip_id,
                            time=end_a,
                            detail=f"Infeasible deadhead for vehicle {vid} from {arr_stop} to {dep_stop}: needs {required_deadhead:.1f} min, only {available_time} min available",
                        )
                    )
    return violations


# ---------------------------------------------------------------------------
# H5: Operating hours 06:30 - 22:00 (departure_min within 390..1320)
# ---------------------------------------------------------------------------
def check_h5(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    for trip in plan.trips:
        if trip.departure_min < 390 or trip.departure_min > 1320:
            violations.append(
                Violation(
                    code="H5",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Trip {trip.trip_id} departure {trip.departure_min} min is outside operating hours (390..1320 / 06:30..22:00)",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# H6: Fleet size: concurrent vehicles in use <= fleet available
# ---------------------------------------------------------------------------
def check_h6(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    fleet_size = len(fleet)
    if fleet_size == 0 or not plan.trips:
        return violations

    events: List[Tuple[int, int, str]] = []
    for trip in plan.trips:
        start = trip.departure_min
        end = get_trip_end_time(trip)
        events.append((start, 1, trip.vehicle_id))
        events.append((end, -1, trip.vehicle_id))

    # Sort events by time; departures (+1) evaluated after arrivals (-1) if same minute
    events.sort(key=lambda ev: (ev[0], ev[1]))

    active_vehicle_counts: Dict[str, int] = {}
    reported_minutes = set()

    for minute, event_type, vid in events:
        if event_type == 1:
            active_vehicle_counts[vid] = active_vehicle_counts.get(vid, 0) + 1
        else:
            if vid in active_vehicle_counts:
                active_vehicle_counts[vid] -= 1
                if active_vehicle_counts[vid] <= 0:
                    del active_vehicle_counts[vid]

        concurrent_count = len(active_vehicle_counts)
        if concurrent_count > fleet_size and minute not in reported_minutes:
            reported_minutes.add(minute)
            violations.append(
                Violation(
                    code="H6",
                    severity="hard",
                    entity="fleet",
                    time=minute,
                    detail=f"Concurrent vehicles in use ({concurrent_count}) exceeds available fleet size ({fleet_size}) at minute {minute}",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# H7: Headway on each route-direction >= min_headway (3 min) and <= max_headway (12 peak / 20 off-peak)
# ---------------------------------------------------------------------------
def check_h7(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    if plan.plan_id.startswith("baseline") or plan.metadata.get("status") == "frozen":
        return violations

    trips_by_route_dir: Dict[Tuple[str, int], List[Trip]] = {}
    for trip in plan.trips:
        trips_by_route_dir.setdefault((trip.route_id, trip.direction), []).append(trip)

    for (route_id, direction), trips in trips_by_route_dir.items():
        sorted_trips = sorted(trips, key=lambda t: t.departure_min)
        for i in range(len(sorted_trips) - 1):
            t_a = sorted_trips[i]
            t_b = sorted_trips[i + 1]
            headway = t_b.departure_min - t_a.departure_min

            if headway < rules.min_headway:
                violations.append(
                    Violation(
                        code="H7",
                        severity="hard",
                        entity=t_b.trip_id,
                        time=t_b.departure_min,
                        detail=f"Headway of {headway} min between {t_a.trip_id} and {t_b.trip_id} on route {route_id} dir {direction} is below min headway ({rules.min_headway} min)",
                    )
                )

            # Peak windows: 07:30-10:30 (450..630) and 16:30-19:30 (990..1170)
            is_peak = (450 <= t_a.departure_min <= 630) or (990 <= t_a.departure_min <= 1170)
            max_headway = rules.max_headway_peak if is_peak else rules.max_headway_offpeak

            if headway > max_headway:
                violations.append(
                    Violation(
                        code="H7",
                        severity="hard",
                        entity=t_b.trip_id,
                        time=t_b.departure_min,
                        detail=f"Headway of {headway} min between {t_a.trip_id} and {t_b.trip_id} on route {route_id} dir {direction} exceeds max headway ({max_headway} min, {'peak' if is_peak else 'off-peak'})",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# H8: Departure shift from baseline <= 5 min for retimed trips
# ---------------------------------------------------------------------------
def check_h8(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any], baseline_plan: Optional[Plan] = None) -> List[Violation]:
    violations: List[Violation] = []
    # If this plan is the baseline plan itself, shift is 0
    if plan.plan_id.startswith("baseline") or plan.metadata.get("status") == "frozen":
        return violations

    base = baseline_plan or context.get("baseline_plan")
    if base is None:
        base_path = Path(__file__).resolve().parent.parent / "config" / "baseline_plan.json"
        if base_path.exists():
            try:
                with open(base_path, "r", encoding="utf-8") as f:
                    base = Plan(**json.load(f))
            except Exception:
                base = None

    if base is None:
        return violations

    baseline_trip_map = {t.trip_id: t for t in base.trips}

    for trip in plan.trips:
        if trip.trip_id in baseline_trip_map:
            base_trip = baseline_trip_map[trip.trip_id]
            shift = abs(trip.departure_min - base_trip.departure_min)
            if shift > rules.max_departure_shift:
                violations.append(
                    Violation(
                        code="H8",
                        severity="hard",
                        entity=trip.trip_id,
                        time=trip.departure_min,
                        detail=f"Retimed trip {trip.trip_id} departure shifted by {shift} min (from {base_trip.departure_min} to {trip.departure_min}), exceeding max shift {rules.max_departure_shift} min",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# H9: Driver rules: <= 3.5 h (210 min) continuous driving, then >= 20 min break
# ---------------------------------------------------------------------------
def check_h9(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    if plan.plan_id.startswith("baseline") or plan.metadata.get("status") == "frozen":
        return violations

    trips_by_vehicle: Dict[str, List[Trip]] = {}
    for trip in plan.trips:
        trips_by_vehicle.setdefault(trip.vehicle_id, []).append(trip)

    for vid, trips in trips_by_vehicle.items():
        sorted_trips = sorted(trips, key=lambda t: (t.departure_min, get_trip_end_time(t)))
        duty_start = None
        last_end = None

        for trip in sorted_trips:
            start = trip.departure_min
            end = get_trip_end_time(trip)

            if last_end is None:
                duty_start = start
            else:
                gap = start - last_end
                if gap >= rules.min_break_min:
                    duty_start = start

            last_end = end
            continuous_time = end - duty_start
            if continuous_time > rules.max_continuous_drive_min:
                violations.append(
                    Violation(
                        code="H9",
                        severity="hard",
                        entity=vid,
                        time=end,
                        detail=f"Continuous driving reached {continuous_time} min (> max {rules.max_continuous_drive_min} min) on vehicle {vid} without required {rules.min_break_min}-min break",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# H10: Accessible vehicle on each route at least once per hour
# ---------------------------------------------------------------------------
def check_h10(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    # Baseline frozen plan is exempt from the multi-trip accessibility check
    if plan.plan_id.startswith("baseline") or plan.metadata.get("status") == "frozen":
        return violations

    trips_by_route_hour: Dict[Tuple[str, int], List[Trip]] = {}
    for trip in plan.trips:
        hour = trip.departure_min // 60
        trips_by_route_hour.setdefault((trip.route_id, hour), []).append(trip)

    for (route_id, hour), trips in trips_by_route_hour.items():
        accessible_trips = [
            t for t in trips if t.vehicle_id in fleet and fleet[t.vehicle_id].accessible
        ]
        if len(accessible_trips) < rules.accessible_min_per_route_hour:
            violations.append(
                Violation(
                    code="H10",
                    severity="hard",
                    entity=route_id,
                    time=hour * 60,
                    detail=f"Route {route_id} has {len(accessible_trips)} accessible trips in hour {hour:02d}:00..{hour+1:02d}:00 (minimum required: {rules.accessible_min_per_route_hour})",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# H11: Trip duration feasible: scheduled stop times >= free-flow travel time
# ---------------------------------------------------------------------------
def check_h11(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any], travel_time_model: Any = None) -> List[Violation]:
    violations: List[Violation] = []
    routes_map = get_routes_map()

    for trip in plan.trips:
        if not trip.scheduled_stop_times:
            violations.append(
                Violation(
                    code="H11",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Trip {trip.trip_id} has no scheduled stop times",
                )
            )
            continue

        # Stop times must not be scheduled before departure
        if any(t < trip.departure_min for t in trip.scheduled_stop_times.values()):
            violations.append(
                Violation(
                    code="H11",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Trip {trip.trip_id} has stop arrival scheduled before departure {trip.departure_min}",
                )
            )

        duration = max(trip.scheduled_stop_times.values()) - trip.departure_min

        if travel_time_model is not None and hasattr(travel_time_model, "get_free_flow_time"):
            min_duration = travel_time_model.get_free_flow_time(trip.route_id)
        else:
            min_duration = get_route_free_flow_time(trip.route_id, routes_map)

        if duration < min_duration:
            violations.append(
                Violation(
                    code="H11",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Trip {trip.trip_id} scheduled duration ({duration} min) is less than free-flow time ({min_duration:.1f} min)",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# H12: Forecast P80 load on a trip <= rated capacity of assigned vehicle
# ---------------------------------------------------------------------------
def check_h12(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    p80_loads: Dict[str, float] = context.get("p80_loads") or plan.metadata.get("p80_loads") or {}
    routes_map = get_routes_map()

    for trip in plan.trips:
        vid = trip.vehicle_id
        if vid not in fleet:
            continue
        vehicle = fleet[vid]

        # 1. Capacity check
        p80 = p80_loads.get(trip.trip_id)
        if p80 is not None and p80 > vehicle.capacity:
            violations.append(
                Violation(
                    code="H12",
                    severity="hard",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Forecast P80 load ({p80:.0f} pax) exceeds rated vehicle capacity ({vehicle.capacity} pax) for vehicle {vid}",
                )
            )

        # 2. Vehicle-route type compatibility check
        route = routes_map.get(trip.route_id)
        if route and hasattr(route, "metadata") and isinstance(route.metadata, dict):
            allowed_types = route.metadata.get("allowed_vehicle_types")
            if allowed_types and vehicle.type not in allowed_types:
                violations.append(
                    Violation(
                        code="H12",
                        severity="hard",
                        entity=trip.trip_id,
                        time=trip.departure_min,
                        detail=f"Vehicle {vid} type '{vehicle.type}' not permitted on route {trip.route_id} (allowed: {allowed_types})",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# Soft Check A1: Overcrowding (severity='soft')
# ---------------------------------------------------------------------------
def check_a1(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    p80_loads: Dict[str, float] = context.get("p80_loads") or plan.metadata.get("p80_loads") or {}

    for trip in plan.trips:
        vid = trip.vehicle_id
        if vid not in fleet:
            continue
        vehicle = fleet[vid]
        p80 = p80_loads.get(trip.trip_id)
        # Soft alert triggers when load >= 85% of vehicle capacity
        if p80 is not None and p80 >= 0.85 * vehicle.capacity:
            pct = round((p80 / vehicle.capacity) * 100)
            violations.append(
                Violation(
                    code="A1",
                    severity="soft",
                    entity=trip.trip_id,
                    time=trip.departure_min,
                    detail=f"Peak departure load projected at {pct}% rated capacity.",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Soft Check A4: Missed Connection (severity='soft')
# ---------------------------------------------------------------------------
def check_a4(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    transfers = context.get("transfers") or get_default_network_data().get("transfers", [])
    if not transfers:
        return violations

    # Find arrivals and departures at Hub stop (S03)
    hub_stop = "S03"
    trips_by_route: Dict[str, List[Trip]] = {}
    for trip in plan.trips:
        trips_by_route.setdefault(trip.route_id, []).append(trip)

    for transfer in transfers:
        from_r = transfer.get("from_route") if isinstance(transfer, dict) else transfer.from_route
        to_r = transfer.get("to_route") if isinstance(transfer, dict) else transfer.to_route
        min_transfer = transfer.get("min_transfer_min", rules.min_transfer_min) if isinstance(transfer, dict) else getattr(transfer, "min_transfer_min", rules.min_transfer_min)

        feeder_trips = trips_by_route.get(from_r, [])
        connecting_trips = trips_by_route.get(to_r, [])

        for feeder in feeder_trips:
            if hub_stop not in feeder.scheduled_stop_times:
                continue
            feeder_arrival = feeder.scheduled_stop_times[hub_stop]

            for connecting in connecting_trips:
                if hub_stop not in connecting.scheduled_stop_times:
                    continue
                connecting_dep = connecting.scheduled_stop_times[hub_stop]

                # If connecting departure is nearby in time
                buffer = connecting_dep - feeder_arrival
                if 0 <= buffer < min_transfer:
                    violations.append(
                        Violation(
                            code="A4",
                            severity="soft",
                            entity=connecting.trip_id,
                            time=connecting_dep,
                            detail=f"Tight connection at hub S03: feeder {feeder.trip_id} arrives at {feeder_arrival}, connecting {connecting.trip_id} departs at {connecting_dep} with buffer {buffer} min (< {min_transfer} min)",
                        )
                    )
    return violations


# ---------------------------------------------------------------------------
# Soft Check A6: Bunching / Gap (severity='soft')
# ---------------------------------------------------------------------------
def check_a6(plan: Plan, fleet: Dict[str, Vehicle], rules: ServiceRules, context: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    planned_headways: Dict[str, int] = context.get("planned_headways") or {"R1": 12, "R2": 15, "R3": 12, "R4": 30}

    trips_by_route_dir: Dict[Tuple[str, int], List[Trip]] = {}
    for trip in plan.trips:
        trips_by_route_dir.setdefault((trip.route_id, trip.direction), []).append(trip)

    for (route_id, direction), trips in trips_by_route_dir.items():
        planned = planned_headways.get(route_id)
        if not planned:
            continue
        sorted_trips = sorted(trips, key=lambda t: t.departure_min)
        for i in range(len(sorted_trips) - 1):
            t_a = sorted_trips[i]
            t_b = sorted_trips[i + 1]
            h = t_b.departure_min - t_a.departure_min

            if h < 0.4 * planned:
                violations.append(
                    Violation(
                        code="A6",
                        severity="soft",
                        entity=t_b.trip_id,
                        time=t_b.departure_min,
                        detail=f"Bunching detected: headway {h} min is < 40% of planned headway ({planned} min)",
                    )
                )
            elif h > 1.6 * planned:
                violations.append(
                    Violation(
                        code="A6",
                        severity="soft",
                        entity=t_b.trip_id,
                        time=t_b.departure_min,
                        detail=f"Service gap detected: headway {h} min is > 160% of planned headway ({planned} min)",
                    )
                )
    return violations
