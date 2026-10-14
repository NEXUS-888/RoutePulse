"""
RoutePulse ETA Prediction Engine (eta/engine.py)
Unified interface combining HistoricalProfiles, OnlineDelayTracker,
LightGBM Quantile Residual Model, Conformal Calibration, and Baselines.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from core.schemas import EtaPrediction, Route, Stop, Trip
from eta.baselines import BaselineB0, BaselineB1
from eta.conformal import ConformalCalibrator
from eta.live import OnlineDelayTracker, compute_base_eta
from eta.model import EtaResidualModel
from eta.profiles import HistoricalProfiles, day_to_day_type

logger = logging.getLogger(__name__)
DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "data" / "eta_artifacts"


class RoutePulseETA:
    """
    High-level ETA Engine for RoutePulse.
    Coordinates historical profiles, online delay EWMA, quantile residual ML,
    and split-conformal calibration with stale GPS fallback.
    """

    def __init__(self, artifacts_dir: Union[Path, str] = DEFAULT_ARTIFACTS_DIR):
        p = Path(artifacts_dir)
        self.artifacts_dir = p

        # Load models or initialize defaults
        if (p / "profiles.json").exists():
            self.profiles = HistoricalProfiles.load(p / "profiles.json")
        else:
            self.profiles = HistoricalProfiles()

        if (p / "eta_residual_model.joblib").exists():
            self.model = EtaResidualModel.load(p)
        else:
            self.model = EtaResidualModel()

        if (p / "conformal_calibration.json").exists():
            self.calibrator = ConformalCalibrator.load(p / "conformal_calibration.json")
        else:
            self.calibrator = ConformalCalibrator(target_coverage=0.80)

        self.b0 = BaselineB0()
        self.b1 = BaselineB1()

    def predict_downstream_etas(
        self,
        trip: Trip,
        route: Route,
        current_stop_id: str,
        query_time_min: float,
        current_delay_min: float = 0.0,
        rho: float = 1.0,
        vehicle_load: float = 15.0,
        day: int = 1,
        gps_age_s: float = 0.0,
    ) -> list[EtaPrediction]:
        """
        Produces conformally-calibrated ETA predictions for all remaining downstream stops.
        Guarantees:
          - Monotonicity: ETA(S_i) <= ETA(S_{i+1})
          - No NaNs or infinities
          - query_time_min <= p10 <= p50 <= p90
          - Degrades to B1 if gps_age_s > 120s
        """
        # Determine stops order
        if route.type == "linear" and trip.direction == 1:
            seq = list(reversed(route.stop_sequence))
        else:
            seq = list(route.stop_sequence)

        if current_stop_id not in seq:
            return []

        curr_idx = seq.index(current_stop_id)
        downstream_stops = seq[curr_idx + 1:]
        if not downstream_stops:
            return []

        predictions: list[EtaPrediction] = []
        last_p50 = query_time_min

        for idx, target_stop in enumerate(downstream_stops):
            stops_ahead = idx + 1

            if gps_age_s > self.calibrator.stale_threshold_s:
                # Stale fallback to B1
                pred = self.calibrator.adjust_prediction(
                    raw_p10=0.0,
                    raw_p50=0.0,
                    raw_p90=0.0,
                    query_time_min=query_time_min,
                    trip=trip,
                    target_stop=target_stop,
                    current_delay_min=current_delay_min,
                    stops_ahead=stops_ahead,
                    gps_age_s=gps_age_s,
                    route_id=route.route_id,
                    vehicle_id=trip.vehicle_id,
                )
            else:
                # Base Profile + Live
                base_eta, _, _ = compute_base_eta(
                    trip=trip,
                    route=route,
                    current_stop_id=current_stop_id,
                    target_stop_id=target_stop,
                    query_time_min=query_time_min,
                    profiles=self.profiles,
                    day=day,
                    rho=rho,
                )

                time_bucket = int(query_time_min // 15)
                weekday = day % 7

                raw_p10, raw_p50, raw_p90 = self.model.predict_eta(
                    base_eta_min=base_eta,
                    remaining_stops=stops_ahead,
                    time_bucket=time_bucket,
                    current_delay_min=current_delay_min,
                    rho=rho,
                    vehicle_load=vehicle_load,
                    weekday=weekday,
                    query_time_min=query_time_min,
                )

                pred = self.calibrator.adjust_prediction(
                    raw_p10=raw_p10,
                    raw_p50=raw_p50,
                    raw_p90=raw_p90,
                    query_time_min=query_time_min,
                    trip=trip,
                    target_stop=target_stop,
                    current_delay_min=current_delay_min,
                    stops_ahead=stops_ahead,
                    gps_age_s=gps_age_s,
                    route_id=route.route_id,
                    vehicle_id=trip.vehicle_id,
                )

            # Enforce downstream monotonicity across stops
            final_p50 = max(last_p50, pred.eta_p50_min)
            final_p10 = max(query_time_min, min(pred.eta_p10_min, final_p50))
            final_p90 = max(final_p50, pred.eta_p90_min)
            last_p50 = final_p50

            pred.eta_p10_min = round(final_p10, 1)
            pred.eta_p50_min = round(final_p50, 1)
            pred.eta_p90_min = round(final_p90, 1)

            predictions.append(pred)

        return predictions


def compute_eta_metrics(
    y_true: Sequence[float],
    p10: Sequence[float],
    p50: Sequence[float],
    p90: Sequence[float],
    alpha: float = 0.20,
) -> dict[str, float]:
    """
    Computes standard RoutePulse ETA metrics:
      - MAE (min)
      - Median AE (min)
      - Window Coverage (%)
      - Mean Window Width (min)
      - Winkler Interval Score
    """
    y = np.asarray(y_true, dtype=float)
    y_p10 = np.asarray(p10, dtype=float)
    y_p50 = np.asarray(p50, dtype=float)
    y_p90 = np.asarray(p90, dtype=float)

    errors = np.abs(y - y_p50)
    mae = float(np.mean(errors))
    med_ae = float(np.median(errors))

    covered = (y >= y_p10) & (y <= y_p90)
    coverage = float(np.mean(covered))

    widths = y_p90 - y_p10
    mean_width = float(np.mean(widths))

    # Winkler Interval Score for 1 - alpha interval (e.g. 80%, alpha = 0.2)
    # Score = (U - L) + (2 / alpha) * (L - y) * I(y < L) + (2 / alpha) * (y - U) * I(y > U)
    penalty_factor = 2.0 / alpha
    lower_penalties = penalty_factor * np.maximum(0.0, y_p10 - y)
    upper_penalties = penalty_factor * np.maximum(0.0, y - y_p90)
    winkler_scores = widths + lower_penalties + upper_penalties
    mean_winkler = float(np.mean(winkler_scores))

    # % late by > 3 min
    pct_late_3m = float(np.mean((y - y_p50) > 3.0)) * 100.0

    return {
        "MAE_min": round(mae, 3),
        "MedAE_min": round(med_ae, 3),
        "Coverage_pct": round(coverage * 100.0, 1),
        "MeanWidth_min": round(mean_width, 2),
        "WinklerScore": round(mean_winkler, 2),
        "LateOver3Min_pct": round(pct_late_3m, 1),
    }
