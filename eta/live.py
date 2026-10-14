"""
Live ETA Adjustments & Dwell Modeling (eta/live.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- Online delay ratio rho (EWMA of observed/expected segment times over last 2-3 segments).
- Downstream exponential decay: rho_k = 1 + (rho - 1) * gamma^k (gamma = 0.85).
- Dwell prediction: max(6, 5 + 1.4*boardings + 0.8*alightings) seconds.
- Base profile + live estimate accumulator for downstream stops.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from core.schemas import Route, Stop, Trip
from eta.profiles import HistoricalProfiles


def predict_dwell_time_sec(boardings: float = 0.0, alightings: float = 0.0) -> float:
    """
    Computes predicted dwell time in seconds based on boardings and alightings:
    dwell = max(6, 5 + 1.4*boardings + 0.8*alightings).
    """
    return max(6.0, 5.0 + 1.4 * max(0.0, boardings) + 0.8 * max(0.0, alightings))


def predict_dwell_time_min(boardings: float = 0.0, alightings: float = 0.0) -> float:
    """Predicted dwell time converted to minutes."""
    return predict_dwell_time_sec(boardings, alightings) / 60.0


class OnlineDelayTracker:
    """
    Tracks real-time performance of an active vehicle trip.
    Maintains an EWMA of observed / expected segment traversal ratios over the last M (2-3) segments.
    Applies exponential decay downstream: rho_k = 1 + (rho - 1) * gamma^k.
    """

    def __init__(
        self,
        lookback_segments: int = 3,
        decay_gamma: float = 0.85,
        ewma_alpha: float = 0.6,
    ):
        self.lookback = lookback_segments
        self.gamma = decay_gamma
        self.alpha = ewma_alpha
        # Ring buffer of recent (observed_s, expected_s)
        self.recent_segments: list[tuple[float, float]] = []

    def reset(self) -> None:
        self.recent_segments.clear()

    def update(
        self,
        *args: Any,
        observed_sec: Optional[float] = None,
        expected_sec: Optional[float] = None,
        segment_id: Optional[str] = None,
    ) -> float:
        """
        Records a newly completed segment and updates the delay ratio rho.
        Accepts both update(observed_sec, expected_sec) and update(segment_id, observed_sec, expected_sec).
        Returns the updated current rho.
        """
        if len(args) >= 3:
            obs = float(args[1])
            exp = float(args[2])
        elif len(args) == 2:
            obs = float(args[0])
            exp = float(args[1])
        else:
            obs = float(observed_sec if observed_sec is not None else 1.0)
            exp = float(expected_sec if expected_sec is not None else 1.0)

        obs = max(1.0, obs)
        exp = max(1.0, exp)
        self.recent_segments.append((obs, exp))
        if len(self.recent_segments) > self.lookback:
            self.recent_segments.pop(0)
        return self.get_rho()

    def get_rho(self) -> float:
        """
        Calculates EWMA ratio of observed to expected traversal times over recent segments.
        If no completed segments yet, returns 1.0 (on-schedule expectation).
        Clipped to [0.5, 2.5] for numerical stability.
        """
        if not self.recent_segments:
            return 1.0

        M = len(self.recent_segments)
        # Compute weights: newest has weight 1.0, older has alpha, alpha^2...
        weights = [self.alpha ** (M - 1 - i) for i in range(M)]
        ratios = [obs / exp for (obs, exp) in self.recent_segments]

        total_w = sum(weights)
        if total_w <= 0:
            return 1.0

        rho = sum(w * r for w, r in zip(weights, ratios)) / total_w
        return float(np.clip(rho, 0.5, 2.5))

    def get_decayed_rho(self, stops_ahead: int) -> float:
        """
        Computes decayed delay ratio for the k-th downstream segment:
        rho_k = 1 + (rho - 1) * (gamma ^ k).
        """
        k = max(1, stops_ahead)
        rho = self.get_rho()
        decayed = 1.0 + (rho - 1.0) * (self.gamma ** k)
        return float(np.clip(decayed, 0.5, 2.5))


def compute_base_eta(
    trip: Trip,
    route: Route,
    current_stop_id: str,
    target_stop_id: str,
    query_time_min: float,
    profiles: HistoricalProfiles,
    day: int = 1,
    rho: float = 1.0,
    expected_boardings_map: Optional[dict[str, float]] = None,
    expected_alightings_map: Optional[dict[str, float]] = None,
    gamma: float = 0.85,
) -> tuple[float, float, int]:
    """
    Computes base Profile + Live ETA (in minutes from midnight) for a downstream stop.
    Accumulates decayed historical segment travel times plus dwell times at intermediate stops.

    Returns:
      (base_eta_min, remaining_distance_m, stops_ahead)
    """
    # Determine stop sequence for this trip direction
    if route.type == "linear" and trip.direction == 1:
        stop_seq = list(reversed(route.stop_sequence))
    else:
        stop_seq = list(route.stop_sequence)

    if current_stop_id not in stop_seq or target_stop_id not in stop_seq:
        # Fallback to schedule
        sched = trip.scheduled_stop_times.get(target_stop_id, query_time_min)
        return max(query_time_min, float(sched)), 0.0, 1

    curr_idx = stop_seq.index(current_stop_id)
    target_idx = stop_seq.index(target_stop_id)

    if target_idx <= curr_idx:
        # Target is at or behind current stop
        return max(query_time_min, query_time_min + 0.5), 0.0, 0

    stops_ahead = target_idx - curr_idx
    running_time_min = query_time_min
    remaining_dist_m = 0.0

    p_board = expected_boardings_map or {}
    p_alight = expected_alightings_map or {}

    for k in range(curr_idx, target_idx):
        from_s = stop_seq[k]
        to_s = stop_seq[k + 1]
        seg_id = f"{from_s}_{to_s}"

        # Segment order ahead (1-based: 1, 2, ...)
        step = k - curr_idx + 1
        rho_k = 1.0 + (rho - 1.0) * (gamma ** step)

        # Historical profile segment time in seconds
        med_s, _ = profiles.get_segment_time(
            seg_id, running_time_min, day=day, route_id=route.route_id
        )
        adj_travel_sec = med_s * rho_k
        travel_min = adj_travel_sec / 60.0

        # Dwell time at destination stop of this segment (if not the target stop, or if dwell occurs at target)
        # Note: arrival at target stop happens BEFORE dwell at target stop.
        # Intermediate stops (between curr and target) have dwell added:
        dwell_min = 0.0
        if k > curr_idx:
            # Stop between curr and target
            b = p_board.get(from_s, 2.0)
            a = p_alight.get(from_s, 1.0)
            dwell_min = predict_dwell_time_min(b, a)

        running_time_min += (travel_min + dwell_min)

    return round(running_time_min, 2), remaining_dist_m, stops_ahead
