"""
Real-time Demand Nowcasting for RoutePulse.
Implements real-time multiplier correction:
  m = (observed last 30 min + eps) / (predicted last 30 min + eps)
clipped to [0.7, 1.8], decaying toward 1.0 over the next 60 minutes.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence, Union
import numpy as np
import pandas as pd


def compute_multiplier(
    observed_30m: float,
    predicted_30m: float,
    eps: float = 1e-3,
    min_clip: float = 0.7,
    max_clip: float = 1.8,
) -> float:
    """
    Computes the real-time demand correction multiplier:
      m = (observed last 30 min + eps) / (predicted last 30 min + eps)
    clipped to [min_clip, max_clip] (default [0.7, 1.8]).
    """
    obs = max(0.0, float(observed_30m))
    pred = max(0.0, float(predicted_30m))
    raw_m = (obs + eps) / (pred + eps)
    clipped_m = max(min_clip, min(max_clip, raw_m))
    return float(clipped_m)


def decay_multiplier(
    multiplier: float,
    lead_time_min: float,
    decay_horizon_min: float = 60.0,
) -> float:
    """
    Decays the multiplier toward 1.0 over the forecast horizon (default 60 minutes).
    For lead_time <= 0: returns full multiplier.
    For lead_time >= decay_horizon: returns 1.0.
    For 0 < lead_time < decay_horizon: linearly interpolates:
      m(t) = 1.0 + (m - 1.0) * (1.0 - lead_time / decay_horizon)
    """
    if lead_time_min <= 0.0:
        return float(multiplier)
    if lead_time_min >= decay_horizon_min:
        return 1.0

    weight = 1.0 - (float(lead_time_min) / float(decay_horizon_min))
    decayed = 1.0 + (float(multiplier) - 1.0) * weight
    return float(decayed)


class NowcastCorrector:
    """
    Manages nowcast correction for demand forecasts based on recent observed telemetry.
    """

    def __init__(
        self,
        eps: float = 1e-3,
        min_clip: float = 0.7,
        max_clip: float = 1.8,
        decay_horizon_min: float = 60.0,
    ):
        self.eps = eps
        self.min_clip = min_clip
        self.max_clip = max_clip
        self.decay_horizon_min = decay_horizon_min

    def compute_multiplier(self, observed_30m: float, predicted_30m: float) -> float:
        """Calculates clipped multiplier for the past 30-min window."""
        return compute_multiplier(
            observed_30m=observed_30m,
            predicted_30m=predicted_30m,
            eps=self.eps,
            min_clip=self.min_clip,
            max_clip=self.max_clip,
        )

    def get_decayed_multiplier(self, multiplier: float, lead_time_min: float) -> float:
        """Returns the decayed multiplier at the specified lead time."""
        return decay_multiplier(
            multiplier=multiplier,
            lead_time_min=lead_time_min,
            decay_horizon_min=self.decay_horizon_min,
        )

    def correct_value(
        self,
        predicted_value: float,
        lead_time_min: float,
        multiplier: float,
    ) -> float:
        """Applies decayed multiplier to a single predicted mean value."""
        m_decayed = self.get_decayed_multiplier(multiplier, lead_time_min)
        return float(max(0.0, predicted_value * m_decayed))

    def correct_bands(
        self,
        p50: float,
        p80: float,
        p90: float,
        lead_time_min: float,
        multiplier: float,
    ) -> tuple[float, float, float]:
        """
        Applies decayed multiplier to quantile bands, strictly guaranteeing monotonicity:
        P50 <= P80 <= P90.
        """
        m_decayed = self.get_decayed_multiplier(multiplier, lead_time_min)
        adj_50 = max(0.0, p50 * m_decayed)
        adj_80 = max(adj_50, p80 * m_decayed)
        adj_90 = max(adj_80, p90 * m_decayed)
        return float(adj_50), float(adj_80), float(adj_90)

    def correct_dataframe(
        self,
        df: pd.DataFrame,
        current_time_min: int,
        observed_30m: float,
        predicted_30m: float,
        slot_col: str = "slot_start",
    ) -> pd.DataFrame:
        """
        Applies nowcast correction to a DataFrame of future slot forecasts.
        """
        df_out = df.copy()
        m = self.compute_multiplier(observed_30m, predicted_30m)

        lead_times = (df_out[slot_col] - current_time_min).astype(float)
        decayed_mults = lead_times.apply(lambda lt: self.get_decayed_multiplier(m, lt))

        if "mean" in df_out.columns:
            df_out["mean"] = np.maximum(0.0, df_out["mean"] * decayed_mults)

        for q in ["p50", "p80", "p90"]:
            if q in df_out.columns:
                df_out[q] = np.maximum(0.0, df_out[q] * decayed_mults)

        # Ensure monotonicity
        if "p50" in df_out.columns and "p80" in df_out.columns:
            df_out["p80"] = np.maximum(df_out["p80"], df_out["p50"])
        if "p80" in df_out.columns and "p90" in df_out.columns:
            df_out["p90"] = np.maximum(df_out["p90"], df_out["p80"])

        df_out["nowcast_multiplier"] = decayed_mults
        return df_out
