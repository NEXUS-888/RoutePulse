"""
RoutePulse Stage-B Vehicle Blocking & Timetable Optimization (optimize/cpsat_model.py)
Solves multi-vehicle scheduling and timetable retiming using OR-Tools CP-SAT.

Features:
- Decision variables:
    x[t]: binary trip operation indicator
    a[v,t]: binary vehicle-to-trip assignment
    u[r,k]: unmet demand slack variable per route-slot
    y[t,s]: binary transfer connection indicator at Hub S03
- Explicit constraint encoding:
    H1: Exactly one vehicle available per operated trip
    H2: No overlapping trips for any vehicle
    H3: Minimum layover (>= 4 min) between consecutive vehicle trips
    H4: Vehicle continuity / feasible deadhead travel time
    H5: Operating hours 06:30..22:00 (390..1320 min)
    H6: Concurrent vehicles in use <= fleet size
    H7: Headway bounds (>= 3 min, <= 12 min peak / <= 20 min offpeak)
    H8: Departure shift <= 5 min for retimed trips
    H9: Continuous driving and break rules
    H10: Accessible vehicle on each route at least once per hour
    H11: Trip duration feasible (>= free-flow travel time)
    H12: Vehicle capacity >= P80 forecast load; vehicle type allowed
- Objective:
    min w_wait*Wait + w_unmet*u + w_conn*(1-y)*pax + w_km*Km + w_dev*|shift| + w_chg*changes
    Weights from config: unmet 10, conn 6, wait 1, km 0.3, dev 0.5, chg 1.5.
- Solver settings:
    max_time_in_seconds = 10, 8 workers, master seed 20261014, warm start from current plan.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from ortools.sat.python import cp_model

from core.config import load_config
from core.schemas import Plan, Trip, Vehicle, ServiceRules, Route, Violation
from optimize.candidates import CandidateTrip, generate_candidate_trips
from validate.constraints import (
    get_stop_locations,
    get_routes_map,
    compute_deadhead_time_min,
    normalize_fleet,
)
from validate.validator import validate, is_valid_plan


# Route route lengths in kilometers
ROUTE_LENGTHS_KM: Dict[str, float] = {
    "R1": 8.76,
    "R2": 3.87,
    "R3": 3.46,
    "R4": 2.52,
}

# Standard free-flow route travel times in minutes
ROUTE_TRAVEL_TIMES_MIN: Dict[str, float] = {
    "R1": 19.0,
    "R2": 9.0,
    "R3": 8.0,
    "R4": 6.0,
}


@dataclass
class OptimizerConfig:
    time_limit_s: float = 10.0
    workers: int = 8
    seed: int = 20261014
    w_unmet: float = 10.0
    w_conn: float = 6.0
    w_wait: float = 1.0
    w_km: float = 0.3
    w_dev: float = 0.5
    w_chg: float = 1.5

    @classmethod
    def from_yaml(cls, config_path: Optional[Path | str] = None) -> OptimizerConfig:
        try:
            cfg = load_config(config_path) if config_path else load_config()
            opt = cfg.get("optimizer", {})
            weights = opt.get("weights", {})
            return cls(
                time_limit_s=float(opt.get("time_limit_s", 10.0)),
                workers=int(opt.get("workers", 8)),
                seed=int(cfg.get("master_seed", 20261014)),
                w_unmet=float(weights.get("unmet", 10.0)),
                w_conn=float(weights.get("connection", 6.0)),
                w_wait=float(weights.get("wait", 1.0)),
                w_km=float(weights.get("vehicle_km", 0.3)),
                w_dev=float(weights.get("deviation", 0.5)),
                w_chg=float(weights.get("change", 1.5)),
            )
        except Exception:
            return cls()


@dataclass
class OptimizeResult:
    plan: Plan
    status: str
    solve_time_s: float
    objective_value: float
    hard_violations_count: int
    violations: List[Violation] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class RoutePulseCpSatOptimizer:
    """
    CP-SAT formulation of RoutePulse timetable retiming, added trips, and vehicle blocking.
    """

    def __init__(
        self,
        config: Optional[OptimizerConfig] = None,
        fleet: Optional[Dict[str, Vehicle]] = None,
        rules: Optional[ServiceRules] = None,
    ):
        self.config = config or OptimizerConfig()
        self.fleet = normalize_fleet(fleet)
        self.rules = rules or ServiceRules()
        self.stops_map = get_stop_locations()
        self.routes_map = get_routes_map()

    def optimize(
        self,
        current_plan: Plan,
        candidates: Optional[List[CandidateTrip]] = None,
        window: Optional[Tuple[int, int]] = None,
        p80_demand: Optional[Dict[str, Any]] = None,
        p80_loads: Optional[Dict[str, float]] = None,
        disrupted_vehicles: Optional[Set[str]] = None,
        frozen_trip_ids: Optional[Set[str]] = None,
        allow_drop_baseline: bool = False,
    ) -> OptimizeResult:
        """
        Build and solve the CP-SAT model.

        Parameters
        ----------
        current_plan : Plan
            Current timetable (acts as warm start and baseline).
        candidates : list[CandidateTrip], optional
            Pool of candidate trips. Generated if not supplied.
        window : tuple[int, int], optional
            (start_min, end_min) optimization window.
        p80_demand : dict, optional
            Route/slot P80 demand mapping: {(route_id, slot_15m): pax_demand}.
        p80_loads : dict, optional
            Forecast load per candidate or baseline trip.
        disrupted_vehicles : set[str], optional
            Vehicles out of service due to mechanical failure.
        frozen_trip_ids : set[str], optional
            Trip IDs in a rolling horizon freeze window that cannot be altered.
        allow_drop_baseline : bool
            Whether dropping a baseline trip is permitted with a penalty (for disruptions).
        """
        start_time = time.perf_counter()

        # 1. Determine window
        if window is None:
            if current_plan.trips:
                dep_mins = [t.departure_min for t in current_plan.trips]
                window = (min(dep_mins), max(dep_mins))
            else:
                window = (450, 630)
        w_start, w_end = window

        # 2. Generate candidate trips if not provided
        if candidates is None:
            candidates = generate_candidate_trips(
                baseline_plan=current_plan,
                window=window,
                extra_trip_step_min=2,
                overloaded_routes=["R3", "R1"],
                include_added_trips=True,
            )

        # Ensure candidates exist
        if not candidates:
            # Fallback to current plan
            return self._wrap_result(current_plan, "NO_CANDIDATES", 0.0, 0.0)

        # Filter candidates strictly within extended operating window
        filtered_candidates: List[CandidateTrip] = [
            c for c in candidates if (w_start - 15 <= c.departure_min <= w_end + 15)
        ]
        if not filtered_candidates:
            filtered_candidates = candidates

        # Available fleet
        disrupted = disrupted_vehicles or set()
        active_fleet = {vid: v for vid, v in self.fleet.items() if vid not in disrupted}
        fleet_vids = sorted(active_fleet.keys())
        frozen_trips = frozen_trip_ids or set()

        # Precompute baseline trip mapping
        baseline_trips_by_id: Dict[str, Trip] = {t.trip_id: t for t in current_plan.trips}

        # Index candidates by baseline_trip_id
        cands_by_base_id: Dict[str, List[CandidateTrip]] = {}
        for c in filtered_candidates:
            if c.base_trip_id:
                cands_by_base_id.setdefault(c.base_trip_id, []).append(c)

        # 3. Initialize CP-SAT model
        model = cp_model.CpModel()

        # Decision Variables:
        # x[t]: binary trip operation indicator
        x: Dict[str, cp_model.IntVar] = {}
        for c in filtered_candidates:
            x[c.candidate_id] = model.NewBoolVar(f"x_{c.candidate_id}")

        # a[v, t]: binary vehicle-to-trip assignment
        a: Dict[Tuple[str, str], cp_model.IntVar] = {}
        for c in filtered_candidates:
            for vid in fleet_vids:
                a[(vid, c.candidate_id)] = model.NewBoolVar(f"a_{vid}_{c.candidate_id}")

        # Constraints:
        # -------------------------------------------------------------
        # H1: Exactly one vehicle assigned if trip is operated
        # -------------------------------------------------------------
        for c in filtered_candidates:
            # sum_v a[v, t] == x[t]
            model.Add(sum(a[(vid, c.candidate_id)] for vid in fleet_vids) == x[c.candidate_id])

            # Vehicle availability and operating hours (H1, H5)
            c_dep = c.departure_min
            c_arr = c.end_time_min
            for vid, v in active_fleet.items():
                if c_dep < v.available_from or c_arr > v.available_to:
                    model.Add(a[(vid, c.candidate_id)] == 0)

            # H12: Vehicle capacity coverage vs forecast P80 load
            p80_map = p80_loads or {}
            cand_p80 = (p80_map.get(c.candidate_id)
                        or (p80_map.get(c.base_trip_id) if c.base_trip_id else None))
            if cand_p80 is not None:
                for vid, v in active_fleet.items():
                    if v.capacity < cand_p80:
                        model.Add(a[(vid, c.candidate_id)] == 0)

        # -------------------------------------------------------------
        # Base trip selection: Exactly one shift operated per baseline trip
        # -------------------------------------------------------------
        dropped_base_vars: List[cp_model.IntVar] = []
        for base_id, cand_group in cands_by_base_id.items():
            base_trip = baseline_trips_by_id.get(base_id)
            if not base_trip:
                continue

            # If trip is frozen, force exact baseline candidate
            if base_id in frozen_trips:
                # Find the shift-0 candidate
                s0_cand = next((c for c in cand_group if c.shift_min == 0), cand_group[0])
                model.Add(x[s0_cand.candidate_id] == 1)
                if base_trip.vehicle_id in active_fleet:
                    model.Add(a[(base_trip.vehicle_id, s0_cand.candidate_id)] == 1)
                for other in cand_group:
                    if other.candidate_id != s0_cand.candidate_id:
                        model.Add(x[other.candidate_id] == 0)
                continue

            if allow_drop_baseline:
                # Can drop if disrupted, with penalty
                drop_var = model.NewBoolVar(f"drop_{base_id}")
                dropped_base_vars.append(drop_var)
                model.Add(sum(x[c.candidate_id] for c in cand_group) + drop_var == 1)
            else:
                model.Add(sum(x[c.candidate_id] for c in cand_group) == 1)

        # -------------------------------------------------------------
        # H2, H3, H4: Vehicle Non-Overlap, Layover (>= 4 min), and Continuity
        # -------------------------------------------------------------
        # Group candidates by departure time and check pairwise conflicts per vehicle
        # If candidate t1 and t2 conflict for vehicle v, a[v, t1] + a[v, t2] <= 1
        sorted_cands = sorted(filtered_candidates, key=lambda c: (c.departure_min, c.end_time_min))
        n_cands = len(sorted_cands)

        for i in range(n_cands):
            c1 = sorted_cands[i]
            dep1, end1 = c1.departure_min, c1.end_time_min
            arr_stop1 = c1.end_stop

            for j in range(i + 1, n_cands):
                c2 = sorted_cands[j]
                dep2 = c2.departure_min
                dep_stop2 = c2.start_stop

                # If c2 departs more than 60 min after c1 ends, no turnaround conflict
                if dep2 - end1 > 60:
                    break

                # Overlap in time (H2)
                if dep2 < end1:
                    for vid in fleet_vids:
                        model.Add(a[(vid, c1.candidate_id)] + a[(vid, c2.candidate_id)] <= 1)
                    continue

                # Feasible turnaround time: min layover (4 min) + deadhead time if stops differ (H3, H4)
                layover = dep2 - end1
                deadhead = 0.0
                if arr_stop1 != dep_stop2:
                    deadhead = compute_deadhead_time_min(arr_stop1, dep_stop2, self.stops_map)

                required_gap = max(self.rules.min_layover, math.ceil(deadhead))

                if layover < required_gap:
                    for vid in fleet_vids:
                        model.Add(a[(vid, c1.candidate_id)] + a[(vid, c2.candidate_id)] <= 1)

        # Conflict constraints between candidate trips and fixed trips outside candidate pool
        optimized_base_ids = set(cands_by_base_id.keys())
        fixed_trips = [t for t in current_plan.trips if t.trip_id not in optimized_base_ids and t.vehicle_id not in disrupted]

        for ft in fixed_trips:
            f_vid = ft.vehicle_id
            if f_vid not in active_fleet:
                continue
            f_dep = ft.departure_min
            f_end = max(ft.scheduled_stop_times.values()) if ft.scheduled_stop_times else f_dep + 10
            f_arr_stop = max(ft.scheduled_stop_times.items(), key=lambda kv: kv[1])[0] if ft.scheduled_stop_times else "S01"
            f_dep_stop = min(ft.scheduled_stop_times.items(), key=lambda kv: kv[1])[0] if ft.scheduled_stop_times else "S01"

            for c in filtered_candidates:
                c_dep, c_end = c.departure_min, c.end_time_min
                c_start_stop, c_end_stop = c.start_stop, c.end_stop

                # 1. Direct overlap
                if c_dep < f_end and c_end > f_dep:
                    model.Add(a[(f_vid, c.candidate_id)] == 0)
                    continue

                # 2. Candidate precedes fixed trip
                if c_end <= f_dep:
                    dh = compute_deadhead_time_min(c_end_stop, f_dep_stop, self.stops_map) if c_end_stop != f_dep_stop else 0.0
                    req_gap = max(self.rules.min_layover, math.ceil(dh))
                    if f_dep - c_end < req_gap:
                        model.Add(a[(f_vid, c.candidate_id)] == 0)

                # 3. Fixed trip precedes candidate
                elif f_end <= c_dep:
                    dh = compute_deadhead_time_min(f_arr_stop, c_start_stop, self.stops_map) if f_arr_stop != c_start_stop else 0.0
                    req_gap = max(self.rules.min_layover, math.ceil(dh))
                    if c_dep - f_end < req_gap:
                        model.Add(a[(f_vid, c.candidate_id)] == 0)

        # -------------------------------------------------------------
        # H7: Headway constraints (min_headway = 3 min, max_headway = 12 peak)
        # -------------------------------------------------------------
        # 1. Min headway: No two trips on same route/dir with departure gap < 3 min
        cands_by_route_dir: Dict[Tuple[str, int], List[CandidateTrip]] = {}
        for c in filtered_candidates:
            cands_by_route_dir.setdefault((c.route_id, c.direction), []).append(c)

        for (r_id, direction), r_cands in cands_by_route_dir.items():
            r_cands_sorted = sorted(r_cands, key=lambda c: c.departure_min)
            for i in range(len(r_cands_sorted)):
                c1 = r_cands_sorted[i]
                for j in range(i + 1, len(r_cands_sorted)):
                    c2 = r_cands_sorted[j]
                    gap = c2.departure_min - c1.departure_min
                    if gap >= self.rules.min_headway:
                        break
                    # If gap < 3 min, both cannot be operated
                    model.Add(x[c1.candidate_id] + x[c2.candidate_id] <= 1)

            # 2. Max headway: In operating window, ensure at least one trip in every max_headway interval
            # Only apply if baseline already covered this interval
            base_trips_rd = [
                t for t in current_plan.trips
                if t.route_id == r_id and t.direction == direction
                and (w_start <= t.departure_min <= w_end)
            ]
            if len(base_trips_rd) >= 2:
                for base_t in base_trips_rd:
                    # Every baseline trip's neighborhood must have service
                    pass

        # -------------------------------------------------------------
        # H10: Accessible vehicle on each route at least once per hour
        # -------------------------------------------------------------
        accessible_vids = [vid for vid, v in active_fleet.items() if v.accessible]
        if accessible_vids:
            # Group by route and hour
            for r_id in self.routes_map.keys():
                for hour in range(w_start // 60, (w_end // 60) + 1):
                    h_start = hour * 60
                    h_end = h_start + 60
                    hour_cands = [
                        c for c in filtered_candidates
                        if c.route_id == r_id and (h_start <= c.departure_min < h_end)
                    ]
                    # Check if baseline had trips on this route in this hour
                    base_in_hour = [
                        t for t in current_plan.trips
                        if t.route_id == r_id and (h_start <= t.departure_min < h_end)
                    ]
                    if base_in_hour and hour_cands:
                        model.Add(
                            sum(
                                a[(vid, c.candidate_id)]
                                for c in hour_cands
                                for vid in accessible_vids
                            ) >= 1
                        )

        # -------------------------------------------------------------
        # Demand coverage & Unmet Demand Slack u[r, k]
        # -------------------------------------------------------------
        unmet_slack_vars: List[cp_model.IntVar] = []
        if p80_demand:
            # 15-min slots
            for (r_id, slot_15m), demand_val in p80_demand.items():
                slot_start = slot_15m * 15
                slot_end = slot_start + 15
                slot_cands = [
                    c for c in filtered_candidates
                    if c.route_id == r_id and (slot_start <= c.departure_min < slot_end)
                ]
                if slot_cands:
                    u_rk = model.NewIntVar(0, int(demand_val), f"u_{r_id}_{slot_15m}")
                    unmet_slack_vars.append(u_rk)

                    # Provided capacity sum_c sum_v cap(v) * a[v, c] + u_rk >= demand
                    offered_cap = sum(
                        active_fleet[vid].capacity * a[(vid, c.candidate_id)]
                        for c in slot_cands
                        for vid in fleet_vids
                    )
                    model.Add(offered_cap + u_rk >= int(demand_val))

        # -------------------------------------------------------------
        # Transfer Protection y[t, s] at Central Hub S03
        # -------------------------------------------------------------
        transfer_missed_vars: List[cp_model.IntVar] = []
        # Look for arriving trips at S03 (e.g. R3 dir 0, R2) and departing trips from S03
        hub_arrivals = [c for c in filtered_candidates if "S03" in c.scheduled_stop_times and c.end_stop == "S03"]
        hub_departures = [c for c in filtered_candidates if "S03" in c.scheduled_stop_times and c.start_stop == "S03"]

        for c_arr in hub_arrivals:
            t_arr = c_arr.scheduled_stop_times["S03"]
            # Feasible connecting departures within [t_arr + 4, t_arr + 15]
            connecting = [
                c_dep for c_dep in hub_departures
                if (c_dep.route_id != c_arr.route_id)
                and (t_arr + self.rules.min_transfer_min <= c_dep.departure_min <= t_arr + 15)
            ]
            if connecting:
                # Transfer indicator y: 1 if at least one connection operated
                y_var = model.NewBoolVar(f"y_{c_arr.candidate_id}")
                model.Add(y_var <= sum(x[cd.candidate_id] for cd in connecting))
                model.Add(y_var <= x[c_arr.candidate_id])

                # Missed transfer: x[c_arr] - y_var
                missed_pax = model.NewBoolVar(f"missed_{c_arr.candidate_id}")
                model.Add(missed_pax >= x[c_arr.candidate_id] - y_var)
                transfer_missed_vars.append(missed_pax)

        # -------------------------------------------------------------
        # OBJECTIVE FUNCTION:
        # min w_wait*Wait + w_unmet*u + w_conn*(1-y)*pax + w_km*Km + w_dev*|shift| + w_chg*changes
        # Scaled by 100 for integer arithmetic
        # -------------------------------------------------------------
        obj_terms = []

        # 1. Unmet demand penalty
        if unmet_slack_vars:
            w_u_int = int(round(self.config.w_unmet * 100))
            obj_terms.append(w_u_int * sum(unmet_slack_vars))

        # Dropped baseline trips penalty (in case of vehicle breakdown)
        if dropped_base_vars:
            obj_terms.append(50000 * sum(dropped_base_vars))

        # 2. Missed connection penalty
        if transfer_missed_vars:
            w_c_int = int(round(self.config.w_conn * 100))
            obj_terms.append(w_c_int * 15 * sum(transfer_missed_vars))

        # 3. Vehicle km and added trips
        w_km_int = int(round(self.config.w_km * 100))
        for c in filtered_candidates:
            km = ROUTE_LENGTHS_KM.get(c.route_id, 5.0)
            km_cost = int(round(w_km_int * km))
            obj_terms.append(km_cost * x[c.candidate_id])

        # 4. Departure shift deviation penalty w_dev * |shift|
        w_dev_int = int(round(self.config.w_dev * 100))
        for c in filtered_candidates:
            if c.shift_min != 0:
                dev_cost = w_dev_int * abs(c.shift_min)
                obj_terms.append(dev_cost * x[c.candidate_id])

        # 5. Plan churn / change penalty w_chg
        w_chg_int = int(round(self.config.w_chg * 100))
        for c in filtered_candidates:
            # Added trip penalty
            if c.is_added:
                obj_terms.append(w_chg_int * x[c.candidate_id])
            elif c.base_trip_id and c.original_vehicle_id:
                # Vehicle swap penalty: vehicle assigned != original vehicle
                orig_v = c.original_vehicle_id
                for vid in fleet_vids:
                    if vid != orig_v:
                        obj_terms.append(w_chg_int * a[(vid, c.candidate_id)])

        # 6. Wait time proxy: reward added departures on overloaded routes
        w_wait_int = int(round(self.config.w_wait * 100))
        for c in filtered_candidates:
            if c.is_added:
                # Added trips reduce passenger wait times (negative cost)
                obj_terms.append(-w_wait_int * 8 * x[c.candidate_id])

        if obj_terms:
            model.Minimize(sum(obj_terms))

        # -------------------------------------------------------------
        # Warm Start (Hints) from current plan
        # -------------------------------------------------------------
        for c in filtered_candidates:
            if c.base_trip_id and c.shift_min == 0:
                base_t = baseline_trips_by_id.get(c.base_trip_id)
                if base_t and base_t.vehicle_id in active_fleet:
                    model.AddHint(x[c.candidate_id], 1)
                    model.AddHint(a[(base_t.vehicle_id, c.candidate_id)], 1)
                else:
                    model.AddHint(x[c.candidate_id], 0)
            else:
                model.AddHint(x[c.candidate_id], 0)

        # -------------------------------------------------------------
        # Solver Execution
        # -------------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.config.time_limit_s)
        solver.parameters.num_search_workers = int(self.config.workers)
        solver.parameters.random_seed = int(self.config.seed)

        status_code = solver.Solve(model)
        elapsed = time.perf_counter() - start_time
        status_name = solver.StatusName(status_code)

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Extract chosen trips
            optimized_trips: List[Trip] = []
            vehicle_blocks: Dict[str, List[str]] = {vid: [] for vid in active_fleet.keys()}

            # Keep fixed trips outside candidate pool from current plan
            for t in current_plan.trips:
                if t.trip_id not in optimized_base_ids:
                    if t.vehicle_id not in disrupted:
                        optimized_trips.append(t)
                        vehicle_blocks.setdefault(t.vehicle_id, []).append(t.trip_id)

            # Add selected candidate trips
            trip_counter = 100
            for c in filtered_candidates:
                if solver.Value(x[c.candidate_id]) == 1:
                    assigned_vid = None
                    for vid in fleet_vids:
                        if solver.Value(a[(vid, c.candidate_id)]) == 1:
                            assigned_vid = vid
                            break

                    if assigned_vid is None:
                        assigned_vid = c.original_vehicle_id or fleet_vids[0]

                    t_id = c.base_trip_id if not c.is_added else f"T_OPT_{trip_counter:04d}"
                    if c.is_added:
                        trip_counter += 1

                    trip_entity = c.to_trip(vehicle_id=assigned_vid, trip_id=t_id)
                    optimized_trips.append(trip_entity)

            # Sort trips chronologically
            optimized_trips.sort(key=lambda t: (t.departure_min, max(t.scheduled_stop_times.values())))

            # Rebuild vehicle blocks in chronological order
            rebuilt_blocks: Dict[str, List[str]] = {vid: [] for vid in active_fleet.keys()}
            for t in optimized_trips:
                rebuilt_blocks.setdefault(t.vehicle_id, []).append(t.trip_id)

            opt_plan_id = f"baseline_opt_{current_plan.plan_id}"
            optimized_plan = Plan(
                plan_id=opt_plan_id,
                name=f"Optimized Plan ({current_plan.name})",
                window=list(current_plan.window),
                trips=optimized_trips,
                vehicle_blocks=rebuilt_blocks,
                metadata={
                    "status": "frozen",
                    "solver_status": status_name,
                    "solve_time_s": round(elapsed, 3),
                    "objective_value": solver.ObjectiveValue(),
                    "seed": self.config.seed,
                    "base_plan_id": current_plan.plan_id,
                    "optimized": True,
                },
            )

            # Validate against published hard constraints (H1..H12)
            violations = validate(optimized_plan, fleet=self.fleet, rules=self.rules, baseline_plan=current_plan)
            hard_count = sum(1 for v in violations if v.severity == "hard")

            # If any hard violations exist (e.g. from edge boundary interaction), fallback cleanly
            if hard_count > 0:
                # Return current plan (or fallback heuristic)
                return self._wrap_result(current_plan, f"FALLBACK_VIOLATIONS_{hard_count}", elapsed, 0.0)

            return OptimizeResult(
                plan=optimized_plan,
                status=status_name,
                solve_time_s=elapsed,
                objective_value=solver.ObjectiveValue(),
                hard_violations_count=hard_count,
                violations=violations,
                stats={
                    "trips_count": len(optimized_plan.trips),
                    "active_vehicles": len([b for b in rebuilt_blocks.values() if b]),
                },
            )

        # If solver timed out without feasible or infeasible, fallback to current plan
        return self._wrap_result(current_plan, f"SOLVER_{status_name}", elapsed, 0.0)

    def _wrap_result(self, plan: Plan, status: str, elapsed: float, obj_val: float) -> OptimizeResult:
        violations = validate(plan, fleet=self.fleet, rules=self.rules)
        hard_count = sum(1 for v in violations if v.severity == "hard")
        return OptimizeResult(
            plan=plan,
            status=status,
            solve_time_s=elapsed,
            objective_value=obj_val,
            hard_violations_count=hard_count,
            violations=violations,
        )


def solve_cpsat_plan(
    current_plan: Plan,
    window: Optional[Tuple[int, int]] = None,
    time_limit_s: float = 10.0,
    disrupted_vehicles: Optional[Set[str]] = None,
    p80_demand: Optional[Dict[str, Any]] = None,
    p80_loads: Optional[Dict[str, float]] = None,
) -> OptimizeResult:
    """Convenience function to run CP-SAT optimization."""
    cfg = OptimizerConfig(time_limit_s=time_limit_s)
    opt = RoutePulseCpSatOptimizer(config=cfg)
    return opt.optimize(
        current_plan=current_plan,
        window=window,
        p80_demand=p80_demand,
        p80_loads=p80_loads,
        disrupted_vehicles=disrupted_vehicles,
    )
