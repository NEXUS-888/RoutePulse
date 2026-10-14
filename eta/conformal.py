"""
Conformal Calibration & Stale Fallbacks (eta/conformal.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- Split-conformal calibration on Validation split (Days 21-25) to calibrate [q10, q90] to 80% empirical coverage.
- Stale GPS fallback: if GPS stale > 120s, degrade to B1 with widened window.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from core.schemas import EtaPrediction, Trip
from eta.baselines import BaselineB1


def assert_validation_split(
    days: Sequence[int], splits: Optional[Sequence[str]] = None
) -> None:
    """
    Asserts that conformal calibration uses ONLY Validation split (Days 21-25).
    Raises AssertionError if Train (1-20) or Test (26-30) days are detected.
    """
    unique_days = set(days)
    invalid_days = unique_days - set(range(21, 26))
    assert not invalid_days, (
        f"Data leakage detected! Conformal calibration must strictly contain Days 21-25 (Validation split). "
        f"Found forbidden days: {invalid_days}"
    )

    if splits is not None:
        for s in set(splits):
            assert str(s).lower() == "validation", (
                f"Data leakage detected! Split column must strictly be 'validation', got '{s}'"
            )


class ConformalCalibrator:
    """
    Calibrates quantile predictions [q10, q90] to guaranteed 80% coverage
    using split-conformal prediction on the Validation split.
    Handles stale GPS fallback when GPS age exceeds 120 seconds.
    """

    def __init__(self, target_coverage: float = 0.80, stale_gps_threshold_s: float = 120.0):
        self.target_coverage = target_coverage
        self.stale_threshold_s = stale_gps_threshold_s
        self.alpha = 1.0 - target_coverage  # e.g. 0.20 for 80% coverage
        self.q_correction: float = 0.0
        self.is_calibrated: bool = False
        self.b1_fallback = BaselineB1()

    def calibrate(
        self,
        y_true: Sequence[float],
        q10_preds: Sequence[float],
        q90_preds: Sequence[float],
        days: Optional[Sequence[int]] = None,
        splits: Optional[Sequence[str]] = None,
    ) -> float:
        """
        Computes the conformal adjustment Q from calibration residuals on the Validation split.
        Non-conformity score: E_i = max(q10_i - y_i, y_i - q90_i).
        """
        if days is not None:
            assert_validation_split(days, splits)

        y = np.asarray(y_true, dtype=float)
        q10 = np.asarray(q10_preds, dtype=float)
        q90 = np.asarray(q90_preds, dtype=float)

        N = len(y)
        if N == 0:
            self.q_correction = 0.0
            self.is_calibrated = True
            return 0.0

        # Non-conformity scores
        # E_i <= 0 means y_i is inside [q10, q90]
        # E_i > 0 means y_i falls outside the interval by E_i
        scores = np.maximum(q10 - y, y - q90)

        # Finite-sample conformal quantile: ceil((N + 1) * (1 - alpha)) / N
        p_level = min(1.0, math.ceil((N + 1) * (1.0 - self.alpha)) / N)
        self.q_correction = float(np.quantile(scores, p_level, method="higher"))
        self.is_calibrated = True
        return self.q_correction

    def calibrate_interval(
        self,
        q10: float,
        q50: float,
        q90: float,
        query_time_min: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Applies conformal calibration shift to widen or narrow [q10, q90] to target coverage.
        Enforces: query_time <= p10 <= p50 <= p90.
        """
        adj = self.q_correction if self.is_calibrated else 0.0

        p10 = round(max(query_time_min, q10 - adj), 1)
        p50 = round(max(query_time_min, q50), 1)
        p90 = round(max(p50, q90 + adj), 1)
        p10 = round(min(p10, p50), 1)

        return p10, p50, p90

    def adjust_prediction(
        self,
        raw_p10: float,
        raw_p50: float,
        raw_p90: float,
        query_time_min: float,
        trip: Union[Trip, dict[str, Any]],
        target_stop: str,
        current_delay_min: float,
        stops_ahead: int,
        gps_age_s: float = 0.0,
        route_id: Optional[str] = None,
        vehicle_id: Optional[str] = None,
    ) -> EtaPrediction:
        """
        Produces fully calibrated EtaPrediction object, automatically invoking
        the stale GPS fallback if gps_age_s > stale_threshold_s.
        """
        trip_id = trip.trip_id if isinstance(trip, Trip) else trip["trip_id"]
        r_id = route_id or (trip.route_id if isinstance(trip, Trip) else trip["route_id"])
        v_id = vehicle_id or (trip.vehicle_id if isinstance(trip, Trip) else trip["vehicle_id"])
        sched_times = trip.scheduled_stop_times if isinstance(trip, Trip) else trip["scheduled_stop_times"]
        sched_time = int(sched_times.get(target_stop, query_time_min))

        # Check for stale GPS fallback
        if gps_age_s > self.stale_threshold_s:
            # Degrade to B1 with widened window
            b1_p10, b1_p50, b1_p90 = self.b1_fallback.predict(
                trip=trip,
                target_stop=target_stop,
                current_delay_min=current_delay_min,
                stops_ahead=stops_ahead,
                query_time_min=query_time_min,
            )
            # Widen window for stale GPS
            w_extra = 2.5
            p10 = round(max(query_time_min, b1_p10 - w_extra), 1)
            p50 = b1_p50
            p90 = round(b1_p90 + w_extra, 1)

            return EtaPrediction(
                stop_id=target_stop,
                route_id=r_id,
                vehicle_id=v_id,
                trip_id=trip_id,
                scheduled_time_min=sched_time,
                eta_p10_min=p10,
                eta_p50_min=p50,
                eta_p90_min=p90,
                confidence="low",
                reasons=[
                    f"Stale GPS signal (age {int(gps_age_s)}s > {int(self.stale_threshold_s)}s)",
                    "Degraded to B1 last-delay schedule carry-forward with widened interval",
                ],
                stale_gps=True,
            )

        # Normal RoutePulse calibrated prediction
        p10, p50, p90 = self.calibrate_interval(
            raw_p10, raw_p50, raw_p90, query_time_min=query_time_min
        )

        confidence = "high" if stops_ahead <= 2 else "medium"
        reasons = [
            f"RoutePulse ML quantile model (stops ahead: {stops_ahead})",
            f"Conformally calibrated to {int(self.target_coverage * 100)}% coverage window",
        ]

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
            stale_gps=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_coverage": self.target_coverage,
            "stale_threshold_s": self.stale_threshold_s,
            "q_correction": self.q_correction,
            "is_calibrated": self.is_calibrated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConformalCalibrator:
        obj = cls(
            target_coverage=data.get("target_coverage", 0.80),
            stale_gps_threshold_s=data.get("stale_threshold_s", 120.0),
        )
        obj.q_correction = float(data.get("q_correction", 0.0))
        obj.is_calibrated = bool(data.get("is_calibrated", False))
        return obj

    def save(self, path: Union[Path, str]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Union[Path, str]) -> ConformalCalibrator:
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
