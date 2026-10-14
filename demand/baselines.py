"""
Historical Baseline Models for RoutePulse Demand Forecasting.
Implements the historical mean baseline per (stop_id, slot, weekday) with event multiplier fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, Sequence
import numpy as np
import pandas as pd


class HistoricalBaseline:
    """
    Historical mean baseline predictor.
    Predicts mean arrivals per (stop_id, slot_start, weekday).
    Provides fallbacks to (stop_id, slot_start), stop_id, and global mean.
    Applies event multiplier fallback when events are active or during post-event outflow.
    """

    def __init__(self, default_event_multiplier: float = 2.0):
        self.default_event_multiplier = default_event_multiplier
        self.stop_slot_weekday_means: dict[tuple[str, int, int], float] = {}
        self.stop_slot_means: dict[tuple[str, int], float] = {}
        self.stop_means: dict[str, float] = {}
        self.global_mean: float = 0.0
        self.is_fitted: bool = False
        self.event_multiplier: float = default_event_multiplier

    def fit(self, df_train: pd.DataFrame, df_events: Optional[pd.DataFrame] = None) -> HistoricalBaseline:
        """
        Fits baseline tables strictly on training data (Days 1-20).
        """
        df = df_train.copy()

        # Strict split boundary check
        if "day" in df.columns:
            assert (df["day"] <= 20).all(), (
                f"Historical baseline must only be fit on train split (Days 1-20). Max day: {df['day'].max()}"
            )
        if "split" in df.columns:
            assert not (df["split"] == "test").any() and not (df["split"] == "validation").any(), (
                "Historical baseline can only be fit on training split!"
            )

        if "weekday" not in df.columns and "day" in df.columns:
            df["weekday"] = ((df["day"] - 1) % 7).astype(int)

        # 1. Primary table: (stop_id, slot_start, weekday)
        grp_primary = df.groupby(["stop_id", "slot_start", "weekday"])["arrivals"].mean()
        self.stop_slot_weekday_means = {
            (str(k[0]), int(k[1]), int(k[2])): float(v) for k, v in grp_primary.items()
        }

        # 2. Fallback table 1: (stop_id, slot_start)
        grp_slot = df.groupby(["stop_id", "slot_start"])["arrivals"].mean()
        self.stop_slot_means = {
            (str(k[0]), int(k[1])): float(v) for k, v in grp_slot.items()
        }

        # 3. Fallback table 2: stop_id
        grp_stop = df.groupby("stop_id")["arrivals"].mean()
        self.stop_means = {str(k): float(v) for k, v in grp_stop.items()}

        # 4. Global mean
        self.global_mean = float(df["arrivals"].mean()) if not df.empty else 0.0

        # Calibrate event multiplier from training events if event features or events df are available
        if "event_active" in df.columns and (df["event_active"] == 1).any():
            event_mean = float(df[df["event_active"] == 1]["arrivals"].mean())
            non_event_mean = float(df[df["event_active"] == 0]["arrivals"].mean())
            if non_event_mean > 0:
                self.event_multiplier = max(1.2, min(5.0, event_mean / non_event_mean))
        else:
            self.event_multiplier = self.default_event_multiplier

        self.is_fitted = True
        return self

    def predict_row(
        self,
        stop_id: str,
        slot_start: int,
        weekday: int,
        event_active: int = 0,
        minutes_since_event_end: float = 999.0,
    ) -> float:
        """Predict arrivals for a single stop, slot, and weekday."""
        if not self.is_fitted:
            raise RuntimeError("HistoricalBaseline must be fit before predict()")

        key_primary = (str(stop_id), int(slot_start), int(weekday))
        if key_primary in self.stop_slot_weekday_means:
            base_pred = self.stop_slot_weekday_means[key_primary]
        elif (str(stop_id), int(slot_start)) in self.stop_slot_means:
            base_pred = self.stop_slot_means[(str(stop_id), int(slot_start))]
        elif str(stop_id) in self.stop_means:
            base_pred = self.stop_means[str(stop_id)]
        else:
            base_pred = self.global_mean

        # Apply event multiplier fallback if active event or recent outflow
        if event_active == 1:
            base_pred *= self.event_multiplier
        elif 0.0 <= minutes_since_event_end <= 45.0:
            # Post-event outflow surge
            decay = max(0.0, 1.0 - minutes_since_event_end / 45.0)
            mult = 1.0 + (self.event_multiplier - 1.0) * decay
            base_pred *= mult

        return float(base_pred)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Vectorized or row-wise prediction on input dataframe."""
        if not self.is_fitted:
            raise RuntimeError("HistoricalBaseline must be fit before predict()")

        df_in = df.copy()
        if "weekday" not in df_in.columns and "day" in df_in.columns:
            df_in["weekday"] = ((df_in["day"] - 1) % 7).astype(int)

        stop_ids = df_in["stop_id"].astype(str).values
        slot_starts = df_in["slot_start"].astype(int).values
        weekdays = df_in["weekday"].astype(int).values

        event_active = (
            df_in["event_active"].astype(int).values
            if "event_active" in df_in.columns
            else np.zeros(len(df_in), dtype=int)
        )
        minutes_since_end = (
            df_in["minutes_since_event_end"].astype(float).values
            if "minutes_since_event_end" in df_in.columns
            else np.full(len(df_in), 999.0, dtype=float)
        )

        preds = np.zeros(len(df_in), dtype=float)
        for i in range(len(df_in)):
            preds[i] = self.predict_row(
                stop_id=stop_ids[i],
                slot_start=slot_starts[i],
                weekday=weekdays[i],
                event_active=event_active[i],
                minutes_since_event_end=minutes_since_end[i],
            )

        return preds


# Alias
HistoricalMeanBaseline = HistoricalBaseline
