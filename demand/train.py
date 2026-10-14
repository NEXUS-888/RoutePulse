"""
Training Script for RoutePulse Demand Forecasting Model.
Trains LightGBM Poisson regressor on Days 1-20 (train split),
fits Negative-Binomial dispersion parameter on Days 21-25 (validation split),
validates against the Historical Mean Baseline, and saves artifacts to demand/models/.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd

from demand.baselines import HistoricalBaseline
from demand.features import extract_features, prepare_splits
from demand.model import DemandModel, compute_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demand.train")


def train_demand_pipeline(
    data_dir: str | Path = "data",
    models_dir: str | Path = "demand/models",
    learning_rate: float = 0.05,
    num_leaves: int = 31,
    min_child_samples: int = 20,
    n_estimators: int = 300,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Executes the full demand model training and calibration pipeline.
    """
    data_path = Path(data_dir)
    demand_parquet = data_path / "demand_obs.parquet"
    events_csv = data_path / "events.csv"
    out_dir = Path(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading dataset and preparing train (Days 1-20) / val (Days 21-25) splits...")
    X_train, y_train, X_val, y_val = prepare_splits(
        demand_path=demand_parquet,
        events_path=events_csv,
    )

    # 1. Fit and evaluate Historical Mean Baseline
    logger.info("Fitting Historical Mean Baseline on train split...")
    df_train_full = extract_features(split="train", demand_path=demand_parquet, events_path=events_csv)
    df_val_full = extract_features(split="validation", demand_path=demand_parquet, events_path=events_csv)

    baseline = HistoricalBaseline()
    baseline.fit(df_train_full)
    baseline_val_preds = baseline.predict(df_val_full)
    baseline_metrics = compute_metrics(y_val, baseline_val_preds)
    logger.info(f"Historical Baseline Validation -> MAE: {baseline_metrics['mae']:.4f}, WAPE: {baseline_metrics['wape']:.4f}")

    # 2. Train LightGBM Poisson Regressor
    logger.info("Training LightGBM Poisson Model...")
    model = DemandModel(
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        min_child_samples=min_child_samples,
        n_estimators=n_estimators,
        random_state=random_state,
        feature_cols=X_train.columns.tolist(),
    )
    model.fit(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        early_stopping_rounds=30,
        verbose=False,
    )

    logger.info(f"Fitted Negative-Binomial dispersion alpha: {model.dispersion_alpha:.6f}")

    # 3. Model Predictions & Metrics
    val_preds = model.predict(X_val)
    val_metrics = compute_metrics(
        y_true=y_val,
        y_pred=val_preds["mean"],
        q80=val_preds["p80"],
    )

    logger.info(
        f"RoutePulse LightGBM Validation -> MAE: {val_metrics['mae']:.4f}, "
        f"WAPE: {val_metrics['wape']:.4f}, "
        f"Bias: {val_metrics['bias']:.4f}, "
        f"Peak Recall: {val_metrics['peak_slot_recall']:.4f}, "
        f"Pinball@0.8: {val_metrics['pinball_loss_0.8']:.4f}"
    )

    # 4. Win condition validation check
    assert val_metrics["mae"] < baseline_metrics["mae"], (
        f"Model MAE ({val_metrics['mae']:.4f}) did not beat Baseline MAE ({baseline_metrics['mae']:.4f})"
    )
    assert val_metrics["wape"] < baseline_metrics["wape"], (
        f"Model WAPE ({val_metrics['wape']:.4f}) did not beat Baseline WAPE ({baseline_metrics['wape']:.4f})"
    )
    logger.info("Win condition satisfied: RoutePulse model outperforms baseline on validation set!")

    # 5. Save Artifacts
    logger.info(f"Saving model artifacts to {out_dir}...")
    model.save(out_dir)

    # Save baseline artifact as well
    joblib.dump(baseline, out_dir / "baseline.pkl")

    # Save training report metadata
    report = {
        "model_type": "LightGBM_Poisson_NegBin_Bands",
        "train_split": "Days 1-20",
        "validation_split": "Days 21-25",
        "test_split_touched": False,
        "dispersion_alpha": model.dispersion_alpha,
        "validation_metrics": val_metrics,
        "baseline_metrics": baseline_metrics,
        "improvement_pct": {
            "mae_reduction_pct": float((baseline_metrics["mae"] - val_metrics["mae"]) / baseline_metrics["mae"] * 100),
            "wape_reduction_pct": float((baseline_metrics["wape"] - val_metrics["wape"]) / baseline_metrics["wape"] * 100),
        },
    }
    with open(out_dir / "training_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Artifacts saved successfully!")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RoutePulse Demand Forecasting Model")
    parser.add_argument("--data-dir", type=str, default="data", help="Path to data directory")
    parser.add_argument("--models-dir", type=str, default="demand/models", help="Output models directory")
    args = parser.parse_args()

    results = train_demand_pipeline(data_dir=args.data_dir, models_dir=args.models_dir)
    print("\n=== Training Summary Report ===")
    print(json.dumps(results, indent=2))
