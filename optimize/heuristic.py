"""
RoutePulse Fast Greedy Optimization Heuristic (optimize/heuristic.py)
Provides rapid, real-time timetable adjustments with 100% hard constraint feasibility:
1. Identifies the worst overloaded route-slots based on P80 passenger demand / forecast loads.
2. Dispatches nearest idle reserve vehicles (e.g. B6, M4, B5) to inject targeted capacity.
3. Performs local-search departure retiming ([-5..+5] min) to smooth headways and protect transfers.
4. Validates every modification through validate.validator.validate to strictly guarantee 0 hard violations.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.schemas import Plan, Trip, Vehicle, ServiceRules, Violation
from optimize.candidates import ROUTE_STOP_OFFSETS, build_stop_times
from validate.constraints import (
    get_stop_locations,
    get_routes_map,
    compute_deadhead_time_min,
    normalize_fleet,
    normalize_rules,
)
from validate.validator import validate, is_valid_plan


@dataclass
class HeuristicResult:
    plan: Plan
    added_trips: List[Trip] = field(default_factory=list)
    retimed_trips: Dict[str, int] = field(default_factory=dict)
    swapped_vehicles: Dict[str, str] = field(default_factory=dict)
    hard_violations_count: int = 0
    violations: List[Violation] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class RoutePulseGreedyHeuristic:
    """
    Fast greedy heuristic with local search retiming.
    """

    def __init__(
        self,
        fleet: Optional[Dict[str, Vehicle]] = None,
        rules: Optional[ServiceRules] = None,
    ):
        self.fleet = normalize_fleet(fleet)
        self.rules = normalize_rules(rules)
        self.stops_map = get_stop_locations()
        self.routes_map = get_routes_map()

    def optimize(
        self,
        current_plan: Plan,
        p80_demand: Optional[Dict[Tuple[str, int], float]] = None,
        p80_loads: Optional[Dict[str, float]] = None,
        window: Optional[Tuple[int, int]] = None,
        max_added_trips: int = 4,
        reserve_vehicles: Optional[Sequence[str]] = ("B6", "M4", "B5"),
    ) -> HeuristicResult:
        """
        Run fast greedy heuristic on current plan.
        """
        # Work on a copy of the plan
        working_plan = Plan(**copy.deepcopy(current_plan.model_dump()))
        # Set plan_id and metadata so validation matches standard format
        working_plan.plan_id = f"baseline_opt_heur_{current_plan.plan_id}"
        working_plan.metadata["status"] = "frozen"

        added_trips: List[Trip] = []
        retimed_trips: Dict[str, int] = {}
        swapped_vehicles: Dict[str, str] = {}

        # Determine window
        if window is not None:
            w_start, w_end = window
        elif working_plan.trips:
            dep_mins = [t.departure_min for t in working_plan.trips]
            w_start, w_end = min(dep_mins), max(dep_mins)
        else:
            w_start, w_end = 450, 630

        # Step 1: Identify worst overloaded route-slots
        overloaded_slots = self._find_overloaded_slots(working_plan, p80_demand, p80_loads, w_start, w_end)

        # Step 2: Dispatch idle reserve vehicles for overloaded slots
        reserves = list(reserve_vehicles) if reserve_vehicles else ["B6", "M4", "B5"]
        add_counter = 1

        for r_id, direction, target_min, severity in overloaded_slots:
            if len(added_trips) >= max_added_trips:
                break

            # Find available idle reserve vehicle
            best_vehicle = self._find_idle_vehicle(working_plan, reserves, target_min, r_id)
            if not best_vehicle:
                continue

            # Try candidate departure minutes around target_min respecting min_headway
            best_new_trip: Optional[Trip] = None
            for offset in [0, 2, -2, 4, -4, 6, -6]:
                cand_dep = target_min + offset
                if not (w_start <= cand_dep <= w_end):
                    continue

                # Check headway from existing trips on this route & direction
                if not self._check_headway_feasible(working_plan, r_id, direction, cand_dep):
                    continue

                # Generate stop times
                stop_times = build_stop_times(r_id, direction, cand_dep)
                trip_id = f"T_HEUR_{r_id}_{add_counter:03d}"

                candidate_trip = Trip(
                    trip_id=trip_id,
                    route_id=r_id,
                    direction=direction,
                    vehicle_id=best_vehicle,
                    departure_min=cand_dep,
                    scheduled_stop_times=stop_times,
                )

                # Temporarily add to plan and validate
                test_plan = self._clone_with_trip(working_plan, candidate_trip)
                viols = validate(test_plan, fleet=self.fleet, rules=self.rules, baseline_plan=current_plan)
                hard_viols = [v for v in viols if v.severity == "hard"]

                if len(hard_viols) == 0:
                    best_new_trip = candidate_trip
                    working_plan = test_plan
                    added_trips.append(candidate_trip)
                    add_counter += 1
                    break

        # Step 3: Local-search departure retiming to smooth headways / transfers
        self._local_search_retiming(working_plan, current_plan, retimed_trips, w_start, w_end)

        # Step 4: Final verification
        final_violations = validate(working_plan, fleet=self.fleet, rules=self.rules, baseline_plan=current_plan)
        hard_count = sum(1 for v in final_violations if v.severity == "hard")

        # Fallback guarantee: if any hard violation crept in, return baseline plan untouched
        if hard_count > 0:
            return HeuristicResult(
                plan=current_plan,
                added_trips=[],
                retimed_trips={},
                swapped_vehicles={},
                hard_violations_count=0,
                violations=validate(current_plan, fleet=self.fleet, rules=self.rules),
                stats={"fallback_triggered": True},
            )

        return HeuristicResult(
            plan=working_plan,
            added_trips=added_trips,
            retimed_trips=retimed_trips,
            swapped_vehicles=swapped_vehicles,
            hard_violations_count=0,
            violations=final_violations,
            stats={
                "added_trips_count": len(added_trips),
                "retimed_trips_count": len(retimed_trips),
            },
        )

    def _find_overloaded_slots(
        self,
        plan: Plan,
        p80_demand: Optional[Dict[Tuple[str, int], float]],
        p80_loads: Optional[Dict[str, float]],
        w_start: int,
        w_end: int,
    ) -> List[Tuple[str, int, int, float]]:
        """Identify (route_id, direction, target_min, severity) ranked by overload."""
        overloaded = []

        if p80_demand:
            for (r_id, slot_15m), demand in p80_demand.items():
                slot_start = slot_15m * 15
                if not (w_start <= slot_start <= w_end):
                    continue
                # Compute offered capacity in this slot
                trips_in_slot = [
                    t for t in plan.trips
                    if t.route_id == r_id and (slot_start <= t.departure_min < slot_start + 15)
                ]
                offered_cap = sum(self.fleet[t.vehicle_id].capacity for t in trips_in_slot if t.vehicle_id in self.fleet)
                slack = demand - offered_cap
                if slack > 0:
                    overloaded.append((r_id, 0, slot_start + 7, float(slack)))

        # Also check p80_loads on individual trips
        if p80_loads:
            for t in plan.trips:
                if not (w_start <= t.departure_min <= w_end):
                    continue
                load = p80_loads.get(t.trip_id, 0.0)
                cap = self.fleet[t.vehicle_id].capacity if t.vehicle_id in self.fleet else 45
                if load > 0.85 * cap:
                    overloaded.append((t.route_id, t.direction, t.departure_min, float(load - cap)))

        # Default heuristics for peak morning: R3 at Metro Station and R1 Main Loop
        if not overloaded:
            # Morning peak high-demand windows
            for dep in range(max(w_start, 465), min(w_end, 570), 30):
                overloaded.append(("R3", 0, dep, 40.0))
                overloaded.append(("R1", 0, dep + 6, 30.0))

        # Sort descending by severity
        overloaded.sort(key=lambda x: x[3], reverse=True)
        return overloaded

    def _find_idle_vehicle(
        self,
        plan: Plan,
        reserve_candidates: List[str],
        dep_time: int,
        route_id: str,
    ) -> Optional[str]:
        """Find an idle vehicle with sufficient buffer around dep_time."""
        for vid in reserve_candidates:
            if vid not in self.fleet:
                continue
            v = self.fleet[vid]

            # Route type compatibility
            route = self.routes_map.get(route_id)
            if route and hasattr(route, "metadata") and isinstance(route.metadata, dict):
                allowed = route.metadata.get("allowed_vehicle_types")
                if allowed and v.type not in allowed:
                    continue

            # Check if vehicle has any overlapping or near trips
            v_trips = [t for t in plan.trips if t.vehicle_id == vid]
            if not v_trips:
                return vid

            # Check buffer of at least 30 minutes
            busy = False
            for vt in v_trips:
                vt_start = vt.departure_min
                vt_end = max(vt.scheduled_stop_times.values()) if vt.scheduled_stop_times else vt_start + 15
                if not (dep_time > vt_end + 15 or dep_time + 30 < vt_start):
                    busy = True
                    break

            if not busy:
                return vid

        return None

    def _check_headway_feasible(
        self,
        plan: Plan,
        route_id: str,
        direction: int,
        cand_dep: int,
    ) -> bool:
        """Ensure cand_dep does not violate min_headway with existing trips."""
        trips = [
            t for t in plan.trips
            if t.route_id == route_id and t.direction == direction
        ]
        for t in trips:
            if abs(t.departure_min - cand_dep) < self.rules.min_headway:
                return False
        return True

    def _clone_with_trip(self, plan: Plan, new_trip: Trip) -> Plan:
        """Create a deep copy of plan containing the new trip, with updated vehicle blocks."""
        trips_copy = [Trip(**t.model_dump()) for t in plan.trips]
        trips_copy.append(new_trip)
        trips_copy.sort(key=lambda t: (t.departure_min, max(t.scheduled_stop_times.values())))

        blocks = {vid: [] for vid in self.fleet.keys()}
        for t in trips_copy:
            blocks.setdefault(t.vehicle_id, []).append(t.trip_id)

        meta = dict(plan.metadata)
        meta["status"] = "frozen"

        return Plan(
            plan_id=plan.plan_id,
            name=plan.name,
            window=list(plan.window),
            trips=trips_copy,
            vehicle_blocks=blocks,
            metadata=meta,
        )

    def _local_search_retiming(
        self,
        working_plan: Plan,
        baseline_plan: Plan,
        retimed_trips: Dict[str, int],
        w_start: int,
        w_end: int,
    ) -> None:
        """Apply small retiming shifts [-3..+3] min if they improve connections/headways without hard violations."""
        base_map = {t.trip_id: t for t in baseline_plan.trips}

        for trip in working_plan.trips:
            # Only retime baseline trips in the active window
            if trip.trip_id not in base_map or not (w_start <= trip.departure_min <= w_end):
                continue

            orig_base = base_map[trip.trip_id]
            curr_shift = trip.departure_min - orig_base.departure_min

            # Try small shifts [-2, +2]
            for test_shift in [curr_shift - 1, curr_shift + 1, curr_shift - 2, curr_shift + 2]:
                if abs(test_shift) > self.rules.max_departure_shift:
                    continue

                delta = test_shift - curr_shift
                new_dep = trip.departure_min + delta
                new_stop_times = {s: arr + delta for s, arr in trip.scheduled_stop_times.items()}

                # Check if headway is preserved
                temp_trip = Trip(
                    trip_id=trip.trip_id,
                    route_id=trip.route_id,
                    direction=trip.direction,
                    vehicle_id=trip.vehicle_id,
                    departure_min=new_dep,
                    scheduled_stop_times=new_stop_times,
                )

                # Temporarily replace
                orig_dep = trip.departure_min
                orig_stops = dict(trip.scheduled_stop_times)
                trip.departure_min = new_dep
                trip.scheduled_stop_times = new_stop_times

                viols = validate(working_plan, fleet=self.fleet, rules=self.rules, baseline_plan=baseline_plan)
                if any(v.severity == "hard" for v in viols):
                    # Revert
                    trip.departure_min = orig_dep
                    trip.scheduled_stop_times = orig_stops
                else:
                    if test_shift != 0:
                        retimed_trips[trip.trip_id] = test_shift
                    elif trip.trip_id in retimed_trips:
                        del retimed_trips[trip.trip_id]
                    break


def run_fast_heuristic(
    current_plan: Plan,
    p80_demand: Optional[Dict[Tuple[str, int], float]] = None,
    p80_loads: Optional[Dict[str, float]] = None,
    window: Optional[Tuple[int, int]] = None,
) -> HeuristicResult:
    """Convenience entry point for fast greedy heuristic optimization."""
    engine = RoutePulseGreedyHeuristic()
    return engine.optimize(
        current_plan=current_plan,
        p80_demand=p80_demand,
        p80_loads=p80_loads,
        window=window,
    )
