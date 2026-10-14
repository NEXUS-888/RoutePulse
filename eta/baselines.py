"""
ETA Baseline Predictors (eta/baselines.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- B0: Timetable ETA (scheduled arrival time)
- B1: Last-delay carry-forward (scheduled arrival time + current observed delay)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from core.schemas import EtaPrediction, Trip


class BaselineB0:
    """
    B0 Baseline: Timetable ETA.
    Predicts the scheduled timetable arrival time for any downstream stop.
    Window is fixed timetable spread (+/- 2.0 min).
    """

    def __init__(self, default_window_half_width: float = 2.0):
        self.default_half_width = default_window_half_width

    def predict(
        self,
        trip: Union[Trip, dict[str, Any]],
        target_stop: str,
        query_time_min: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Returns (eta_p10, eta_p50, eta_p90) in minutes from midnight.
        """
        sched_times = trip.scheduled_stop_times if isinstance(trip, Trip) else trip["scheduled_stop_times"]
        sched_time = float(sched_times.get(target_stop, query_time_min))

        eta_p50 = round(max(query_time_min, sched_time), 1)
        eta_p10 = round(max(query_time_min, eta_p50 - self.default_half_width), 1)
        eta_p90 = round(eta_p50 + self.default_half_width, 1)

        return eta_p10, eta_p50, eta_p90

    def predict_prediction_obj(
        self,
        trip: Union[Trip, dict[str, Any]],
        target_stop: str,
        query_time_min: float,
        route_id: Optional[str] = None,
        vehicle_id: Optional[str] = None,
    ) -> EtaPrediction:
        """Constructs a validated Pydantic EtaPrediction object."""
        trip_id = trip.trip_id if isinstance(trip, Trip) else trip["trip_id"]
        r_id = route_id or (trip.route_id if isinstance(trip, Trip) else trip["route_id"])
        v_id = vehicle_id or (trip.vehicle_id if isinstance(trip, Trip) else trip["vehicle_id"])
        sched_times = trip.scheduled_stop_times if isinstance(trip, Trip) else trip["scheduled_stop_times"]
        sched_time = int(sched_times.get(target_stop, query_time_min))

        p10, p50, p90 = self.predict(trip, target_stop, query_time_min)
        return EtaPrediction(
            stop_id=target_stop,
            route_id=r_id,
            vehicle_id=v_id,
            trip_id=trip_id,
            scheduled_time_min=sched_time,
            eta_p10_min=p10,
            eta_p50_min=p50,
            eta_p90_min=p90,
            confidence="medium",
            reasons=["B0: Timetable scheduled arrival"],
            stale_gps=False,
        )


class BaselineB1:
    """
    B1 Baseline: Last-delay carry-forward.
    Predicts scheduled arrival time + current observed delay.
    Window widens linearly with downstream stop count (+/- (1.0 + 0.5 * stops_ahead) min).
    """

    def __init__(self, base_half_width: float = 1.0, slope_per_stop: float = 0.5):
        self.base_half_width = base_half_width
        self.slope_per_stop = slope_per_stop

    def predict(
        self,
        trip: Union[Trip, dict[str, Any]],
        target_stop: str,
        current_delay_min: float,
        stops_ahead: int = 1,
        query_time_min: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Returns (eta_p10, eta_p50, eta_p90) in minutes from midnight.
        """
        sched_times = trip.scheduled_stop_times if isinstance(trip, Trip) else trip["scheduled_stop_times"]
        sched_time = float(sched_times.get(target_stop, query_time_min))

        eta_p50 = round(max(query_time_min, sched_time + current_delay_min), 1)
        spread = self.base_half_width + self.slope_per_stop * max(0, stops_ahead)
        eta_p10 = round(max(query_time_min, eta_p50 - spread), 1)
        eta_p90 = round(eta_p50 + spread, 1)

        return eta_p10, eta_p50, eta_p90

    def predict_prediction_obj(
        self,
        trip: Union[Trip, dict[str, Any]],
        target_stop: str,
        current_delay_min: float,
        stops_ahead: int,
        query_time_min: float,
        route_id: Optional[str] = None,
        vehicle_id: Optional[str] = None,
        stale_gps: bool = False,
    ) -> EtaPrediction:
        """Constructs a validated Pydantic EtaPrediction object."""
        trip_id = trip.trip_id if isinstance(trip, Trip) else trip["trip_id"]
        r_id = route_id or (trip.route_id if isinstance(trip, Trip) else trip["route_id"])
        v_id = vehicle_id or (trip.vehicle_id if isinstance(trip, Trip) else trip["vehicle_id"])
        sched_times = trip.scheduled_stop_times if isinstance(trip, Trip) else trip["scheduled_stop_times"]
        sched_time = int(sched_times.get(target_stop, query_time_min))

        p10, p50, p90 = self.predict(
            trip, target_stop, current_delay_min, stops_ahead=stops_ahead, query_time_min=query_time_min
        )

        reasons = [f"B1: Schedule + observed delay ({current_delay_min:+.1f} min)"]
        confidence = "high" if stops_ahead <= 2 and not stale_gps else "medium"

        if stale_gps:
            confidence = "low"
            # Widen window for stale GPS fallback
            extra_w = 2.0
            p10 = round(max(query_time_min, p10 - extra_w), 1)
            p90 = round(p90 + extra_w, 1)
            reasons.append("GPS signal stale (> 120s); widened uncertainty window")

        return EtaPrediction(
            stop_id=target_stop,
            route_id=r_id,
            vehicle_id=v_id,
            trip_id=trip_id,
            scheduled_time_min=sched_time,
            eta_p10_min=p10,
            eta_p50_min=p50,
            eta_p90_min=p90,
            confidence=confidence,
            reasons=reasons,
            stale_gps=stale_gps,
        )
