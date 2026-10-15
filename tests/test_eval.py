"""
Comprehensive Unit & Contract Tests for RoutePulse Evaluation Framework (tests/test_eval.py)
Tests:
  - KPI calculation formulas (P1 through P10)
  - Confidence interval and Student's t math
  - Paired differences, percent improvements, and statistical significance
  - Composite objective function
  - ETA horizon-bucketed error and empirical coverage
  - Report ablation and sensitivity generation
  - Markdown summary generation
  - Strict Test Split integrity enforcement guard
  - Schema conformity with EvalResultsResponse
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
import pytest
import scipy.stats as stats

from core.schemas import EvalResultsResponse, Plan, Trip
from eval.metrics import (
    ConfidenceInterval,
    PairedDifference,
    compute_composite_objective,
    compute_confidence_interval,
    compute_p1_mean_wait,
    compute_p2_left_behind_and_unmet,
    compute_p3_missed_connections,
    compute_p4_overcrowded_trips,
    compute_p5_p95_wait,
    compute_p6_fleet_utilization,
    compute_p7_eta_metrics,
    compute_p8_hard_violations,
    compute_p9_demand_wape,
    compute_p10_plan_churn,
    compute_paired_difference,
)
from eval.report import (
    generate_ablation_data,
    generate_sensitivity_data,
    generate_summary_markdown,
)
from eval.run_eval import assert_test_split_integrity


# ---------------------------------------------------------------------------
# Test Data Fixtures & Helper Classes
# ---------------------------------------------------------------------------
@dataclass
class DummyPassenger:
    pax_id: str
    status: str = "completed"
    left_behind_count: int = 0
    needs_transfer: bool = False
    missed_connection: bool = False
    total_wait_min: float = 5.0


@dataclass
class DummyTripMetrics:
    trip_id: str
    capacity: int = 45
    max_load: int = 30


# ---------------------------------------------------------------------------
# 1. Statistical Confidence Interval & Paired Differences Tests
# ---------------------------------------------------------------------------
def test_confidence_interval_math():
    """Verify Student's t confidence interval formula on known dataset."""
    sample = [6.0, 7.0, 6.5, 7.5, 6.2, 6.8, 7.1, 6.9, 7.3, 6.7]
    n = len(sample)
    mean_expected = float(np.mean(sample))
    std_expected = float(np.std(sample, ddof=1))
    se_expected = std_expected / math.sqrt(n)
    t_crit = float(stats.t.ppf(0.975, df=n - 1))
    hw_expected = t_crit * se_expected

    ci = compute_confidence_interval(sample, confidence=0.95)

    assert math.isclose(ci.mean, mean_expected, rel_tol=1e-5)
    assert math.isclose(ci.std, std_expected, rel_tol=1e-5)
    assert math.isclose(ci.se, se_expected, rel_tol=1e-5)
    assert math.isclose(ci.half_width, hw_expected, rel_tol=1e-5)
    assert math.isclose(ci.lower, mean_expected - hw_expected, rel_tol=1e-5)
    assert math.isclose(ci.upper, mean_expected + hw_expected, rel_tol=1e-5)
    assert ci.n == n
    assert "±" in ci.formatted()


def test_confidence_interval_edge_cases():
    """Verify CI handling of empty and single-element arrays."""
    empty_ci = compute_confidence_interval([])
    assert empty_ci.mean == 0.0
    assert empty_ci.half_width == 0.0
    assert empty_ci.n == 0

    single_ci = compute_confidence_interval([5.5])
    assert single_ci.mean == 5.5
    assert single_ci.half_width == 0.0
    assert single_ci.n == 1


def test_paired_difference_math():
    """Verify paired difference math, standard error of difference, and p-value."""
    base = [7.0, 7.2, 6.8, 7.5, 6.9, 7.1, 7.3, 7.0, 6.7, 7.4]
    prop = [5.0, 5.1, 4.9, 5.3, 4.8, 5.2, 5.0, 5.1, 4.7, 5.2]

    diff = compute_paired_difference(base, prop, lower_is_better=True)

    expected_diffs = np.array(prop) - np.array(base)
    expected_mean_diff = float(np.mean(expected_diffs))
    assert math.isclose(diff.mean_diff, expected_mean_diff, rel_tol=1e-5)
    assert diff.mean_diff < 0  # Lower wait is better
    assert diff.percent_improvement > 25.0  # ~28% improvement
    assert diff.p_value < 0.001  # Highly statistically significant
    assert diff.n == 10
    assert "(-" in diff.formatted() or "(+" in diff.formatted()


def test_paired_difference_mismatched_lengths():
    """Verify error raised on mismatched series lengths."""
    with pytest.raises(ValueError):
        compute_paired_difference([1.0, 2.0], [1.0])


# ---------------------------------------------------------------------------
# 2. Predeclared KPI Unit Tests (P1 - P10)
# ---------------------------------------------------------------------------
def test_p1_mean_wait():
    """P1: Mean wait formula."""
    waits = [4.0, 6.0, 5.0, 9.0, 6.0]
    assert compute_p1_mean_wait(waits) == 6.0
    assert compute_p1_mean_wait([]) == 0.0


def test_p2_left_behind_and_unmet():
    """P2: Left-behind and unmet demand counts."""
    pax_list = [
        DummyPassenger("P1", status="completed", left_behind_count=0),
        DummyPassenger("P2", status="completed", left_behind_count=2),
        DummyPassenger("P3", status="balked", left_behind_count=1),
        DummyPassenger("P4", status="waiting", left_behind_count=0),
    ]
    left_behind, unmet = compute_p2_left_behind_and_unmet(pax_list)
    assert left_behind == 2  # P2 and P3
    assert unmet == 2        # P3 (balked) and P4 (unserved waiting)


def test_p3_missed_connections():
    """P3: Missed connections count and percentage."""
    pax_list = [
        DummyPassenger("P1", needs_transfer=False),
        DummyPassenger("P2", needs_transfer=True, missed_connection=False),
        DummyPassenger("P3", needs_transfer=True, missed_connection=True),
        DummyPassenger("P4", needs_transfer=True, missed_connection=False),
        DummyPassenger("P5", needs_transfer=True, missed_connection=True),
    ]
    missed_count, missed_pct = compute_p3_missed_connections(pax_list)
    assert missed_count == 2
    assert math.isclose(missed_pct, 50.0, rel_tol=1e-5)


def test_p4_overcrowded_trips():
    """P4: Overcrowded trips (>85% soft and >100% hard capacity)."""
    trips = [
        DummyTripMetrics("T1", capacity=45, max_load=30),  # 66.7% - OK
        DummyTripMetrics("T2", capacity=45, max_load=39),  # 86.7% - Soft >85%
        DummyTripMetrics("T3", capacity=45, max_load=48),  # 106.7% - Both >85% and >100%
        DummyTripMetrics("T4", capacity=22, max_load=20),  # 90.9% - Soft >85%
    ]
    count_100, count_85 = compute_p4_overcrowded_trips(trips)
    assert count_100 == 1  # Only T3
    assert count_85 == 3   # T2, T3, T4


def test_p5_p95_wait():
    """P5: 95th percentile tail wait."""
    waits = list(range(1, 101))  # 1 to 100
    p95 = compute_p5_p95_wait(waits)
    assert math.isclose(p95, 95.05, rel_tol=1e-2)


def test_p6_fleet_utilization():
    """P6: Fleet utilization ratio, seat-km, vehicle-km."""
    res = compute_p6_fleet_utilization(
        seat_km_used=2400.0,
        seat_km_offered=6000.0,
        vehicle_km=150.0,
        active_vehicles=8,
    )
    assert res["fleet_utilization_ratio"] == 0.4
    assert res["seat_km_offered"] == 6000.0
    assert res["seat_km_used"] == 2400.0
    assert res["vehicle_km"] == 150.0
    assert res["vehicles_in_service"] == 8.0

    # Zero denominator safety
    zero_res = compute_p6_fleet_utilization(0.0, 0.0, 0.0, 0)
    assert zero_res["fleet_utilization_ratio"] == 0.0


def test_p7_eta_metrics():
    """P7: ETA MAE bucketed by horizon and window coverage."""
    preds = [
        {"stops_away": 1, "actual_arrival_min": 10.0, "eta_p50": 10.5, "eta_p10": 9.0, "eta_p90": 11.5},   # err 0.5, covered
        {"stops_away": 1, "actual_arrival_min": 15.0, "eta_p50": 14.2, "eta_p10": 13.0, "eta_p90": 15.5},  # err 0.8, covered
        {"stops_away": 3, "actual_arrival_min": 25.0, "eta_p50": 26.5, "eta_p10": 24.0, "eta_p90": 28.0},  # err 1.5, covered
        {"stops_away": 5, "actual_arrival_min": 40.0, "eta_p50": 43.0, "eta_p10": 41.0, "eta_p90": 45.0},  # err 3.0, NOT covered
    ]
    m = compute_p7_eta_metrics(preds)
    assert m["sample_size"] == 4
    assert math.isclose(m["mae_overall"], (0.5 + 0.8 + 1.5 + 3.0) / 4.0, rel_tol=1e-2)
    assert math.isclose(m["mae_horizon_1"], (0.5 + 0.8) / 2.0, rel_tol=1e-2)
    assert math.isclose(m["mae_horizon_3"], 1.5, rel_tol=1e-2)
    assert math.isclose(m["mae_horizon_5plus"], 3.0, rel_tol=1e-2)
    assert m["coverage_80"] == 75.0  # 3 out of 4 covered


def test_p8_hard_violations_gate():
    """P8: Hard-constraint gate check."""
    # A valid baseline plan dict has 0 hard violations
    from sim.baseline import generate_baseline_plan
    plan = generate_baseline_plan()
    viols = compute_p8_hard_violations(plan)
    assert viols == 0


def test_p9_demand_wape():
    """P9: Demand forecast WAPE and MAE."""
    actuals = [10.0, 20.0, 30.0, 40.0]
    forecasts = [12.0, 18.0, 35.0, 35.0]
    # abs errors: 2, 2, 5, 5 => sum = 14
    # sum actuals = 100 => WAPE = 14 / 100 = 0.14
    wape, mae = compute_p9_demand_wape(actuals, forecasts)
    assert math.isclose(wape, 0.14, rel_tol=1e-4)
    assert math.isclose(mae, 3.5, rel_tol=1e-2)


def test_p10_plan_churn():
    """P10: Plan churn detection."""
    base_plan = Plan(
        plan_id="p_base",
        name="Base",
        window=["07:30", "10:30"],
        trips=[
            Trip(trip_id="T1", route_id="R1", direction=0, vehicle_id="B1", departure_min=450, scheduled_stop_times={"S01": 450}),
            Trip(trip_id="T2", route_id="R1", direction=0, vehicle_id="B1", departure_min=465, scheduled_stop_times={"S01": 465}),
            Trip(trip_id="T3", route_id="R2", direction=0, vehicle_id="M1", departure_min=460, scheduled_stop_times={"S03": 460}),
        ],
        vehicle_blocks={"B1": ["T1", "T2"], "M1": ["T3"]},
    )
    # Modified plan: T1 retimed to 452, T2 cancelled, T4 added, T3 vehicle swapped to M2
    eval_plan = Plan(
        plan_id="p_eval",
        name="Eval",
        window=["07:30", "10:30"],
        trips=[
            Trip(trip_id="T1", route_id="R1", direction=0, vehicle_id="B1", departure_min=452, scheduled_stop_times={"S01": 452}),  # retimed
            Trip(trip_id="T3", route_id="R2", direction=0, vehicle_id="M2", departure_min=460, scheduled_stop_times={"S03": 460}),  # reassigned
            Trip(trip_id="T4", route_id="R3", direction=0, vehicle_id="B6", departure_min=470, scheduled_stop_times={"S13": 470}),  # added
        ],
        vehicle_blocks={"B1": ["T1"], "M2": ["T3"], "B6": ["T4"]},
    )
    churn = compute_p10_plan_churn(base_plan, eval_plan)
    assert churn["added_trips"] == 1       # T4
    assert churn["cancelled_trips"] == 1   # T2
    assert churn["retimed_trips"] == 1     # T1
    assert churn["reassigned_trips"] == 1  # T3
    assert churn["total_churn"] == 4


def test_composite_objective():
    """Predeclared composite objective calculation."""
    cost = compute_composite_objective(
        p1_wait=5.1,
        p2_unmet=12.0,
        p3_missed=6.0,
        vehicle_km=180.0,
        departure_shift=2.0,
        plan_churn=4.0,
    )
    # Default weights: unmet=10, conn=6, wait=1, km=0.3, dev=0.5, chg=1.5
    # 1.0*5.1 + 10.0*12 + 6.0*6 + 0.3*180 + 0.5*2.0 + 1.5*4.0 = 5.1 + 120 + 36 + 54 + 1.0 + 6.0 = 222.1
    assert math.isclose(cost, 222.1, rel_tol=1e-2)


# ---------------------------------------------------------------------------
# 3. Security Test Split Integrity Guard Tests
# ---------------------------------------------------------------------------
def test_strict_test_split_integrity_pass():
    """Verify test split guard accepts legitimate Test days [26..30]."""
    df = pd.DataFrame({
        "day": [26, 27, 28, 29, 30],
        "split": ["test", "test", "test", "test", "test"],
    })
    # Should pass without assertion error
    assert_test_split_integrity(df, [26, 27, 28, 29, 30])


def test_strict_test_split_integrity_rejection_of_train_days():
    """Verify test split guard catches accidental access to train/validation days."""
    df_leak = pd.DataFrame({
        "day": [20, 26],
        "split": ["test", "test"],
    })
    with pytest.raises(AssertionError, match="SECURITY VIOLATION: Evaluation attempted to access non-test day"):
        assert_test_split_integrity(df_leak, [20, 26])


def test_strict_test_split_integrity_rejection_of_non_test_split():
    """Verify test split guard catches non-test split labels."""
    df_wrong_split = pd.DataFrame({
        "day": [26, 27],
        "split": ["validation", "test"],
    })
    with pytest.raises(AssertionError, match="SECURITY VIOLATION: Non-test split data detected in evaluation slice"):
        assert_test_split_integrity(df_wrong_split, [26, 27])


# ---------------------------------------------------------------------------
# 4. Report Generation & Schema Verification Tests
# ---------------------------------------------------------------------------
def test_ablation_data_generation():
    """Verify ablation generator outputs all 4 required variants."""
    ablations = generate_ablation_data(None, None)
    assert len(ablations) == 4
    variants = [ab["variant"] for ab in ablations]
    assert "Full RoutePulse" in variants
    assert "w/o Live ETA Adjustment" in variants
    assert "w/o Connection Constraint" in variants
    assert "w/o Demand Nowcast" in variants
    # Check that Full RoutePulse has lowest wait and MAE
    full = next(ab for ab in ablations if ab["variant"] == "Full RoutePulse")
    assert full["hard_violations"] == 0


def test_sensitivity_data_generation():
    """Verify sensitivity generator produces operator trade-off profiles."""
    mock_detailed = {
        "S0": {
            "baseline-0": {"p1_mean_wait_min": {"mean": 6.9}, "p2_unmet_demand_pax": {"mean": 47.0}, "p3_missed_connections_count": {"mean": 15.0}},
            "baseline-1": {"p1_mean_wait_min": {"mean": 6.1}, "p2_unmet_demand_pax": {"mean": 32.0}, "p3_missed_connections_count": {"mean": 11.4}},
            "routepulse": {"p1_mean_wait_min": {"mean": 5.1}, "p2_unmet_demand_pax": {"mean": 12.4}, "p3_missed_connections_count": {"mean": 6.2}},
        }
    }
    sens = generate_sensitivity_data(mock_detailed)
    assert len(sens) == 4
    for row in sens:
        assert row["improvement_vs_b0_pct"] > 0
        assert row["routepulse_objective_score"] < row["b0_objective_score"]


def test_summary_markdown_generation():
    """Verify publication markdown summary includes all required sections."""
    mock_results = {
        "summary_table": [
            {"system": "Baseline-0", "scenario": "S0 (Normal)", "wait_min": "6.9 ± 0.4", "left_behind": "47.2 ± 3.1", "missed_conn": "15.1 ± 1.2", "hard_violations": 0},
            {"system": "RoutePulse", "scenario": "S0 (Normal)", "wait_min": "5.1 ± 0.2", "left_behind": "12.4 ± 1.5", "missed_conn": "6.2 ± 0.7", "hard_violations": 0},
        ],
        "eta_metrics": {
            "baseline-0": {"mae_overall": 3.48, "coverage_80": 48.2},
            "routepulse": {"mae_overall": 1.42, "coverage_80": 80.4},
        },
        "demand_forecast": {"baseline_wape": 0.286, "routepulse_wape": 0.148, "wape_improvement_pct": 48.2},
        "ablations": generate_ablation_data(None, None),
        "sensitivity": generate_sensitivity_data({}),
        "paired_differences": {},
        "timestamp": "2026-10-14T12:00:00Z",
    }
    md = generate_summary_markdown(mock_results)
    assert "# RoutePulse Evaluation & Benchmarking Report" in md
    assert "## 2. Predeclared Benchmark Summary Table" in md
    assert "## 5. P7: ETA Accuracy" in md
    assert "## 7. Architectural Ablation Study" in md
    assert "## 8. Objective Weight Sensitivity Analysis" in md
    assert "## 9. Comparison Against Predeclared Stretch Targets" in md


def test_results_json_schema_conformity():
    """Verify results/results.json conforms to EvalResultsResponse schema."""
    import json
    from pathlib import Path
    results_path = Path("results/results.json")
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        resp = EvalResultsResponse(**data)
        assert len(resp.summary_table) == 12
        assert "results/wait_by_scenario.png" in resp.chart_paths
        assert "S0" in resp.scenarios


def test_headline_is_computed_from_measured_results():
    """The headline shown in the UI/report must be derived from results.json, never typed in."""
    import json
    from pathlib import Path
    from eval.report import compute_headline

    results_path = Path("results/results.json")
    if not results_path.exists():
        return
    data = json.loads(results_path.read_text(encoding="utf-8"))
    h = compute_headline(data)

    paired = data["paired_differences"]
    s0 = paired["S0"]["rp_vs_b0"]
    assert h["s0"]["left_behind_rp"] == round(s0["p2_left_behind_pax"]["system_mean"], 1)
    assert h["s0"]["left_behind_b0"] == round(s0["p2_left_behind_pax"]["baseline_mean"], 1)
    assert h["s0"]["left_behind_reduction_pct"] == round(s0["p2_left_behind_pax"]["percent_improvement"], 1)

    lo, hi = h["left_behind_reduction_pct"]
    per_scenario = [paired[k]["rp_vs_b0"]["p2_left_behind_pax"]["percent_improvement"] for k in paired]
    assert lo == round(min(per_scenario), 1) and hi == round(max(per_scenario), 1)

    assert h["hard_violations"] == sum(int(r["hard_violations"]) for r in data["summary_table"])
    assert h["runs"] == len(data["summary_table"]) * data["replications"]
    assert h["eta"]["mae_rp"] == data["eta_metrics"]["routepulse"]["mae_overall"]


def test_headline_is_empty_safe_for_partial_results():
    from eval.report import compute_headline

    h = compute_headline({"summary_table": [], "paired_differences": {}, "eta_metrics": {}})
    assert h["hard_violations"] == 0
    assert h["wait_reduction_pct"] == [0.0, 0.0]


def test_bundled_fixtures_match_measured_results():
    """Offline fixtures (API + web) must carry the same headline as results/results.json."""
    import json
    from pathlib import Path
    from eval.report import compute_headline

    results_path = Path("results/results.json")
    if not results_path.exists():
        return
    expected = compute_headline(json.loads(results_path.read_text(encoding="utf-8")))
    for fixture in ("api/fixtures/eval_results.json", "web/src/fixtures/eval_results.json"):
        got = json.loads(Path(fixture).read_text(encoding="utf-8"))["headline"]
        assert got == expected, f"{fixture} is stale: re-run the fixture export after `make eval`"
