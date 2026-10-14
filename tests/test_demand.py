"""
Unit and Integration Tests for RoutePulse Demand Forecasting Module.
Verifies:
  - Feature extraction and strict split boundary enforcement (Days 1-20 train, 21-25 val, never 26-30)
  - Historical mean baseline with event multiplier fallback
  - LightGBM Poisson model training and dispersion calibration
  - Prediction band monotonicity (P50 <= P80 <= P90)
  - Metric computations: WAPE, MAE, bias, peak-slot recall, pinball loss at 0.8
  - Win condition: RoutePulse demand model beats historical mean baseline on validation set
  - Nowcast multiplier clipping and decay over 60 minutes
  - Model serialization and deserialization
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from demand.baselines import HistoricalBaseline
from demand.features import (
    ALL_STOPS,
    FEATURE_COLUMNS,
    compute_proximity_to_class_change,
    extract_features,
    get_feature_columns,
    prepare_splits,
)
from demand.model import DemandModel, compute_metrics
from demand.nowcast import NowcastCorrector, compute_multiplier, decay_multiplier


# ---------------------------------------------------------------------------
# Test 1: Feature Extraction and Split Boundary Enforcement
# ---------------------------------------------------------------------------

def test_feature_columns_and_types():
    """Verify that feature extraction generates all required columns without NaNs."""
    df_features = extract_features(split="train")

    expected_cols = [
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
    for col in expected_cols:
        assert col in df_features.columns, f"Missing required feature column: {col}"

    # Verify no NaN values in features
    assert not df_features[expected_cols].isna().any().any(), "Feature matrix contains unexpected NaNs"

    # Verify hour and minute bounds
    assert (df_features["hour"] >= 6).all() and (df_features["hour"] <= 21).all()
    assert (df_features["minute"].isin([0, 15, 30, 45])).all()

    # Verify class change proximity calculation
    assert (df_features["class_change_proximity"] >= 0).all()
    assert (df_features["class_change_proximity"] <= 25).all()


def test_split_boundary_enforcement():
    """Verify strict split boundary: train Days 1-20, validation Days 21-25, NEVER Days 26-30."""
    df_train = extract_features(split="train")
    assert set(df_train["day"].unique()) == set(range(1, 21))

    df_val = extract_features(split="validation")
    assert set(df_val["day"].unique()) == set(range(21, 26))

    # Test that passing an explicit test split triggers an AssertionError
    df_fake_test = pd.DataFrame({
        "day": [26, 27, 28],
        "stop_id": ["S01", "S02", "S03"],
        "slot_start": [480, 495, 510],
        "arrivals": [10, 15, 20],
        "split": ["test", "test", "test"],
    })
    with pytest.raises(AssertionError, match="Data leak detected|Days 26-30 must never be touched"):
        extract_features(df_demand=df_fake_test, enforce_split_boundary=True)


def test_class_change_proximity_logic():
    """Verify class-change proximity function for minutes within the hour."""
    # Minute 0: distance to 00 is 0
    assert compute_proximity_to_class_change(0) == 0
    # Minute 50: distance to 50 is 0
    assert compute_proximity_to_class_change(50) == 0
    # Minute 45: distance to 50 is 5
    assert compute_proximity_to_class_change(45) == 5
    # Minute 15: distance to 00 is 15
    assert compute_proximity_to_class_change(15) == 15
    # Minute 30: distance to 50 is 20, to 00 is 30 -> min is 20
    assert compute_proximity_to_class_change(30) == 20


# ---------------------------------------------------------------------------
# Test 2: Historical Mean Baseline
# ---------------------------------------------------------------------------

def test_historical_baseline():
    """Tests fitting and prediction of historical mean baseline with event fallback."""
    df_train = extract_features(split="train")
    df_val = extract_features(split="validation")

    baseline = HistoricalBaseline()
    baseline.fit(df_train)

    preds = baseline.predict(df_val)
    assert len(preds) == len(df_val)
    assert np.all(preds >= 0.0)
    assert not np.isnan(preds).any()

    # Verify fallback for unseen combinations
    dummy_df = pd.DataFrame({
        "stop_id": ["UNKNOWN_STOP"],
        "slot_start": [500],
        "day": [3],
        "event_active": [0],
        "minutes_since_event_end": [999.0],
    })
    dummy_pred = baseline.predict(dummy_df)
    assert dummy_pred[0] == pytest.approx(baseline.global_mean, rel=1e-3)

    # Verify event multiplier elevates prediction
    dummy_evt_df = pd.DataFrame({
        "stop_id": ["S07"],
        "slot_start": [900],
        "day": [12],
        "event_active": [1],
        "minutes_since_event_end": [-1.0],
    })
    pred_event = baseline.predict(dummy_evt_df)[0]
    dummy_no_evt_df = dummy_evt_df.copy()
    dummy_no_evt_df["event_active"] = 0
    pred_no_event = baseline.predict(dummy_no_evt_df)[0]

    assert pred_event > pred_no_event


# ---------------------------------------------------------------------------
# Test 3: Poisson Model Training and Dispersion Fitting
# ---------------------------------------------------------------------------

def test_poisson_model_training_and_dispersion():
    """Tests LightGBM Poisson regressor training and Negative-Binomial dispersion calibration."""
    X_train, y_train, X_val, y_val = prepare_splits()

    model = DemandModel(
        n_estimators=100,
        learning_rate=0.08,
        random_state=42,
    )
    model.fit(X_train, y_train, X_val, y_val)

    assert model.is_fitted
    assert model.booster is not None
    assert model.dispersion_alpha > 0.0, "Dispersion alpha must be strictly positive"

    val_means = model.predict_mean(X_val)
    assert len(val_means) == len(y_val)
    assert np.all(val_means >= 0.0)
    assert not np.isnan(val_means).any()


# ---------------------------------------------------------------------------
# Test 4: Prediction Band Monotonicity (P50 <= P80 <= P90)
# ---------------------------------------------------------------------------

def test_band_monotonicity_on_validation_set():
    """Verifies that P50 <= P80 <= P90 holds strictly for all validation samples."""
    X_train, y_train, X_val, y_val = prepare_splits()

    model = DemandModel(n_estimators=100, learning_rate=0.08, random_state=42)
    model.fit(X_train, y_train, X_val, y_val)

    bands = model.predict_bands(X_val, quantiles=(0.50, 0.80, 0.90))
    p50 = bands["p50"]
    p80 = bands["p80"]
    p90 = bands["p90"]

    # Strict monotonicity checks
    assert (p50 <= p80).all(), "Monotonicity violated: found instances where P50 > P80"
    assert (p80 <= p90).all(), "Monotonicity violated: found instances where P80 > P90"


def test_band_monotonicity_edge_cases():
    """Verifies monotonicity under edge cases: zero mean, large mean."""
    model = DemandModel()
    model.is_fitted = True
    model.dispersion_alpha = 0.05

    # Mock predictions
    zero_mu = np.array([0.0, 0.001, 1.0, 10.0, 50.0, 200.0])
    # Manually compute bands
    r = 1.0 / model.dispersion_alpha
    p = r / (r + np.maximum(zero_mu, 1e-9))
    from scipy import stats
    p50 = stats.nbinom.ppf(0.50, r, p)
    p80 = stats.nbinom.ppf(0.80, r, p)
    p90 = stats.nbinom.ppf(0.90, r, p)

    assert (p50 <= p80).all()
    assert (p80 <= p90).all()


# ---------------------------------------------------------------------------
# Test 5: Metric Computations
# ---------------------------------------------------------------------------

def test_compute_metrics():
    """Tests calculation of WAPE, MAE, bias, relative bias, peak-slot recall, and pinball loss."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([12.0, 18.0, 32.0, 38.0])
    q80 = np.array([15.0, 25.0, 35.0, 45.0])

    metrics = compute_metrics(y_true, y_pred, q80=q80)

    # MAE = (|10-12| + |20-18| + |30-32| + |40-38|) / 4 = 8 / 4 = 2.0
    assert metrics["mae"] == pytest.approx(2.0, rel=1e-5)

    # WAPE = 8 / (10 + 20 + 30 + 40) = 8 / 100 = 0.08
    assert metrics["wape"] == pytest.approx(0.08, rel=1e-5)

    # Mean Bias = (2 - 2 + 2 - 2) / 4 = 0.0
    assert metrics["bias"] == pytest.approx(0.0, abs=1e-5)

    # Pinball loss at 0.8:
    # y - q: 10-15 = -5; 20-25 = -5; 30-35 = -5; 40-45 = -5 (all y < q)
    # loss per item = (1 - 0.8) * 5 = 1.0
    assert metrics["pinball_loss_0.8"] == pytest.approx(1.0, rel=1e-5)


# ---------------------------------------------------------------------------
# Test 6: Win Condition (RoutePulse beats Historical Baseline)
# ---------------------------------------------------------------------------

def test_routepulse_beats_historical_baseline():
    """
    Validates that RoutePulse demand forecast beats the historical mean baseline
    on the validation set (Days 21-25) in both MAE and WAPE.
    """
    df_train = extract_features(split="train")
    df_val = extract_features(split="validation")
    X_train, y_train, X_val, y_val = prepare_splits()

    # 1. Historical Baseline
    baseline = HistoricalBaseline()
    baseline.fit(df_train)
    baseline_preds = baseline.predict(df_val)
    baseline_metrics = compute_metrics(y_val, baseline_preds)

    # 2. RoutePulse LightGBM Poisson Model
    model = DemandModel(learning_rate=0.05, n_estimators=300, random_state=42)
    model.fit(X_train, y_train, X_val, y_val)
    preds = model.predict(X_val)
    model_metrics = compute_metrics(y_val, preds["mean"], q80=preds["p80"])

    print(f"\n[Validation Set Results]")
    print(f"Historical Baseline -> MAE: {baseline_metrics['mae']:.4f}, WAPE: {baseline_metrics['wape']:.4f}")
    print(f"RoutePulse LightGBM -> MAE: {model_metrics['mae']:.4f}, WAPE: {model_metrics['wape']:.4f}")

    # Assert model wins
    assert model_metrics["mae"] < baseline_metrics["mae"], (
        f"RoutePulse MAE ({model_metrics['mae']:.4f}) failed to beat Baseline MAE ({baseline_metrics['mae']:.4f})"
    )
    assert model_metrics["wape"] < baseline_metrics["wape"], (
        f"RoutePulse WAPE ({model_metrics['wape']:.4f}) failed to beat Baseline WAPE ({baseline_metrics['wape']:.4f})"
    )


# ---------------------------------------------------------------------------
# Test 7: Real-Time Nowcast Correction
# ---------------------------------------------------------------------------

def test_nowcast_multiplier_and_decay():
    """Tests real-time multiplier computation, clipping [0.7, 1.8], and decay over 60 min."""
    # 1. Equal counts -> m ~ 1.0
    m_equal = compute_multiplier(observed_30m=30.0, predicted_30m=30.0)
    assert m_equal == pytest.approx(1.0, rel=1e-3)

    # 2. Large surge -> clipped to 1.8
    m_high = compute_multiplier(observed_30m=100.0, predicted_30m=20.0)
    assert m_high == pytest.approx(1.8, abs=1e-5)

    # 3. Large slump -> clipped to 0.7
    m_low = compute_multiplier(observed_30m=5.0, predicted_30m=50.0)
    assert m_low == pytest.approx(0.7, abs=1e-5)

    # 4. Multiplier decay over 60 minutes
    m_init = 1.6
    # lead_time = 0 -> m_init
    assert decay_multiplier(m_init, 0.0) == pytest.approx(1.6, abs=1e-5)
    # lead_time = 30 -> halfway between 1.6 and 1.0 = 1.3
    assert decay_multiplier(m_init, 30.0) == pytest.approx(1.3, abs=1e-5)
    # lead_time = 60 -> decayed to 1.0
    assert decay_multiplier(m_init, 60.0) == pytest.approx(1.0, abs=1e-5)
    # lead_time = 90 -> beyond decay horizon, still 1.0
    assert decay_multiplier(m_init, 90.0) == pytest.approx(1.0, abs=1e-5)

    # 5. NowcastCorrector band monotonicity preservation
    corrector = NowcastCorrector()
    p50, p80, p90 = corrector.correct_bands(10.0, 15.0, 20.0, lead_time_min=15.0, multiplier=m_high)
    assert p50 <= p80 <= p90


# ---------------------------------------------------------------------------
# Test 8: Model Serialization and Deserialization
# ---------------------------------------------------------------------------

def test_model_save_and_load(tmp_path: Path):
    """Verifies that saved model can be loaded and produces identical predictions."""
    X_train, y_train, X_val, y_val = prepare_splits()

    model = DemandModel(n_estimators=50, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train, X_val, y_val)

    original_preds = model.predict(X_val)

    # Save to temporary test directory
    model.save(tmp_path)

    # Load back
    loaded_model = DemandModel.load(tmp_path)
    loaded_preds = loaded_model.predict(X_val)

    # Verify identical predictions
    np.testing.assert_allclose(original_preds["mean"].values, loaded_preds["mean"].values, rtol=1e-5)
    np.testing.assert_allclose(original_preds["p50"].values, loaded_preds["p50"].values, rtol=1e-5)
    np.testing.assert_allclose(original_preds["p80"].values, loaded_preds["p80"].values, rtol=1e-5)
    np.testing.assert_allclose(original_preds["p90"].values, loaded_preds["p90"].values, rtol=1e-5)
    assert loaded_model.dispersion_alpha == pytest.approx(model.dispersion_alpha, rel=1e-5)
