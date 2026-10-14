"""
LightGBM Poisson Demand Regressor with Negative-Binomial Quantile Prediction Bands.
Fits mean arrivals using LightGBM Poisson objective and calibrates dispersion on the validation split.
Derives P50, P80, and P90 prediction bands guaranteeing monotonicity (P50 <= P80 <= P90).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence, Union
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import optimize, special, stats


class DemandModel:
    """
    Demand forecasting model combining LightGBM Poisson regression for conditional mean
    with a Negative-Binomial dispersion model fit on validation data for quantile prediction bands.
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        n_estimators: int = 300,
        random_state: int = 42,
        feature_cols: Optional[list[str]] = None,
    ):
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.feature_cols = feature_cols

        self.booster: Optional[lgb.Booster] = None
        self.dispersion_alpha: float = 0.01  # Var(Y) = mu + alpha * mu^2
        self.is_fitted: bool = False
        self.metadata: dict[str, Any] = {}

    def _negbin_nll(self, alpha: float, mu: np.ndarray, y: np.ndarray) -> float:
        """Negative log-likelihood of negative-binomial with mean mu and dispersion alpha."""
        if alpha <= 1e-6:
            # Poisson limit
            return float(-np.sum(stats.poisson.logpmf(y, np.maximum(mu, 1e-9))))

        r = 1.0 / alpha
        # Log PMF: gammaln(y + r) - gammaln(r) - gammaln(y + 1) + r*log(r/(r+mu)) + y*log(mu/(r+mu))
        mu_safe = np.maximum(mu, 1e-9)
        term1 = special.gammaln(y + r) - special.gammaln(r) - special.gammaln(y + 1)
        term2 = r * (np.log(r) - np.log(r + mu_safe))
        term3 = y * (np.log(mu_safe) - np.log(r + mu_safe))
        return float(-np.sum(term1 + term2 + term3))

    def fit_dispersion(self, y_val: np.ndarray, mu_pred: np.ndarray) -> float:
        """
        Fits Negative-Binomial overdispersion parameter alpha on the validation set
        by maximizing log-likelihood (minimizing negative log-likelihood).
        """
        y_val_arr = np.asarray(y_val, dtype=float)
        mu_pred_arr = np.asarray(mu_pred, dtype=float)

        res = optimize.minimize_scalar(
            self._negbin_nll,
            bounds=(1e-5, 2.0),
            method="bounded",
            args=(mu_pred_arr, y_val_arr),
        )

        if res.success and res.x > 1e-5:
            self.dispersion_alpha = float(res.x)
        else:
            self.dispersion_alpha = 1e-5

        return self.dispersion_alpha

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series | np.ndarray] = None,
        early_stopping_rounds: int = 30,
        verbose: bool = False,
    ) -> DemandModel:
        """
        Fits the LightGBM Poisson regressor on training split (Days 1-20).
        If validation split (Days 21-25) is provided, performs early stopping and
        fits the Negative-Binomial dispersion parameter alpha on the validation set.
        """
        if self.feature_cols is None:
            self.feature_cols = [c for c in X_train.columns if c not in ("day", "split", "arrivals", "od_destination")]

        X_tr = X_train[self.feature_cols].copy()
        y_tr = np.asarray(y_train, dtype=float)

        train_dataset = lgb.Dataset(X_tr, label=y_tr)
        valid_sets = [train_dataset]

        if X_val is not None and y_val is not None:
            X_v = X_val[self.feature_cols].copy()
            y_v = np.asarray(y_val, dtype=float)
            val_dataset = lgb.Dataset(X_v, label=y_v, reference=train_dataset)
            valid_sets.append(val_dataset)

        params = {
            "objective": "poisson",
            "metric": "poisson",
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_child_samples": self.min_child_samples,
            "random_state": self.random_state,
            "verbose": -1,
        }

        callbacks = []
        if len(valid_sets) > 1 and early_stopping_rounds > 0:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=verbose))

        self.booster = lgb.train(
            params,
            train_dataset,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            callbacks=callbacks,
        )

        self.is_fitted = True

        # Fit dispersion parameter on validation set if available
        if X_val is not None and y_val is not None:
            mu_val = self.predict_mean(X_val)
            self.fit_dispersion(y_val=np.asarray(y_val, dtype=float), mu_pred=mu_val)

        return self

    def predict_mean(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Predicts mean arrivals mu = E[Y|X]. Guaranteed non-negative."""
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("DemandModel is not fitted yet!")

        if isinstance(X, pd.DataFrame):
            cols = self.feature_cols if self.feature_cols is not None else X.columns.tolist()
            X_in = X[cols]
        else:
            X_in = X

        preds = self.booster.predict(X_in)
        return np.maximum(0.0, np.asarray(preds, dtype=float))

    def predict_bands(
        self,
        X: pd.DataFrame | np.ndarray,
        quantiles: tuple[float, ...] = (0.50, 0.80, 0.90),
    ) -> dict[str, np.ndarray]:
        """
        Derives quantile prediction bands using the Negative-Binomial distribution
        with fitted dispersion parameter alpha:
          Var(Y) = mu + alpha * mu^2
        Guarantees monotonicity: P50 <= P80 <= P90.
        """
        mu = self.predict_mean(X)
        bands: dict[str, np.ndarray] = {}

        # Sort requested quantiles
        sorted_quantiles = sorted(quantiles)

        if self.dispersion_alpha > 1e-5:
            r = 1.0 / self.dispersion_alpha
            p = r / (r + np.maximum(mu, 1e-9))
            for q in sorted_quantiles:
                q_key = f"p{int(round(q * 100))}"
                raw_band = stats.nbinom.ppf(q, r, p)
                bands[q_key] = np.maximum(0.0, raw_band.astype(float))
        else:
            for q in sorted_quantiles:
                q_key = f"p{int(round(q * 100))}"
                raw_band = stats.poisson.ppf(q, np.maximum(mu, 1e-9))
                bands[q_key] = np.maximum(0.0, raw_band.astype(float))

        # Strictly enforce monotonicity across bands: P50 <= P80 <= P90
        band_keys = [f"p{int(round(q * 100))}" for q in sorted_quantiles]
        for i in range(1, len(band_keys)):
            prev_key = band_keys[i - 1]
            curr_key = band_keys[i]
            bands[curr_key] = np.maximum(bands[curr_key], bands[prev_key])

        return bands

    def predict(
        self,
        X: pd.DataFrame | np.ndarray,
        quantiles: tuple[float, ...] = (0.50, 0.80, 0.90),
    ) -> pd.DataFrame:
        """
        Full prediction returning a DataFrame with mean and quantile prediction bands.
        """
        mu = self.predict_mean(X)
        bands = self.predict_bands(X, quantiles=quantiles)

        res = {"mean": mu}
        res.update(bands)
        return pd.DataFrame(res)

    def save(self, dir_path: str | Path) -> None:
        """Saves model booster, dispersion parameter, and metadata to disk."""
        target_dir = Path(dir_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        if self.booster is not None:
            self.booster.save_model(str(target_dir / "lgb_demand_model.txt"))

        meta = {
            "dispersion_alpha": self.dispersion_alpha,
            "feature_cols": self.feature_cols,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_child_samples": self.min_child_samples,
            "n_estimators": self.n_estimators,
            "random_state": self.random_state,
        }
        with open(target_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Save picklable instance wrapper for seamless single-call load
        joblib.dump(self, target_dir / "model.pkl")

    @classmethod
    def load(cls, dir_path: str | Path) -> DemandModel:
        """Loads a saved DemandModel from directory."""
        target_dir = Path(dir_path)
        pkl_path = target_dir / "model.pkl"
        if pkl_path.exists():
            instance = joblib.load(pkl_path)
            return instance

        # Alternatively reconstruct from booster text and metadata.json
        meta_path = target_dir / "metadata.json"
        txt_path = target_dir / "lgb_demand_model.txt"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        instance = cls(
            learning_rate=meta["learning_rate"],
            num_leaves=meta["num_leaves"],
            min_child_samples=meta["min_child_samples"],
            n_estimators=meta["n_estimators"],
            random_state=meta["random_state"],
            feature_cols=meta["feature_cols"],
        )
        instance.dispersion_alpha = meta["dispersion_alpha"]
        instance.booster = lgb.Booster(model_file=str(txt_path))
        instance.is_fitted = True
        return instance


def compute_metrics(
    y_true: Union[Sequence[float], np.ndarray],
    y_pred: Union[Sequence[float], np.ndarray],
    q80: Optional[Union[Sequence[float], np.ndarray]] = None,
) -> dict[str, float]:
    """
    Computes required evaluation metrics:
      - MAE: Mean Absolute Error
      - WAPE: Weighted Absolute Percentage Error (sum(|y - y_hat|) / sum(y))
      - Bias: Mean forecast error (mean(y_hat - y))
      - Relative Bias: Normalized forecast error (sum(y_hat - y) / sum(y))
      - Peak-Slot Recall: Proportion of top 10% actual arrival slots flagged in top 10% predictions
      - Pinball Loss at 0.8: Pinball loss for 80th percentile prediction band
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    sum_t = float(np.sum(y_t))
    mae = float(np.mean(np.abs(y_t - y_p)))
    wape = float(np.sum(np.abs(y_t - y_p)) / (sum_t + 1e-9))
    bias = float(np.mean(y_p - y_t))
    rel_bias = float(np.sum(y_p - y_t) / (sum_t + 1e-9))

    # Peak-slot recall (flags true top 10% slots)
    top10_true_thresh = float(np.percentile(y_t, 90))
    true_peak = y_t >= top10_true_thresh

    top10_pred_thresh = float(np.percentile(y_p, 90))
    pred_peak = y_p >= top10_pred_thresh

    peak_recall = float(np.sum(true_peak & pred_peak) / (np.sum(true_peak) + 1e-9))

    metrics: dict[str, float] = {
        "mae": mae,
        "wape": wape,
        "bias": bias,
        "relative_bias": rel_bias,
        "peak_slot_recall": peak_recall,
    }

    if q80 is not None:
        q_arr = np.asarray(q80, dtype=float)
        diff = y_t - q_arr
        pinball = float(np.mean(np.maximum(0.8 * diff, (0.8 - 1.0) * diff)))
        metrics["pinball_loss_0.8"] = pinball

    return metrics
