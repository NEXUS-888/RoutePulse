"""
Quantile Residual Regression Model (eta/model.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- LightGBM quantile regression at quantiles [0.1, 0.5, 0.9] predicting residual error on:
  - remaining stops
  - time bucket (15-min slot)
  - current delay (min)
  - rho (online delay ratio)
  - vehicle load
  - weekday (day % 7)
- CRITICAL SPLIT CONSTRAINT: Train ONLY on Train split (Days 1-20). NEVER touch Test split (Days 26-30).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor


def assert_train_split(
    days: Sequence[int], splits: Optional[Sequence[str]] = None
) -> None:
    """
    Enforces strict split isolation.
    Asserts that all training samples come strictly from Days 1-20 (Train split).
    Raises AssertionError immediately if Validation (21-25) or Test (26-30) days are detected.
    """
    unique_days = set(days)
    invalid_days = unique_days - set(range(1, 21))
    assert not invalid_days, (
        f"Data leakage detected! Training data must strictly contain Days 1-20 (Train split). "
        f"Found forbidden days: {invalid_days}"
    )

    if splits is not None:
        for s in set(splits):
            assert str(s).lower() == "train", (
                f"Data leakage detected! Split column must strictly be 'train', got '{s}'"
            )


FEATURE_COLUMNS = [
    "remaining_stops",
    "time_bucket",
    "current_delay_min",
    "rho",
    "vehicle_load",
    "weekday",
]


class EtaResidualModel:
    """
    Predicts residual error (actual arrival min - base profile+live ETA min)
    at quantiles [0.1, 0.5, 0.9] using LightGBM quantile regression.
    """

    def __init__(
        self,
        quantiles: Sequence[float] = (0.1, 0.5, 0.9),
        n_estimators: int = 80,
        learning_rate: float = 0.05,
        max_depth: int = 4,
        num_leaves: int = 15,
        random_state: int = 20261014,
    ):
        self.quantiles = list(quantiles)
        self.models: dict[float, LGBMRegressor] = {}
        self.is_fitted = False

        for q in self.quantiles:
            self.models[q] = LGBMRegressor(
                objective="quantile",
                alpha=q,
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                num_leaves=num_leaves,
                min_child_samples=10,
                random_state=random_state,
                verbose=-1,
                n_jobs=1,
            )

    def fit(self, df_train: pd.DataFrame) -> EtaResidualModel:
        """
        Trains quantile regression models.
        Strictly enforces Train split isolation (Days 1-20).
        """
        # Strict validation of training split integrity
        if "day" in df_train.columns:
            splits = df_train["split"].tolist() if "split" in df_train.columns else None
            assert_train_split(df_train["day"].tolist(), splits)

        # Ensure all required features are present
        for col in FEATURE_COLUMNS:
            if col not in df_train.columns:
                raise ValueError(f"Missing required feature column: {col}")

        X = df_train[FEATURE_COLUMNS].copy()
        y = df_train["residual_min"].copy()

        # Handle any possible NaN values
        X = X.fillna({
            "remaining_stops": 1,
            "time_bucket": 30,
            "current_delay_min": 0.0,
            "rho": 1.0,
            "vehicle_load": 15.0,
            "weekday": 1,
        })

        for q in self.quantiles:
            self.models[q].fit(X, y)

        self.is_fitted = True
        return self

    def predict_residuals(
        self, X: Union[pd.DataFrame, dict[str, Any]]
    ) -> dict[float, np.ndarray]:
        """
        Predicts residual quantiles for input feature records.
        Returns dict: {0.1: array, 0.5: array, 0.9: array}.
        Enforces quantile monotonicity: q10 <= q50 <= q90.
        """
        if isinstance(X, dict):
            df_x = pd.DataFrame([X])
        else:
            df_x = X.copy()

        # Fill defaults for missing features
        defaults = {
            "remaining_stops": 1,
            "time_bucket": 30,
            "current_delay_min": 0.0,
            "rho": 1.0,
            "vehicle_load": 15.0,
            "weekday": 1,
        }
        for col, default_val in defaults.items():
            if col not in df_x.columns:
                df_x[col] = default_val
            else:
                df_x[col] = df_x[col].fillna(default_val)

        feat_matrix = df_x[FEATURE_COLUMNS]

        if not self.is_fitted:
            # Fallback heuristic if models not yet fitted
            n = len(df_x)
            stops = feat_matrix["remaining_stops"].to_numpy()
            spread = 0.5 * np.sqrt(np.maximum(1, stops))
            return {
                0.1: -1.28 * spread,
                0.5: np.zeros(n),
                0.9: 1.28 * spread,
            }

        preds: dict[float, np.ndarray] = {}
        for q in self.quantiles:
            preds[q] = self.models[q].predict(feat_matrix)

        # Enforce quantile monotonicity: q10 <= q50 <= q90
        if 0.1 in preds and 0.5 in preds and 0.9 in preds:
            preds[0.1] = np.minimum(preds[0.1], preds[0.5])
            preds[0.9] = np.maximum(preds[0.9], preds[0.5])

        return preds

    def predict_eta(
        self,
        base_eta_min: float,
        remaining_stops: int,
        time_bucket: int,
        current_delay_min: float,
        rho: float,
        vehicle_load: float,
        weekday: int,
        query_time_min: float,
    ) -> tuple[float, float, float]:
        """
        Computes final uncalibrated (eta_p10, eta_p50, eta_p90) arrival minutes.
        """
        feat = {
            "remaining_stops": max(1, remaining_stops),
            "time_bucket": time_bucket,
            "current_delay_min": current_delay_min,
            "rho": rho,
            "vehicle_load": vehicle_load,
            "weekday": weekday,
        }
        residuals = self.predict_residuals(feat)
        r10 = float(residuals[0.1][0])
        r50 = float(residuals[0.5][0])
        r90 = float(residuals[0.9][0])

        eta_p10 = max(query_time_min, base_eta_min + r10)
        eta_p50 = max(query_time_min, base_eta_min + r50)
        eta_p90 = max(eta_p50, base_eta_min + r90)
        eta_p10 = min(eta_p10, eta_p50)

        return round(eta_p10, 1), round(eta_p50, 1), round(eta_p90, 1)

    def save(self, model_dir: Union[Path, str]) -> None:
        p = Path(model_dir)
        p.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "quantiles": self.quantiles,
                "is_fitted": self.is_fitted,
                "models": self.models,
            },
            p / "eta_residual_model.joblib",
        )

    @classmethod
    def load(cls, model_dir: Union[Path, str]) -> EtaResidualModel:
        p = Path(model_dir) / "eta_residual_model.joblib"
        data = joblib.load(p)
        obj = cls(quantiles=data["quantiles"])
        obj.is_fitted = data["is_fitted"]
        obj.models = data["models"]
        return obj
