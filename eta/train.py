"""
ETA Training & Calibration Pipeline (eta/train.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- Orchestrates:
  1. Processing GPS pings into segment_times & stop_events for Train split (Days 1-20).
  2. Fitting historical segment travel-time profiles (HistoricalProfiles).
  3. Generating residual feature dataset and fitting LightGBM quantile regressors ([0.1, 0.5, 0.9]).
  4. Performing split-conformal calibration on Validation split (Days 21-25) for 80% coverage.
  5. Saving model artifacts and printing validation summary.
- STRICT SPLIT INTEGRITY: Asserts that training ONLY touches Days 1-20, and NEVER touches Test split (Days 26-30).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from core.io import load_json, save_json
from core.schemas import ApcRecord, Plan, Route, Stop, Trip
from eta.baselines import BaselineB0, BaselineB1
from eta.conformal import ConformalCalibrator, assert_validation_split
from eta.gps_processing import extract_trip_stop_events
from eta.live import OnlineDelayTracker, compute_base_eta
from eta.model import EtaResidualModel, assert_train_split
from eta.profiles import HistoricalProfiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTIFACTS_DIR = DATA_DIR / "eta_artifacts"


def load_inputs(data_dir: Path = DATA_DIR) -> tuple[dict[str, Stop], dict[str, Route], Plan, pd.DataFrame, pd.DataFrame]:
    """Loads network definition, baseline plan, GPS pings, and APC records."""
    net_json = load_json(data_dir / "network.json")
    stops = {s["stop_id"]: Stop(**s) for s in net_json["stops"]}
    routes = {r["route_id"]: Route(**r) for r in net_json["routes"]}

    plan_json = load_json(data_dir / "baseline_plan.json")
    plan = Plan(**plan_json)

    df_pings = pd.read_parquet(data_dir / "gps_pings.parquet")
    df_apc = pd.read_parquet(data_dir / "apc_records.parquet")

    return stops, routes, plan, df_pings, df_apc


def extract_split_events_and_segments(
    days: list[int],
    df_pings: pd.DataFrame,
    routes: dict[str, Route],
    stops: dict[str, Stop],
    plan: Plan,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Processes GPS traces for specified days into stop events and segment times.
    """
    all_stop_events: list[dict[str, Any]] = []
    all_segment_times: list[dict[str, Any]] = []

    # Filter pings for target days
    pings_subset = df_pings[df_pings["day"].isin(days)].copy()

    for day in days:
        day_pings = pings_subset[pings_subset["day"] == day]
        if day_pings.empty:
            continue

        for trip in plan.trips:
            r = routes[trip.route_id]
            t_start = trip.departure_min * 60 - 30
            # Latest scheduled stop plus buffer
            last_sched_min = list(trip.scheduled_stop_times.values())[-1]
            t_end = last_sched_min * 60 + 180

            tpings = day_pings[
                (day_pings["vehicle_id"] == trip.vehicle_id)
                & (day_pings["t_sec"] >= t_start)
                & (day_pings["t_sec"] <= t_end)
            ]

            if len(tpings) >= 2:
                events, segs = extract_trip_stop_events(
                    df_trip_pings=tpings,
                    route=r,
                    trip=trip,
                    stops_map=stops,
                    day=day,
                )
                for e in events:
                    e["trip_id"] = trip.trip_id
                    e["vehicle_id"] = trip.vehicle_id
                    e["route_id"] = trip.route_id
                    e["direction"] = trip.direction
                    e["day"] = day
                all_stop_events.extend(events)
                all_segment_times.extend(segs)

    return all_stop_events, all_segment_times


def build_residual_dataset(
    days: list[int],
    stop_events: list[dict[str, Any]],
    routes: dict[str, Route],
    plan: Plan,
    profiles: HistoricalProfiles,
    df_apc: pd.DataFrame,
    split_name: str = "train",
) -> pd.DataFrame:
    """
    Builds training or validation feature rows with residual targets:
    residual_min = actual_arrival_min - base_eta_min.
    """
    trip_map = {t.trip_id: t for t in plan.trips}

    # Group stop events by (day, trip_id)
    events_df = pd.DataFrame(stop_events)
    if events_df.empty:
        return pd.DataFrame()

    # Pre-index APC load by (day, trip_id, stop_id)
    apc_map: dict[tuple[int, str, str], int] = {}
    if not df_apc.empty and "load_after" in df_apc.columns:
        for _, row in df_apc.iterrows():
            apc_map[(int(row["day"]), str(row["trip_id"]), str(row["stop_id"]))] = int(row["load_after"])

    rows: list[dict[str, Any]] = []

    for (day, trip_id), grp in events_df.groupby(["day", "trip_id"]):
        if trip_id not in trip_map:
            continue
        trip = trip_map[trip_id]
        r = routes[trip.route_id]
        grp_sorted = grp.sort_values("arrival_time_sec").reset_index(drop=True)
        K = len(grp_sorted)
        if K < 2:
            continue

        tracker = OnlineDelayTracker()

        for i in range(K - 1):
            curr_row = grp_sorted.iloc[i]
            curr_stop = curr_row["stop_id"]
            curr_dep_sec = curr_row["departure_time_sec"]
            curr_dep_min = curr_dep_sec / 60.0

            # Scheduled departure / arrival at current stop
            sched_curr_min = trip.scheduled_stop_times.get(curr_stop, trip.departure_min)
            current_delay_min = curr_dep_min - sched_curr_min

            # Update tracker if previous segment exists
            if i > 0:
                prev_row = grp_sorted.iloc[i - 1]
                prev_seg = f"{prev_row['stop_id']}_{curr_stop}"
                obs_dur = curr_row["arrival_time_sec"] - prev_row["departure_time_sec"]
                exp_dur, _ = profiles.get_segment_time(prev_seg, prev_row["departure_time_sec"] / 60.0, day=day)
                tracker.update(prev_seg, obs_dur, exp_dur)

            current_rho = tracker.get_rho()
            current_load = apc_map.get((day, trip_id, curr_stop), 15)

            # Generate target predictions for all downstream stops
            for j in range(i + 1, K):
                target_row = grp_sorted.iloc[j]
                target_stop = target_row["stop_id"]
                actual_arr_min = target_row["arrival_time_sec"] / 60.0

                base_eta, _, stops_ahead = compute_base_eta(
                    trip=trip,
                    route=r,
                    current_stop_id=curr_stop,
                    target_stop_id=target_stop,
                    query_time_min=curr_dep_min,
                    profiles=profiles,
                    day=day,
                    rho=current_rho,
                )

                residual = actual_arr_min - base_eta
                time_bucket = int(curr_dep_min // 15)
                weekday = day % 7

                rows.append({
                    "day": int(day),
                    "split": split_name,
                    "trip_id": trip_id,
                    "route_id": trip.route_id,
                    "vehicle_id": trip.vehicle_id,
                    "current_stop": curr_stop,
                    "target_stop": target_stop,
                    "query_time_min": round(curr_dep_min, 2),
                    "actual_arrival_min": round(actual_arr_min, 2),
                    "base_eta_min": round(base_eta, 2),
                    "residual_min": round(residual, 2),
                    "remaining_stops": stops_ahead,
                    "time_bucket": time_bucket,
                    "current_delay_min": round(current_delay_min, 2),
                    "rho": round(current_rho, 3),
                    "vehicle_load": float(current_load),
                    "weekday": weekday,
                })

    return pd.DataFrame(rows)


def train_pipeline(
    data_dir: Path = DATA_DIR,
    artifacts_dir: Path = ARTIFACTS_DIR,
    train_days: list[int] = list(range(1, 21)),
    val_days: list[int] = list(range(21, 26)),
) -> tuple[HistoricalProfiles, EtaResidualModel, ConformalCalibrator]:
    """
    Main training execution function.
    Fits historical profiles, trains residual models, calibrates conformal intervals, and saves artifacts.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Starting RoutePulse ETA Training Pipeline...")

    # Strict isolation checks
    assert_train_split(train_days)
    assert_validation_split(val_days)

    stops, routes, plan, df_pings, df_apc = load_inputs(data_dir)

    # 1. Extract GPS Stop Events & Segments for Train Split (Days 1-20)
    logger.info(f"[1/5] Extracting stop events and segment times for Train Split (Days {min(train_days)}..{max(train_days)})...")
    train_events, train_segs = extract_split_events_and_segments(
        days=train_days,
        df_pings=df_pings,
        routes=routes,
        stops=stops,
        plan=plan,
    )
    df_train_segs = pd.DataFrame(train_segs)
    logger.info(f"  -> Extracted {len(train_segs):,} segment traversal records from Train split.")

    # 2. Fit Historical Profiles on Train Split
    logger.info("[2/5] Fitting HistoricalProfiles with shrinkage on Train split...")
    profiles = HistoricalProfiles(slot_size_min=15, shrinkage_lambda_seg=5.0, shrinkage_lambda_route=10.0)
    profiles.fit(df_train_segs)
    profiles.save(artifacts_dir / "profiles.json")
    logger.info(f"  -> Saved historical profiles to {artifacts_dir / 'profiles.json'}")

    # 3. Build Residual Feature Set & Train LightGBM Quantile Models on Train Split
    logger.info("[3/5] Building residual training set and fitting LightGBM quantile regression [0.1, 0.5, 0.9]...")
    df_train_residuals = build_residual_dataset(
        days=train_days,
        stop_events=train_events,
        routes=routes,
        plan=plan,
        profiles=profiles,
        df_apc=df_apc,
        split_name="train",
    )
    logger.info(f"  -> Generated {len(df_train_residuals):,} training feature records.")

    # Strict check before training
    assert_train_split(df_train_residuals["day"].tolist(), df_train_residuals["split"].tolist())
    model = EtaResidualModel(quantiles=(0.1, 0.5, 0.9), n_estimators=80, learning_rate=0.05)
    model.fit(df_train_residuals)
    model.save(artifacts_dir)
    logger.info(f"  -> Saved quantile regression model to {artifacts_dir / 'eta_residual_model.joblib'}")

    # 4. Extract Validation Split (Days 21-25) & Conformal Calibration
    logger.info(f"[4/5] Extracting Validation Split (Days {min(val_days)}..{max(val_days)}) for Conformal Calibration...")
    val_events, _ = extract_split_events_and_segments(
        days=val_days,
        df_pings=df_pings,
        routes=routes,
        stops=stops,
        plan=plan,
    )
    df_val_residuals = build_residual_dataset(
        days=val_days,
        stop_events=val_events,
        routes=routes,
        plan=plan,
        profiles=profiles,
        df_apc=df_apc,
        split_name="validation",
    )
    logger.info(f"  -> Generated {len(df_val_residuals):,} validation feature records.")

    # Strict check before validation calibration
    assert_validation_split(df_val_residuals["day"].tolist(), df_val_residuals["split"].tolist())

    # Predict raw quantiles on validation set
    val_preds = model.predict_residuals(df_val_residuals)
    raw_q10 = df_val_residuals["base_eta_min"].to_numpy() + val_preds[0.1]
    raw_q90 = df_val_residuals["base_eta_min"].to_numpy() + val_preds[0.9]
    val_y = df_val_residuals["actual_arrival_min"].to_numpy()

    calibrator = ConformalCalibrator(target_coverage=0.80)
    q_adj = calibrator.calibrate(
        y_true=val_y,
        q10_preds=raw_q10,
        q90_preds=raw_q90,
        days=df_val_residuals["day"].tolist(),
        splits=df_val_residuals["split"].tolist(),
    )
    calibrator.save(artifacts_dir / "conformal_calibration.json")
    logger.info(f"  -> Calibrated conformal shift Q = {q_adj:+.2f} min (Saved to {artifacts_dir / 'conformal_calibration.json'})")

    # 5. Evaluate Validation Set Performance
    calibrated_q10 = np.maximum(df_val_residuals["query_time_min"].to_numpy(), raw_q10 - q_adj)
    calibrated_q90 = np.maximum(calibrated_q10, raw_q90 + q_adj)
    empirical_coverage = np.mean((val_y >= calibrated_q10) & (val_y <= calibrated_q90))
    mean_width = np.mean(calibrated_q90 - calibrated_q10)
    mae_p50 = np.mean(np.abs(val_y - (df_val_residuals["base_eta_min"].to_numpy() + val_preds[0.5])))

    logger.info("[5/5] Pipeline Complete!")
    logger.info(f"  Validation Coverage: {empirical_coverage * 100:.1f}% (Target: 80%)")
    logger.info(f"  Validation Mean Window Width: {mean_width:.2f} min")
    logger.info(f"  Validation P50 MAE: {mae_p50:.2f} min")

    return profiles, model, calibrator


if __name__ == "__main__":
    train_pipeline()
