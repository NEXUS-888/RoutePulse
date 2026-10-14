"""
RoutePulse Predeclared Evaluation Metrics & Statistical Analysis (eval/metrics.py)
Computes all predeclared KPIs P1 through P10 and 95% confidence intervals
and paired differences across stochastic seeds.

Section 9.2 Predeclared KPIs:
  P1:  Mean passenger wait (min)
  P2:  Left-behind / unmet demand (pax)
  P3:  Missed connections (count & %)
  P4:  Overcrowded trips count (>100% hard and >85% soft)
  P5:  P95 wait (min)
  P6:  Fleet utilization ratio, seat-km, vehicle-km
  P7:  ETA MAE and 80% window coverage
  P8:  Hard-constraint violations (must be 0 for all evaluated plans)
  P9:  Demand forecast WAPE
  P10: Plan churn (# changed trips vs published baseline)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import scipy.stats as stats

from core.schemas import Plan, Trip, ApcRecord, Violation
from validate.validator import get_hard_violations


@dataclass
class ConfidenceInterval:
    """Represents a sample mean with 95% Student's t confidence interval."""
    mean: float
    std: float
    se: float
    half_width: float
    lower: float
    upper: float
    n: int
    confidence: float = 0.95

    def formatted(self, precision: int = 1) -> str:
        """Returns string representation in 'mean ± half_width' format."""
        return f"{self.mean:.{precision}f} \u00b1 {self.half_width:.{precision}f}"

    def to_dict(self) -> dict[str, float]:
        return {
            "mean": round(self.mean, 3),
            "std": round(self.std, 3),
            "se": round(self.se, 3),
            "half_width": round(self.half_width, 3),
            "lower": round(self.lower, 3),
            "upper": round(self.upper, 3),
            "n": self.n,
        }


@dataclass
class PairedDifference:
    """Represents a paired difference between two systems across matching seeds."""
    baseline_mean: float
    system_mean: float
    mean_diff: float          # system_mean - baseline_mean
    std_diff: float
    se_diff: float
    half_width: float
    lower: float
    upper: float
    percent_improvement: float # Positive means system is better (e.g. Lower wait/unmet)
    p_value: float
    n: int
    confidence: float = 0.95

    def formatted(self, precision: int = 1) -> str:
        sign = "+" if self.mean_diff > 0 else ""
        return f"{sign}{self.mean_diff:.{precision}f} \u00b1 {self.half_width:.{precision}f} ({self.percent_improvement:+.1f}%)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_mean": round(self.baseline_mean, 3),
            "system_mean": round(self.system_mean, 3),
            "mean_diff": round(self.mean_diff, 3),
            "std_diff": round(self.std_diff, 3),
            "se_diff": round(self.se_diff, 3),
            "half_width": round(self.half_width, 3),
            "lower": round(self.lower, 3),
            "upper": round(self.upper, 3),
            "percent_improvement": round(self.percent_improvement, 2),
            "p_value": round(self.p_value, 5),
            "statistically_significant": self.p_value < 0.05,
            "n": self.n,
        }


def compute_confidence_interval(
    data: Sequence[float],
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """
    Computes sample mean and two-tailed Student's t confidence interval.
    For n=20 and confidence=0.95, t_crit(19) ~ 2.093.
    """
    arr = np.asarray(data, dtype=float)
    n = len(arr)
    if n == 0:
        return ConfidenceInterval(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, confidence)
    if n == 1:
        val = float(arr[0])
        return ConfidenceInterval(val, 0.0, 0.0, 0.0, val, val, 1, confidence)

    mean = float(np.mean(arr))
    # ddof=1 for unbiased sample variance
    std = float(np.std(arr, ddof=1))
    se = std / math.sqrt(n)

    # Student-t critical value
    t_crit = float(stats.t.ppf((1.0 + confidence) / 2.0, df=n - 1))
    half_width = t_crit * se

    return ConfidenceInterval(
        mean=mean,
        std=std,
        se=se,
        half_width=half_width,
        lower=mean - half_width,
        upper=mean + half_width,
        n=n,
        confidence=confidence,
    )


def compute_paired_difference(
    baseline_series: Sequence[float],
    system_series: Sequence[float],
    confidence: float = 0.95,
    lower_is_better: bool = True,
) -> PairedDifference:
    """
    Computes paired difference d_i = system_i - baseline_i across identical seeds.
    Percent improvement is defined such that positive values indicate improvement:
      If lower_is_better (e.g. wait, left-behind, missed connections):
        pct_imp = (baseline_mean - system_mean) / baseline_mean * 100%
      If higher_is_better (e.g. utilization, coverage):
        pct_imp = (system_mean - baseline_mean) / baseline_mean * 100%
    """
    base_arr = np.asarray(baseline_series, dtype=float)
    sys_arr = np.asarray(system_series, dtype=float)
    if len(base_arr) != len(sys_arr):
        raise ValueError(f"Series lengths must match for paired analysis: {len(base_arr)} vs {len(sys_arr)}")

    n = len(base_arr)
    if n == 0:
        return PairedDifference(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0, confidence)

    diffs = sys_arr - base_arr
    mean_base = float(np.mean(base_arr))
    mean_sys = float(np.mean(sys_arr))
    mean_diff = float(np.mean(diffs))

    if n > 1:
        std_diff = float(np.std(diffs, ddof=1))
        se_diff = std_diff / math.sqrt(n)
        t_crit = float(stats.t.ppf((1.0 + confidence) / 2.0, df=n - 1))
        half_width = t_crit * se_diff
        # Two-sided paired t-test
        t_stat, p_val = stats.ttest_rel(sys_arr, base_arr)
        p_val = float(p_val) if not np.isnan(p_val) else 1.0
    else:
        std_diff = 0.0
        se_diff = 0.0
        half_width = 0.0
        p_val = 1.0

    if abs(mean_base) > 1e-9:
        if lower_is_better:
            pct_imp = ((mean_base - mean_sys) / mean_base) * 100.0
        else:
            pct_imp = ((mean_sys - mean_base) / mean_base) * 100.0
    else:
        pct_imp = 0.0

    return PairedDifference(
        baseline_mean=mean_base,
        system_mean=mean_sys,
        mean_diff=mean_diff,
        std_diff=std_diff,
        se_diff=se_diff,
        half_width=half_width,
        lower=mean_diff - half_width,
        upper=mean_diff + half_width,
        percent_improvement=pct_imp,
        p_value=p_val,
        n=n,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Individual Predeclared KPI Functions (P1 - P10)
# ---------------------------------------------------------------------------

def compute_p1_mean_wait(waits: Sequence[float]) -> float:
    """
    P1: Mean passenger wait (min).
    Average (boarding time - arrival time at stop), including waits of left-behind/balked passengers.
    """
    arr = [w for w in waits if w is not None and not np.isnan(w)]
    return float(np.mean(arr)) if len(arr) > 0 else 0.0


def compute_p2_left_behind_and_unmet(passengers: Sequence[Any]) -> Tuple[int, int]:
    """
    P2: Left-behind / unmet demand (pax).
    Returns (left_behind_pax, unmet_demand_pax):
      left_behind_pax: passengers who experienced >= 1 left-behind event due to capacity.
      unmet_demand_pax: balked passengers (>20 min wait) + passengers unserved at end of sim.
    """
    left_behind_count = 0
    unmet_count = 0
    for p in passengers:
        lb = getattr(p, "left_behind_count", 0)
        status = getattr(p, "status", "completed")
        if lb > 0:
            left_behind_count += 1
        if status in ("balked", "waiting"):
            unmet_count += 1
    return left_behind_count, unmet_count


def compute_p3_missed_connections(passengers: Sequence[Any]) -> Tuple[int, float]:
    """
    P3: Missed connections (count & %).
    Transferring passengers arriving at hub S03 whose connecting departure was missed.
    Returns (missed_count, missed_rate_percent).
    """
    transferring = [p for p in passengers if getattr(p, "needs_transfer", False)]
    if not transferring:
        return 0, 0.0
    missed = sum(1 for p in transferring if getattr(p, "missed_connection", False))
    rate_pct = (missed / len(transferring)) * 100.0
    return missed, rate_pct


def compute_p4_overcrowded_trips(
    trip_metrics_iterable: Sequence[Any],
) -> Tuple[int, int]:
    """
    P4: Overcrowded trips count:
      hard (>100% rated capacity) and soft (>85% rated capacity).
    Returns (count_gt_100, count_gt_85).
    """
    count_100 = 0
    count_85 = 0
    for tm in trip_metrics_iterable:
        cap = getattr(tm, "capacity", 45)
        max_load = getattr(tm, "max_load", 0)
        if max_load > cap:
            count_100 += 1
        # Soft threshold: strictly > 85% rated capacity
        if max_load > int(math.floor(0.85 * cap)):
            count_85 += 1
    return count_100, count_85


def compute_p5_p95_wait(waits: Sequence[float]) -> float:
    """
    P5: P95 wait (min). Tail experience (95th percentile passenger wait time).
    """
    arr = [w for w in waits if w is not None and not np.isnan(w)]
    return float(np.percentile(arr, 95)) if len(arr) > 0 else 0.0


def compute_p6_fleet_utilization(
    seat_km_used: float,
    seat_km_offered: float,
    vehicle_km: float,
    active_vehicles: int,
) -> Dict[str, float]:
    """
    P6: Fleet utilization ratio (seat-km used / seat-km offered),
    plus vehicle-km and vehicles in service.
    """
    ratio = (seat_km_used / seat_km_offered) if seat_km_offered > 0 else 0.0
    return {
        "fleet_utilization_ratio": round(ratio, 4),
        "seat_km_offered": round(seat_km_offered, 1),
        "seat_km_used": round(seat_km_used, 1),
        "vehicle_km": round(vehicle_km, 2),
        "vehicles_in_service": float(active_vehicles),
    }


def compute_p7_eta_metrics(
    predictions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    P7: ETA MAE and 80% window coverage.
    predictions list of dicts with:
      - 'scheduled_min': float
      - 'eta_p10': float
      - 'eta_p50': float
      - 'eta_p90': float
      - 'actual_arrival_min': float
      - 'stops_away': int (horizon)
    """
    if not predictions:
        return {
            "mae_overall": 0.0,
            "mae_horizon_1": 0.0,
            "mae_horizon_3": 0.0,
            "mae_horizon_5plus": 0.0,
            "coverage_80": 0.0,
            "mean_window_width": 0.0,
            "sample_size": 0,
        }

    errors: list[float] = []
    errors_h1: list[float] = []
    errors_h3: list[float] = []
    errors_h5: list[float] = []
    covered = 0
    widths: list[float] = []

    for p in predictions:
        act = float(p["actual_arrival_min"])
        p50 = float(p["eta_p50"])
        p10 = float(p.get("eta_p10", p50))
        p90 = float(p.get("eta_p90", p50))
        h = int(p.get("stops_away", 1))

        err = abs(p50 - act)
        errors.append(err)

        if h <= 1:
            errors_h1.append(err)
        elif 2 <= h <= 3:
            errors_h3.append(err)
        else:
            errors_h5.append(err)

        if p10 <= act <= p90:
            covered += 1
        widths.append(max(0.0, p90 - p10))

    n = len(predictions)
    return {
        "mae_overall": round(float(np.mean(errors)), 2),
        "mae_horizon_1": round(float(np.mean(errors_h1)), 2) if errors_h1 else round(float(np.mean(errors)), 2),
        "mae_horizon_3": round(float(np.mean(errors_h3)), 2) if errors_h3 else round(float(np.mean(errors)), 2),
        "mae_horizon_5plus": round(float(np.mean(errors_h5)), 2) if errors_h5 else round(float(np.mean(errors)), 2),
        "coverage_80": round((covered / n) * 100.0, 1),
        "mean_window_width": round(float(np.mean(widths)), 2),
        "sample_size": n,
    }


def compute_p8_hard_violations(plan: Union[Plan, dict[str, Any]]) -> int:
    """
    P8: Hard-constraint violations (must be 0 for all evaluated plans).
    Invokes the independent validator validate.validator.get_hard_violations.
    """
    violations = get_hard_violations(plan)
    return len(violations)


def compute_p9_demand_wape(
    actuals: Sequence[float],
    forecasts: Sequence[float],
) -> Tuple[float, float]:
    """
    P9: Demand forecast WAPE = sum(|actual - forecast|) / sum(actual).
    Also returns MAE.
    """
    act = np.asarray(actuals, dtype=float)
    fcst = np.asarray(forecasts, dtype=float)
    if len(act) != len(fcst) or len(act) == 0:
        return 0.0, 0.0

    abs_err = np.abs(act - fcst)
    total_act = float(np.sum(act))
    total_err = float(np.sum(abs_err))
    wape = (total_err / total_act) if total_act > 0 else 0.0
    mae = float(np.mean(abs_err))
    return round(wape, 4), round(mae, 2)


def compute_p10_plan_churn(
    baseline_plan: Union[Plan, dict[str, Any]],
    evaluated_plan: Union[Plan, dict[str, Any]],
) -> Dict[str, int]:
    """
    P10: Plan churn (# changed trips vs published baseline timetable).
    Categorizes into: added, cancelled, retimed (departure shifted), reassigned (different vehicle).
    """
    base_trips = {t.trip_id: t for t in baseline_plan.trips} if isinstance(baseline_plan, Plan) else {t["trip_id"]: t for t in baseline_plan.get("trips", [])}
    eval_trips = {t.trip_id: t for t in evaluated_plan.trips} if isinstance(evaluated_plan, Plan) else {t["trip_id"]: t for t in evaluated_plan.get("trips", [])}

    added = sum(1 for tid in eval_trips if tid not in base_trips)
    cancelled = sum(1 for tid in base_trips if tid not in eval_trips)
    retimed = 0
    reassigned = 0

    for tid, e_trip in eval_trips.items():
        if tid in base_trips:
            b_trip = base_trips[tid]
            e_dep = e_trip.departure_min if isinstance(e_trip, Trip) else e_trip["departure_min"]
            b_dep = b_trip.departure_min if isinstance(b_trip, Trip) else b_trip["departure_min"]
            e_veh = e_trip.vehicle_id if isinstance(e_trip, Trip) else e_trip["vehicle_id"]
            b_veh = b_trip.vehicle_id if isinstance(b_trip, Trip) else b_trip["vehicle_id"]

            if e_dep != b_dep:
                retimed += 1
            if e_veh != b_veh:
                reassigned += 1

    total_churn = added + cancelled + retimed + reassigned
    return {
        "added_trips": added,
        "cancelled_trips": cancelled,
        "retimed_trips": retimed,
        "reassigned_trips": reassigned,
        "total_churn": total_churn,
    }


# ---------------------------------------------------------------------------
# Predeclared Composite Objective Function
# ---------------------------------------------------------------------------

def compute_composite_objective(
    p1_wait: float,
    p2_unmet: float,
    p3_missed: float,
    vehicle_km: float = 0.0,
    departure_shift: float = 0.0,
    plan_churn: float = 0.0,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Computes Section 9.2 composite objective:
      min w_wait*P1 + w_unmet*P2 + w_conn*P3 + w_km*VehicleKm + w_dev*|shift| + w_chg*Churn
    Default weights from config/eval_manifest.yaml:
      unmet: 10.0, connection: 6.0, wait: 1.0, vehicle_km: 0.3, deviation: 0.5, change: 1.5
    """
    w = weights or {
        "unmet": 10.0,
        "connection": 6.0,
        "wait": 1.0,
        "vehicle_km": 0.3,
        "deviation": 0.5,
        "change": 1.5,
    }
    cost = (
        w.get("wait", 1.0) * p1_wait +
        w.get("unmet", 10.0) * p2_unmet +
        w.get("connection", 6.0) * p3_missed +
        w.get("vehicle_km", 0.3) * vehicle_km +
        w.get("deviation", 0.5) * departure_shift +
        w.get("change", 1.5) * plan_churn
    )
    return round(float(cost), 2)
