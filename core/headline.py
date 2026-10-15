"""
Headline evaluation numbers, derived from measured results.

Pure Python on purpose (no numpy/pandas): the deployed API (e.g. on Vercel) runs with a slim
dependency set and must be able to import this without the analytics stack.
"""
from __future__ import annotations

from typing import Any, Dict


def pct_range(paired: Dict[str, Any], metric: str, vs: str = "rp_vs_b0") -> tuple[float, float]:
    """Min and max measured % improvement of `metric` across all scenarios."""
    vals = [
        sc.get(vs, {}).get(metric, {}).get("percent_improvement")
        for sc in paired.values()
    ]
    vals = [v for v in vals if v is not None]
    return (min(vals), max(vals)) if vals else (0.0, 0.0)


def kpi_mean(detailed: Dict[str, Any], scenario: str, system: str, metric: str) -> float | None:
    v = detailed.get(scenario, {}).get(system, {}).get(metric)
    if isinstance(v, dict):
        return v.get("mean")
    return float(v) if isinstance(v, (int, float)) else None


def compute_headline(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Headline numbers shown in the UI landing page, the before/after slider and summary.md.
    Everything is derived from the measured results (paired per-seed comparisons); nothing is typed in.
    """
    paired = results.get("paired_differences", {}) or {}
    summary_table = results.get("summary_table", []) or []
    eta_m = results.get("eta_metrics", {}) or {}
    replications = int(results.get("replications", 20) or 20)

    w_lo, w_hi = pct_range(paired, "p1_mean_wait_min")
    lb_lo, lb_hi = pct_range(paired, "p2_left_behind_pax")
    mc_lo, mc_hi = pct_range(paired, "p3_missed_connections_count")

    def _s0(metric: str) -> Dict[str, float]:
        d = (paired.get("S0", {}).get("rp_vs_b0", {}) or {}).get(metric, {}) or {}
        return {
            "b0": round(d.get("baseline_mean", 0.0), 1),
            "rp": round(d.get("system_mean", 0.0), 1),
            "pct": round(d.get("percent_improvement", 0.0), 1),
        }

    wait, lb, mc = _s0("p1_mean_wait_min"), _s0("p2_left_behind_pax"), _s0("p3_missed_connections_count")

    rp_eta = eta_m.get("routepulse", {}) or {}
    b0_eta = eta_m.get("baseline-0", {}) or {}
    eta_pct = 0.0
    if rp_eta.get("mae_overall") and b0_eta.get("mae_overall"):
        eta_pct = round((1 - rp_eta["mae_overall"] / b0_eta["mae_overall"]) * 100, 1)

    return {
        "replications": replications,
        "runs": len(summary_table) * replications,
        "hard_violations": sum(int(r.get("hard_violations", 0)) for r in summary_table),
        "wait_reduction_pct": [round(w_lo, 1), round(w_hi, 1)],
        "left_behind_reduction_pct": [round(lb_lo, 1), round(lb_hi, 1)],
        "missed_conn_reduction_pct": [round(mc_lo, 1), round(mc_hi, 1)],
        "s0": {
            "wait_b0": wait["b0"], "wait_rp": wait["rp"], "wait_reduction_pct": wait["pct"],
            "left_behind_b0": lb["b0"], "left_behind_rp": lb["rp"], "left_behind_reduction_pct": lb["pct"],
            "missed_b0": mc["b0"], "missed_rp": mc["rp"], "missed_reduction_pct": mc["pct"],
        },
        "eta": {
            "mae_rp": rp_eta.get("mae_overall", 0.0),
            "mae_b0": b0_eta.get("mae_overall", 0.0),
            "reduction_pct": eta_pct,
            "coverage_80": rp_eta.get("coverage_80", 0.0),
        },
    }
