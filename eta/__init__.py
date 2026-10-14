"""
RoutePulse ETA Prediction Engine
"""
from __future__ import annotations

from eta.gps_processing import (
    PolylineMatcher,
    KalmanSmoother1D,
    StopEventDetector,
    map_match_pings,
    smooth_matched_pings,
    extract_trip_stop_events,
)
from eta.baselines import (
    BaselineB0,
    BaselineB1,
)
from eta.profiles import (
    HistoricalProfiles,
    day_to_day_type,
)
from eta.live import (
    OnlineDelayTracker,
    predict_dwell_time_sec,
    predict_dwell_time_min,
)
from eta.model import (
    EtaResidualModel,
    assert_train_split,
)
from eta.conformal import (
    ConformalCalibrator,
    assert_validation_split,
)
from eta.engine import (
    RoutePulseETA,
    compute_eta_metrics,
)

__all__ = [
    "PolylineMatcher",
    "KalmanSmoother1D",
    "StopEventDetector",
    "map_match_pings",
    "smooth_matched_pings",
    "extract_trip_stop_events",
    "BaselineB0",
    "BaselineB1",
    "HistoricalProfiles",
    "day_to_day_type",
    "OnlineDelayTracker",
    "predict_dwell_time_sec",
    "predict_dwell_time_min",
    "EtaResidualModel",
    "assert_train_split",
    "ConformalCalibrator",
    "assert_validation_split",
    "RoutePulseETA",
    "compute_eta_metrics",
]
