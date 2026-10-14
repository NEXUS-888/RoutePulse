"""
GPS Processing & Map Matching (eta/gps_processing.py)
Implements Section 8.2 of docs/ARCHITECTURE.md:
1. Map matching: Lightweight HMM / Viterbi on 1-D route polyline progress with monotonic enforcement.
2. Smoothing: 1-D constant-velocity Kalman filter on progress s(t); handles dropouts; flags gaps > 60s.
3. Stop events: 25m geofence detection -> arrival, departure, dwell. Emits segment_times table.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from core.geometry import latlon_to_xy, xy_to_latlon, euclidean_dist
from core.schemas import GpsPing, Plan, Route, Stop, Trip


class PolylineMatcher:
    """
    Projects 2D coordinates onto a route polyline and converts between
    progress distance s (in meters) and 2D metric (x, y) coordinates.
    """

    def __init__(self, polyline: Sequence[Sequence[float]]):
        if len(polyline) < 2:
            raise ValueError("Polyline must have at least 2 vertices")
        self.polyline = [list(pt) for pt in polyline]
        self.n_vertices = len(self.polyline)
        self.n_segments = self.n_vertices - 1

        self.seg_lengths: list[float] = []
        self.cum_dist: list[float] = [0.0]
        self.seg_vecs: list[tuple[float, float]] = []
        self.seg_len_sq: list[float] = []

        total_d = 0.0
        for i in range(self.n_segments):
            p1 = self.polyline[i]
            p2 = self.polyline[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            l = math.hypot(dx, dy)
            self.seg_lengths.append(l)
            self.seg_vecs.append((dx, dy))
            self.seg_len_sq.append(dx * dx + dy * dy)
            total_d += l
            self.cum_dist.append(total_d)

        self.total_length = total_d

    def project_point(self, x: float, y: float) -> tuple[float, float, int]:
        """
        Projects point (x, y) onto the nearest point of the polyline.
        Returns: (progress_m, distance_to_polyline_m, segment_index)
        """
        best_dist = float("inf")
        best_progress = 0.0
        best_seg = 0

        for i in range(self.n_segments):
            ax, ay = self.polyline[i]
            dx, dy = self.seg_vecs[i]
            l_sq = self.seg_len_sq[i]
            if l_sq <= 1e-9:
                t = 0.0
            else:
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l_sq))

            proj_x = ax + t * dx
            proj_y = ay + t * dy
            dist = math.hypot(x - proj_x, y - proj_y)

            if dist < best_dist:
                best_dist = dist
                best_progress = self.cum_dist[i] + t * self.seg_lengths[i]
                best_seg = i

        return best_progress, best_dist, best_seg

    def get_candidates(
        self, x: float, y: float, max_dist: float = 120.0, top_k: int = 4
    ) -> list[tuple[float, float, int]]:
        """
        Finds candidate projection points on all segments within max_dist.
        Returns list of (progress_m, distance_to_polyline_m, segment_index) sorted by distance.
        """
        candidates: list[tuple[float, float, int]] = []
        for i in range(self.n_segments):
            ax, ay = self.polyline[i]
            dx, dy = self.seg_vecs[i]
            l_sq = self.seg_len_sq[i]
            if l_sq <= 1e-9:
                t = 0.0
            else:
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l_sq))

            proj_x = ax + t * dx
            proj_y = ay + t * dy
            dist = math.hypot(x - proj_x, y - proj_y)
            progress = self.cum_dist[i] + t * self.seg_lengths[i]

            if dist <= max_dist:
                candidates.append((progress, dist, i))

        if not candidates:
            # Fall back to global nearest segment
            p, d, s = self.project_point(x, y)
            return [(p, d, s)]

        candidates.sort(key=lambda c: c[1])
        return candidates[:top_k]

    def progress_to_xy(self, s: float) -> tuple[float, float]:
        """Converts progress s along polyline to metric coordinates (x, y)."""
        s_clamped = max(0.0, min(self.total_length, s))
        if s_clamped <= 0.0:
            return float(self.polyline[0][0]), float(self.polyline[0][1])
        if s_clamped >= self.total_length:
            return float(self.polyline[-1][0]), float(self.polyline[-1][1])

        # Binary search or scan for segment
        for i in range(self.n_segments):
            if self.cum_dist[i] <= s_clamped <= self.cum_dist[i + 1]:
                seg_len = self.seg_lengths[i]
                if seg_len <= 1e-9:
                    return float(self.polyline[i][0]), float(self.polyline[i][1])
                t = (s_clamped - self.cum_dist[i]) / seg_len
                ax, ay = self.polyline[i]
                dx, dy = self.seg_vecs[i]
                return ax + t * dx, ay + t * dy

        return float(self.polyline[-1][0]), float(self.polyline[-1][1])


def map_match_pings(
    pings: Sequence[Union[dict[str, Any], GpsPing]] | pd.DataFrame,
    polyline: Sequence[Sequence[float]],
    v_max: float = 25.0,
    sigma_gps: float = 8.0,
) -> list[dict[str, Any]]:
    """
    Lightweight HMM / Viterbi map matching of GPS pings onto a 1D route polyline.
    Enforces monotonic 1D progress s(t).

    Returns a list of dicts with:
      - t_sec: int
      - progress_m: float
      - matched_x: float
      - matched_y: float
      - match_dist_m: float
      - speed_mps: float
    """
    if isinstance(pings, pd.DataFrame):
        ping_list = pings.to_dict(orient="records")
    else:
        ping_list = [p.model_dump() if isinstance(p, GpsPing) else dict(p) for p in pings]

    if not ping_list:
        return []

    matcher = PolylineMatcher(polyline)

    # Standardize ping format (ensure x, y in meters)
    formatted_pings: list[dict[str, Any]] = []
    for p in ping_list:
        t_sec = int(p["t_sec"])
        if "x" in p and "y" in p and not (math.isnan(p["x"]) or math.isnan(p["y"])):
            x, y = float(p["x"]), float(p["y"])
        elif "lat" in p and "lon" in p:
            x, y = latlon_to_xy(float(p["lat"]), float(p["lon"]))
        else:
            continue
        speed = float(p.get("speed_mps", 0.0))
        formatted_pings.append({
            "t_sec": t_sec,
            "x": x,
            "y": y,
            "speed_mps": speed,
            "original": p,
        })

    formatted_pings.sort(key=lambda p: p["t_sec"])
    N = len(formatted_pings)
    if N == 0:
        return []

    # Get candidate projections for each ping
    candidates_per_ping: list[list[tuple[float, float, int]]] = []
    for p in formatted_pings:
        cands = matcher.get_candidates(p["x"], p["y"], max_dist=120.0, top_k=4)
        candidates_per_ping.append(cands)

    # Viterbi Dynamic Programming
    # V[k][i] = best cost to candidate i of ping k
    # BP[k][i] = index of candidate in ping k-1 that led to best cost
    K0 = len(candidates_per_ping[0])
    V: list[list[float]] = [[(c[1] / sigma_gps) ** 2 for c in candidates_per_ping[0]]]
    BP: list[list[int]] = [[-1] * K0]

    for k in range(1, N):
        prev_cands = candidates_per_ping[k - 1]
        curr_cands = candidates_per_ping[k]
        dt = max(1.0, float(formatted_pings[k]["t_sec"] - formatted_pings[k - 1]["t_sec"]))

        curr_V: list[float] = []
        curr_BP: list[int] = []

        for i, (curr_s, curr_d, _) in enumerate(curr_cands):
            emission_cost = (curr_d / sigma_gps) ** 2
            best_prev_cost = float("inf")
            best_prev_idx = 0

            for j, (prev_s, prev_d, _) in enumerate(prev_cands):
                ds = curr_s - prev_s
                # Transition cost
                if ds < -5.0:
                    # Harsh penalty for moving backwards along route
                    trans_cost = 1000.0 + 100.0 * abs(ds)
                elif ds < 0:
                    # Minor jitter backwards
                    trans_cost = 50.0 * abs(ds)
                else:
                    speed = ds / dt
                    if speed > v_max:
                        trans_cost = 500.0 + 50.0 * (speed - v_max)
                    else:
                        # Mild penalty for unrealistic jump from typical bus speed (~10 m/s)
                        trans_cost = 0.5 * ((speed - 10.0) / 10.0) ** 2

                total_cost = V[k - 1][j] + trans_cost
                if total_cost < best_prev_cost:
                    best_prev_cost = total_cost
                    best_prev_idx = j

            curr_V.append(emission_cost + best_prev_cost)
            curr_BP.append(best_prev_idx)

        V.append(curr_V)
        BP.append(curr_BP)

    # Traceback optimal candidate path
    best_last_idx = int(np.argmin(V[-1]))
    path_indices = [best_last_idx]
    for k in range(N - 1, 0, -1):
        prev_idx = BP[k][path_indices[-1]]
        path_indices.append(prev_idx)
    path_indices.reverse()

    # Extract chosen progress values
    chosen_s: list[float] = []
    chosen_d: list[float] = []
    for k, idx in enumerate(path_indices):
        cand = candidates_per_ping[k][idx]
        chosen_s.append(cand[0])
        chosen_d.append(cand[1])

    # Enforce strictly non-decreasing progress along route
    monotone_s: list[float] = [chosen_s[0]]
    for k in range(1, N):
        monotone_s.append(max(monotone_s[-1], chosen_s[k]))

    # Construct final matched ping records
    matched_results: list[dict[str, Any]] = []
    for k in range(N):
        s_val = min(matcher.total_length, monotone_s[k])
        mx, my = matcher.progress_to_xy(s_val)
        matched_results.append({
            "t_sec": formatted_pings[k]["t_sec"],
            "progress_m": round(s_val, 2),
            "matched_x": round(mx, 2),
            "matched_y": round(my, 2),
            "match_dist_m": round(chosen_d[k], 2),
            "speed_mps": formatted_pings[k]["speed_mps"],
            "raw_x": formatted_pings[k]["x"],
            "raw_y": formatted_pings[k]["y"],
        })

    return matched_results


class KalmanSmoother1D:
    """
    1D constant-velocity Kalman filter for smoothing route progress s(t).
    State: x = [s (progress in m), v (velocity in m/s)]^T.
    Handles dropouts by propagating state variance.
    Flags gaps > 60s as low_confidence.
    """

    def __init__(self, q_accel: float = 0.2, r_obs: float = 64.0):
        self.q = q_accel  # Process acceleration noise spectral density
        self.r = r_obs    # Measurement noise variance (sigma=8m -> 64 m^2)

    def smooth(
        self, matched_pings: list[dict[str, Any]], max_gap_s: float = 60.0
    ) -> list[dict[str, Any]]:
        """
        Runs Kalman filter over matched pings to smooth progress and estimate velocity.
        Flags pings where the preceding time gap exceeds max_gap_s as low_confidence.
        """
        if not matched_pings:
            return []

        N = len(matched_pings)
        if N == 1:
            res = dict(matched_pings[0])
            res["smoothed_progress_m"] = res["progress_m"]
            res["smoothed_speed_mps"] = max(0.0, res.get("speed_mps", 0.0))
            res["low_confidence"] = False
            res["quality_flag"] = "high_confidence"
            return [res]

        # Initialize state: x = [s0, v0]
        s0 = matched_pings[0]["progress_m"]
        v0 = max(0.0, matched_pings[0].get("speed_mps", 0.0))
        x = np.array([s0, v0], dtype=float)
        P = np.diag([self.r, 4.0])  # Initial covariance

        H = np.array([[1.0, 0.0]])
        R = np.array([[self.r]])

        smoothed: list[dict[str, Any]] = []

        # Record first state
        p0 = dict(matched_pings[0])
        p0["smoothed_progress_m"] = round(s0, 2)
        p0["smoothed_speed_mps"] = round(v0, 2)
        p0["low_confidence"] = False
        p0["quality_flag"] = "high_confidence"
        smoothed.append(p0)

        last_s = s0

        for k in range(1, N):
            p_curr = dict(matched_pings[k])
            dt = max(0.1, float(p_curr["t_sec"] - matched_pings[k - 1]["t_sec"]))
            z = float(p_curr["progress_m"])

            is_gap = dt > max_gap_s

            # State transition matrix F and process noise Q
            F = np.array([[1.0, dt], [0.0, 1.0]])
            Q = self.q * np.array([
                [(dt ** 3) / 3.0, (dt ** 2) / 2.0],
                [(dt ** 2) / 2.0, dt]
            ])
            if is_gap:
                # Extra process noise for long gap uncertainty
                Q *= 3.0

            # Time update (Predict)
            x_pred = F @ x
            P_pred = F @ P @ F.T + Q

            # Measurement update (Update)
            y = z - (H @ x_pred)[0]
            S = (H @ P_pred @ H.T)[0, 0] + self.r
            K = (P_pred @ H.T) / S

            x = x_pred + K.flatten() * y
            P = (np.eye(2) - K @ H) @ P_pred

            # Enforce non-decreasing progress and non-negative speed
            s_smooth = max(last_s, float(x[0]))
            v_smooth = max(0.0, float(x[1]))
            x[0] = s_smooth
            x[1] = v_smooth
            last_s = s_smooth

            p_curr["smoothed_progress_m"] = round(s_smooth, 2)
            p_curr["smoothed_speed_mps"] = round(v_smooth, 2)
            p_curr["low_confidence"] = is_gap
            p_curr["quality_flag"] = "low_confidence" if is_gap else "high_confidence"
            smoothed.append(p_curr)

        return smoothed


def smooth_matched_pings(
    matched_pings: list[dict[str, Any]], max_gap_s: float = 60.0
) -> list[dict[str, Any]]:
    """Helper function to apply Kalman smoothing on matched pings."""
    smoother = KalmanSmoother1D()
    return smoother.smooth(matched_pings, max_gap_s=max_gap_s)


class StopEventDetector:
    """
    Detects arrival, departure, and dwell events at stops using a 25m geofence on 1D progress.
    Computes segment travel times between consecutive stops.
    """

    def __init__(self, geofence_m: float = 25.0):
        self.geofence_m = geofence_m

    def compute_stop_progresses(
        self,
        stop_sequence: list[str],
        polyline: list[list[float]],
        stops_map: dict[str, Stop],
    ) -> list[tuple[str, float]]:
        """
        Calculates monotonic reference progress s along the polyline for each stop in stop_sequence.
        """
        matcher = PolylineMatcher(polyline)
        stop_progs: list[tuple[str, float]] = []
        last_s = 0.0

        for idx, sid in enumerate(stop_sequence):
            stop_obj = stops_map[sid]
            # Project stop (x, y) to polyline
            if idx == 0:
                s_ref = 0.0
            elif idx == len(stop_sequence) - 1 and len(stop_sequence) > 1 and stop_sequence[0] == sid:
                # Terminal stop of loop route
                s_ref = matcher.total_length
            else:
                s_proj, _, _ = matcher.project_point(stop_obj.x, stop_obj.y)
                # Ensure strictly monotonic stop progression
                s_ref = max(last_s + 10.0, s_proj)

            last_s = s_ref
            stop_progs.append((sid, s_ref))

        return stop_progs

    def detect_stop_events(
        self,
        smoothed_pings: list[dict[str, Any]],
        stop_progs: list[tuple[str, float]],
    ) -> list[dict[str, Any]]:
        """
        Detects arrival, departure, and dwell at each stop in the sequence.
        Returns list of stop event dicts with:
          - stop_id: str
          - arrival_time_sec: float
          - departure_time_sec: float
          - dwell_time_sec: float
          - low_confidence: bool
        """
        if not smoothed_pings or not stop_progs:
            return []

        stop_events: list[dict[str, Any]] = []
        p_times = [p["t_sec"] for p in smoothed_pings]
        p_progs = [p["smoothed_progress_m"] for p in smoothed_pings]
        p_flags = [p.get("low_confidence", False) for p in smoothed_pings]
        N = len(smoothed_pings)

        for stop_idx, (sid, s_stop) in enumerate(stop_progs):
            # Geofence window [s_stop - geofence_m, s_stop + geofence_m]
            s_min = s_stop - self.geofence_m
            s_max = s_stop + self.geofence_m

            # Find all pings inside the geofence
            in_geofence_indices = [
                i for i in range(N) if s_min <= p_progs[i] <= s_max
            ]

            if in_geofence_indices:
                first_i = in_geofence_indices[0]
                last_i = in_geofence_indices[-1]
                t_arr = float(p_times[first_i])
                t_dep = float(p_times[last_i])
                has_low_conf = any(p_flags[i] for i in in_geofence_indices)
            else:
                # Bus traversed through geofence between consecutive pings
                # Find crossing index
                crossing_idx = -1
                for i in range(N - 1):
                    if p_progs[i] <= s_stop <= p_progs[i + 1]:
                        crossing_idx = i
                        break

                if crossing_idx >= 0:
                    t1 = p_times[crossing_idx]
                    t2 = p_times[crossing_idx + 1]
                    s1 = p_progs[crossing_idx]
                    s2 = p_progs[crossing_idx + 1]
                    ds = s2 - s1
                    if ds > 1e-3:
                        frac = (s_stop - s1) / ds
                        t_cross = t1 + frac * (t2 - t1)
                    else:
                        t_cross = float(t1)
                    t_arr = float(t_cross)
                    t_dep = float(t_cross)
                    has_low_conf = p_flags[crossing_idx] or p_flags[crossing_idx + 1]
                else:
                    # Fallback to closest ping
                    closest_i = int(np.argmin([abs(s - s_stop) for s in p_progs]))
                    t_arr = float(p_times[closest_i])
                    t_dep = float(p_times[closest_i])
                    has_low_conf = p_flags[closest_i]

            dwell = max(0.0, t_dep - t_arr)
            stop_events.append({
                "stop_id": sid,
                "arrival_time_sec": round(t_arr, 1),
                "departure_time_sec": round(t_dep, 1),
                "dwell_time_sec": round(dwell, 1),
                "low_confidence": has_low_conf,
            })

        return stop_events

    def extract_segment_times(
        self,
        stop_events: list[dict[str, Any]],
        vehicle_id: str,
        trip_id: str,
        route_id: str,
        day: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Emits segment_times records for consecutive stops in trip:
        (vehicle_id, trip_id, route_id, segment_id, from_stop, to_stop, entry_time_sec, exit_time_sec, duration_sec, quality_flag, day)
        """
        if len(stop_events) < 2:
            return []

        segments: list[dict[str, Any]] = []
        for i in range(len(stop_events) - 1):
            e_from = stop_events[i]
            e_to = stop_events[i + 1]

            from_stop = e_from["stop_id"]
            to_stop = e_to["stop_id"]
            entry_t = e_from["departure_time_sec"]
            exit_t = e_to["arrival_time_sec"]
            duration = max(1.0, exit_t - entry_t)

            low_conf = e_from["low_confidence"] or e_to["low_confidence"]
            quality_flag = "low_confidence" if low_conf else "high_confidence"

            segments.append({
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
                "route_id": route_id,
                "segment_id": f"{from_stop}_{to_stop}",
                "from_stop": from_stop,
                "to_stop": to_stop,
                "entry_time_sec": entry_t,
                "exit_time_sec": exit_t,
                "duration_sec": round(duration, 1),
                "quality_flag": quality_flag,
                "day": day,
            })

        return segments


def extract_trip_stop_events(
    df_trip_pings: pd.DataFrame | list[dict[str, Any]],
    route: Route,
    trip: Trip,
    stops_map: dict[str, Stop],
    geofence_m: float = 25.0,
    day: Optional[int] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Given pings for a single trip, runs:
      1. Map matching on route polyline (with reversal for linear direction 1)
      2. 1D Kalman smoothing
      3. Stop event detection & segment traversal time calculation
    Returns (stop_events, segment_times).
    """
    if route.type == "linear" and trip.direction == 1:
        stop_seq = list(reversed(route.stop_sequence))
        polyline = list(reversed(route.polyline))
    else:
        stop_seq = list(route.stop_sequence)
        polyline = list(route.polyline)

    matched = map_match_pings(df_trip_pings, polyline)
    smoothed = smooth_matched_pings(matched)

    detector = StopEventDetector(geofence_m=geofence_m)
    stop_progs = detector.compute_stop_progresses(stop_seq, polyline, stops_map)
    events = detector.detect_stop_events(smoothed, stop_progs)
    segments = detector.extract_segment_times(
        events,
        vehicle_id=trip.vehicle_id,
        trip_id=trip.trip_id,
        route_id=route.route_id,
        day=day,
    )
    return events, segments
