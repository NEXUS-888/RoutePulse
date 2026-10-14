"""
Demand Feature Engineering for RoutePulse.
Extracts spatiotemporal, lag, event, and schedule features from demand observations and event logs.
Strictly enforces split boundaries: Days 1-20 (train), Days 21-25 (validation). Never touches Days 26-30.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence
import numpy as np
import pandas as pd


# Default feature column list used for model training and inference
FEATURE_COLUMNS = [
    "stop_code",
    "hour",
    "minute",
    "slot_index",
    "weekday",
    "lag_1d",
    "lag_2d",
    "lag_3d",
    "lag_7d",
    "rolling_mean_3d",
    "class_change_proximity",
    "event_active",
    "event_attendance",
    "minutes_since_event_end",
]

# All 14 campus stops
ALL_STOPS = [f"S{i:02d}" for i in range(1, 15)]
STOP_TO_CODE = {s: i for i, s in enumerate(ALL_STOPS)}


def get_feature_columns() -> list[str]:
    """Returns the ordered list of feature column names used for training."""
    return list(FEATURE_COLUMNS)


def compute_proximity_to_class_change(minute_val: int) -> int:
    """
    Computes circular proximity in minutes to the nearest class-change marker (:00 or :50).
    For a given minute m in [0, 59]:
      - Distance to :00 is min(m, 60 - m)
      - Distance to :50 is min(|m - 50|, 60 - |m - 50|)
    Returns min(dist_to_00, dist_to_50).
    """
    m = int(minute_val) % 60
    dist_00 = min(m, 60 - m)
    dist_50 = min(abs(m - 50), 60 - abs(m - 50))
    return min(dist_00, dist_50)


def load_raw_data(
    demand_path: str | Path = "data/demand_obs.parquet",
    events_path: str | Path = "data/events.csv",
    enforce_split_boundary: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads demand observations and events CSV.
    If enforce_split_boundary is True, asserts that Days 26-30 (test split) are NEVER loaded or touched.
    """
    demand_p = Path(demand_path)
    events_p = Path(events_path)

    if not demand_p.exists():
        raise FileNotFoundError(f"Demand observations not found at: {demand_p}")
    if not events_p.exists():
        raise FileNotFoundError(f"Events CSV not found at: {events_p}")

    df_demand = pd.read_parquet(demand_p)
    df_events = pd.read_csv(events_p)

    if enforce_split_boundary:
        # Strictly reject test days 26-30
        assert "day" in df_demand.columns, "demand_obs must have a 'day' column"
        if (df_demand["day"] > 25).any() or (df_demand.get("split") == "test").any():
            # If the raw file contains days 26-30, immediately filter them out and assert
            df_demand = df_demand[df_demand["day"] <= 25].copy()
            if "split" in df_demand.columns:
                df_demand = df_demand[df_demand["split"] != "test"].copy()

        assert (df_demand["day"] <= 25).all(), (
            "Split violation: Days 26-30 must NEVER be touched during feature engineering or training!"
        )
        if "split" in df_demand.columns:
            assert not (df_demand["split"] == "test").any(), (
                "Split violation: test split rows detected in demand training/validation data!"
            )

    return df_demand, df_events


def extract_features(
    df_demand: Optional[pd.DataFrame] = None,
    df_events: Optional[pd.DataFrame] = None,
    split: Optional[str] = None,
    enforce_split_boundary: bool = True,
    demand_path: str | Path = "data/demand_obs.parquet",
    events_path: str | Path = "data/events.csv",
) -> pd.DataFrame:
    """
    Extracts all demand features from demand observations and event records.

    Features extracted:
      - stop_id: Categorical string / stop code
      - hour: slot_start // 60
      - minute: slot_start % 60
      - slot_index: 15-min slot index within service day (0 to 61)
      - weekday: Day of week (0=Mon ... 6=Sun)
      - lagged same-slot counts (previous days): lag_1d, lag_2d, lag_3d, lag_7d
      - 3-day rolling mean: rolling_mean_3d (of past days)
      - class-change proximity: minutes to :00/:50
      - event active indicator: 1 if active event during slot, 0 otherwise
      - event attendance: attendance of event (float)
      - minutes since event end: minutes elapsed since event end, or -1 if before/none

    Split Boundary Rules:
      - Train split: Days 1-20
      - Validation split: Days 21-25
      - Test split: Days 26-30 (NEVER touched, asserts split IDs)
    """
    if df_demand is None or df_events is None:
        loaded_demand, loaded_events = load_raw_data(
            demand_path=demand_path,
            events_path=events_path,
            enforce_split_boundary=enforce_split_boundary,
        )
        df_demand = loaded_demand if df_demand is None else df_demand
        df_events = loaded_events if df_events is None else df_events

    df = df_demand.copy()

    # Split Boundary Enforcement
    if enforce_split_boundary:
        if (df["day"] > 25).any():
            raise AssertionError(
                "Data leak detected: Days 26-30 must never be touched in demand forecasting! "
                f"Found days: {sorted(df[df['day'] > 25]['day'].unique())}"
            )
        if "split" in df.columns and (df["split"] == "test").any():
            raise AssertionError("Data leak detected: 'test' split rows present in demand data!")

    # Sort deterministically by (stop_id, slot_start, day)
    df = df.sort_values(["stop_id", "slot_start", "day"]).reset_index(drop=True)

    # 1. Spatiotemporal & Calendar Features
    df["stop_code"] = df["stop_id"].map(STOP_TO_CODE).fillna(-1).astype(int)
    df["stop_cat"] = df["stop_id"].astype("category")
    df["hour"] = (df["slot_start"] // 60).astype(int)
    df["minute"] = (df["slot_start"] % 60).astype(int)
    # 15-min slot index within service day (06:30 is 390 min -> slot 0)
    df["slot_index"] = ((df["slot_start"] - 390) // 15).astype(int)
    # Day 1 is Monday (0) -> (day - 1) % 7
    df["weekday"] = ((df["day"] - 1) % 7).astype(int)

    # 2. Class Change Proximity (minutes to :00 or :50)
    df["class_change_proximity"] = df["minute"].apply(compute_proximity_to_class_change).astype(float)

    # 3. Event Features
    event_dict: dict[tuple[int, str], dict] = {}
    if df_events is not None and not df_events.empty:
        for _, row in df_events.iterrows():
            evt_day = int(row["day"])
            evt_venue = str(row["venue_stop_id"])
            event_dict[(evt_day, evt_venue)] = {
                "start_min": int(row["start_min"]),
                "end_min": int(row["end_min"]),
                "attendance": float(row["attendance"]),
            }

    event_active_list: list[int] = []
    event_attendance_list: list[float] = []
    minutes_since_end_list: list[float] = []

    for _, row in df.iterrows():
        key = (int(row["day"]), str(row["stop_id"]))
        slot_s = int(row["slot_start"])
        slot_e = slot_s + 15

        if key in event_dict:
            evt = event_dict[key]
            # Active if slot overlaps [start_min, end_min)
            is_active = 1 if (slot_s < evt["end_min"] and slot_e > evt["start_min"]) else 0
            att = evt["attendance"]
            if slot_s >= evt["end_min"]:
                mins_since = float(slot_s - evt["end_min"])
            else:
                mins_since = -1.0
        else:
            is_active = 0
            att = 0.0
            mins_since = 999.0

        event_active_list.append(is_active)
        event_attendance_list.append(att)
        minutes_since_end_list.append(mins_since)

    df["event_active"] = event_active_list
    df["event_attendance"] = event_attendance_list
    df["minutes_since_event_end"] = minutes_since_end_list

    # 4. Lagged same-slot counts and 3-day rolling mean (strictly causal)
    # Shift operations operate over the sorted day axis per (stop_id, slot_start)
    grouped = df.groupby(["stop_id", "slot_start"])["arrivals"]
    df["lag_1d"] = grouped.shift(1)
    df["lag_2d"] = grouped.shift(2)
    df["lag_3d"] = grouped.shift(3)
    df["lag_7d"] = grouped.shift(7)

    # 3-day rolling mean of previous days (excluding current day)
    df["rolling_mean_3d"] = df.groupby(["stop_id", "slot_start"])["lag_1d"].transform(
        lambda s: s.rolling(window=3, min_periods=1).mean()
    )

    # Calculate prior means strictly from train split (Days 1-20) for imputation
    train_subset = df[df["day"] <= 20]
    train_means_slot = train_subset.groupby(["stop_id", "slot_start"])["arrivals"].mean()
    train_overall_mean = float(train_subset["arrivals"].mean()) if not train_subset.empty else 0.0

    # Fill NaNs on early days (e.g. Day 1) with train baseline priors
    slot_prior_series = pd.Series(
        df.set_index(["stop_id", "slot_start"]).index.map(train_means_slot),
        index=df.index,
    ).fillna(train_overall_mean)

    for col in ["lag_1d", "lag_2d", "lag_3d", "lag_7d", "rolling_mean_3d"]:
        df[col] = df[col].fillna(slot_prior_series).astype(float)

    # 5. Split filtering & validation assertions
    if split == "train":
        df = df[df["day"] <= 20].copy()
        assert (df["day"] >= 1).all() and (df["day"] <= 20).all(), (
            f"Train split must strictly contain Days 1-20. Got days: {sorted(df['day'].unique())}"
        )
    elif split == "validation":
        df = df[(df["day"] >= 21) & (df["day"] <= 25)].copy()
        assert (df["day"] >= 21).all() and (df["day"] <= 25).all(), (
            f"Validation split must strictly contain Days 21-25. Got days: {sorted(df['day'].unique())}"
        )
    else:
        # Default: Days 1-25 only
        assert (df["day"] <= 25).all(), "Data leak: Day > 25 found in feature dataframe"

    return df.reset_index(drop=True)


def prepare_splits(
    demand_path: str | Path = "data/demand_obs.parquet",
    events_path: str | Path = "data/events.csv",
    feature_cols: Optional[Sequence[str]] = None,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Loads data, extracts features, and returns (X_train, y_train, X_val, y_val).
    Strictly enforces split boundaries:
      Train: Days 1-20
      Validation: Days 21-25
    """
    cols = list(feature_cols) if feature_cols is not None else list(FEATURE_COLUMNS)

    df_full = extract_features(
        demand_path=demand_path,
        events_path=events_path,
        enforce_split_boundary=True,
    )

    train_mask = df_full["day"] <= 20
    val_mask = (df_full["day"] >= 21) & (df_full["day"] <= 25)

    # Validate split invariants
    train_days = set(df_full.loc[train_mask, "day"].unique())
    val_days = set(df_full.loc[val_mask, "day"].unique())
    assert train_days == set(range(1, 21)), f"Train days mismatch: {train_days}"
    assert val_days == set(range(21, 26)), f"Validation days mismatch: {val_days}"
    assert not any(d > 25 for d in train_days | val_days), "Days 26-30 must never be touched!"

    X_train = df_full.loc[train_mask, cols].copy()
    y_train = df_full.loc[train_mask, "arrivals"].astype(float).copy()

    X_val = df_full.loc[val_mask, cols].copy()
    y_val = df_full.loc[val_mask, "arrivals"].astype(float).copy()

    return X_train, y_train, X_val, y_val
