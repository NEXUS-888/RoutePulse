"""
RoutePulse Candidate Trip Generator (optimize/candidates.py)
Generates decision candidate trips for the RoutePulse optimization engine:
1. Baseline trips (unmodified, shift = 0).
2. Retimed candidate trips: shifted by [-5..+5] minutes in 1-minute steps (H8 compliant).
3. Added candidate trips: inserted every 2 minutes on overloaded routes (e.g. R3, R1 during peak).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from core.schemas import Plan, Trip, Route, Stop

# Standard stop arrival offsets (relative to trip departure minute) based on topology free-flow run times
ROUTE_STOP_OFFSETS: Dict[Tuple[str, int], List[Tuple[str, int]]] = {
    ("R1", 0): [
        ("S02", 2), ("S03", 5), ("S04", 8), ("S05", 11),
        ("S06", 14), ("S07", 16), ("S01", 19),
    ],
    ("R2", 0): [
        ("S10", 2), ("S08", 4), ("S09", 6), ("S03", 9),
    ],
    ("R3", 0): [
        ("S13", 0), ("S01", 4), ("S02", 6), ("S03", 8),
    ],
    ("R3", 1): [
        ("S03", 0), ("S02", 2), ("S01", 4), ("S13", 8),
    ],
    ("R4", 0): [
        ("S03", 0), ("S14", 2), ("S12", 4), ("S11", 6),
    ],
    ("R4", 1): [
        ("S11", 0), ("S12", 2), ("S14", 4), ("S03", 6),
    ],
}


@dataclass
class CandidateTrip:
    """
    Representation of a candidate trip in the optimization decision pool.
    """
    candidate_id: str
    route_id: str
    direction: int
    departure_min: int
    scheduled_stop_times: Dict[str, int]
    base_trip_id: Optional[str] = None
    shift_min: int = 0
    is_added: bool = False
    original_vehicle_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def end_time_min(self) -> int:
        """Arrival time at the final scheduled stop."""
        if self.scheduled_stop_times:
            return max(self.scheduled_stop_times.values())
        return self.departure_min

    @property
    def start_stop(self) -> str:
        """Earliest scheduled stop identifier."""
        if not self.scheduled_stop_times:
            return "S01"
        return min(self.scheduled_stop_times.items(), key=lambda kv: kv[1])[0]

    @property
    def end_stop(self) -> str:
        """Latest scheduled stop identifier."""
        if not self.scheduled_stop_times:
            return "S01"
        return max(self.scheduled_stop_times.items(), key=lambda kv: kv[1])[0]

    def to_trip(self, vehicle_id: Optional[str] = None, trip_id: Optional[str] = None) -> Trip:
        """Instantiate a validated Pydantic Trip entity from this candidate."""
        v_id = vehicle_id or self.original_vehicle_id or "B1"
        t_id = trip_id or (self.base_trip_id if not self.is_added else self.candidate_id)
        return Trip(
            trip_id=t_id,
            route_id=self.route_id,
            direction=self.direction,
            vehicle_id=v_id,
            departure_min=self.departure_min,
            scheduled_stop_times=dict(self.scheduled_stop_times),
        )


def build_stop_times(route_id: str, direction: int, dep_min: int) -> Dict[str, int]:
    """Build scheduled stop times dictionary for a given route, direction, and departure time."""
    offsets = ROUTE_STOP_OFFSETS.get((route_id, direction))
    if offsets is None:
        offsets = ROUTE_STOP_OFFSETS.get((route_id, 0), [("S01", 10)])
    return {stop_id: dep_min + off for stop_id, off in offsets}


def generate_candidate_trips(
    baseline_plan: Plan,
    window: Optional[Tuple[int, int]] = None,
    shift_range: Tuple[int, int] = (-5, 5),
    shift_step: int = 1,
    extra_trip_step_min: int = 2,
    overloaded_routes: Optional[Sequence[str]] = None,
    include_added_trips: bool = True,
    operating_hours: Tuple[int, int] = (390, 1320),
) -> List[CandidateTrip]:
    """
    Generate the complete candidate trip pool for RoutePulse optimization.

    Parameters
    ----------
    baseline_plan : Plan
        Current or baseline operating plan.
    window : tuple[int, int], optional
        (start_min, end_min) interval to filter or generate trips within.
        Defaults to window defined on baseline_plan or full operating day (390..1320).
    shift_range : tuple[int, int]
        Minimum and maximum departure shift in minutes (e.g. (-5, 5)).
    shift_step : int
        Step size for retiming shifts (default 1 min).
    extra_trip_step_min : int
        Departure step for added candidate trips on overloaded routes (default 2 min).
    overloaded_routes : list[str], optional
        Routes on which to inject added candidate trips. Defaults to ["R3", "R1"].
    include_added_trips : bool
        Whether to generate added candidate trips (default True).
    operating_hours : tuple[int, int]
        Valid operating window (06:30..22:00 = 390..1320).

    Returns
    -------
    list[CandidateTrip]
        Generated candidate trips.
    """
    candidates: List[CandidateTrip] = []
    overloaded = list(overloaded_routes) if overloaded_routes is not None else ["R3", "R1"]

    # Determine optimization window
    if window is not None:
        w_start, w_end = window
    else:
        # Default to peak morning window W1 (450..630) if not specified, or plan departures
        if baseline_plan.trips:
            dep_mins = [t.departure_min for t in baseline_plan.trips]
            w_start, w_end = min(dep_mins), max(dep_mins)
        else:
            w_start, w_end = 450, 630

    min_op, max_op = operating_hours

    # 1. Baseline trips and shifted retiming candidates [-5..+5] min
    for base_trip in baseline_plan.trips:
        # Only process trips that fall within or touch the active window
        if not (w_start - 10 <= base_trip.departure_min <= w_end + 10):
            continue

        for shift in range(shift_range[0], shift_range[1] + 1, shift_step):
            cand_dep = base_trip.departure_min + shift
            # Enforce operating hours H5
            if cand_dep < min_op or cand_dep > max_op:
                continue

            sign_str = "0" if shift == 0 else (f"p{shift}" if shift > 0 else f"m{abs(shift)}")
            cand_id = f"c_{base_trip.trip_id}_s{sign_str}"

            # Shift all stop arrival times identically
            cand_stop_times = {
                stop: arr + shift for stop, arr in base_trip.scheduled_stop_times.items()
            }

            candidates.append(
                CandidateTrip(
                    candidate_id=cand_id,
                    route_id=base_trip.route_id,
                    direction=base_trip.direction,
                    departure_min=cand_dep,
                    scheduled_stop_times=cand_stop_times,
                    base_trip_id=base_trip.trip_id,
                    shift_min=shift,
                    is_added=False,
                    original_vehicle_id=base_trip.vehicle_id,
                )
            )

    # 2. Added candidate trips every 2 min on overloaded routes (especially R3 and R1)
    if include_added_trips and extra_trip_step_min > 0:
        for route_id in overloaded:
            # Directions to cover
            directions = [0, 1] if route_id in ("R3", "R4") else [0]
            for direction in directions:
                for dep_t in range(w_start, w_end + 1, extra_trip_step_min):
                    if dep_t < min_op or dep_t > max_op:
                        continue

                    cand_id = f"add_{route_id}_d{direction}_{dep_t:04d}"
                    stop_times = build_stop_times(route_id, direction, dep_t)

                    candidates.append(
                        CandidateTrip(
                            candidate_id=cand_id,
                            route_id=route_id,
                            direction=direction,
                            departure_min=dep_t,
                            scheduled_stop_times=stop_times,
                            base_trip_id=None,
                            shift_min=0,
                            is_added=True,
                            original_vehicle_id=None,
                            metadata={"overloaded_route": route_id},
                        )
                    )

    return candidates
