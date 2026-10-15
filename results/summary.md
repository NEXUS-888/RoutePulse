# RoutePulse Evaluation & Benchmarking Report

> **Evaluation Run Timestamp:** `2026-10-14T08:00:18.250502+00:00`  
> **Master Replications:** `20 stochastic seeds (seeds 1..20)`  
> **Test Split Protocol:** `Locked Days 26..30 (Asserted in code; zero leakage)`  
> **Hard Constraint Gate (P8):** **PASSED** (0 violations across 240 evaluated runs)

## 1. Executive Summary

All figures below are computed from `results/results.json` (paired per-seed comparisons, simulated data, test split only).
- **P1 Mean Passenger Wait:** Reduced by **26.1% to 31.5%** vs Baseline-0 across scenarios (down to 5.2 min in the normal peak).
- **P2 Left-Behind Unmet Demand:** Reduced by **67.7% to 77.2%** vs Baseline-0.
- **P3 Missed Connections at Hub S03:** Reduced by **55.2% to 60.1%** vs Baseline-0.
- **P7 ETA Accuracy:** Conformal ETA achieves **0.8 min MAE** vs 3.19 min for the timetable (**74.9% lower error**) and 3.14 min for last-delay carry-forward (**74.5% lower**), with **79.7% empirical coverage** of the 80% window.
- **P8 Hard-Constraint Safety Gate:** **0 violations** in all 240 evaluated runs.

---

## 2. Predeclared Benchmark Summary Table (Mean ± 95% CI)

| System | Scenario | P1: Mean Wait (min) | P2: Left-Behind (pax) | P3: Missed Conn (#) | P8: Hard Violations |
|---|---|---|---|---|---|
| **Baseline-0** | S0 (Normal) | 7.3 ± 0.3 | 47.0 ± 2.7 | 13.7 ± 1.2 | **0** |
| **Baseline-1** | S0 (Normal) | 6.1 ± 0.2 | 33.5 ± 2.1 | 11.9 ± 1.2 | **0** |
| **RoutePulse** | S0 (Normal) | 5.2 ± 0.1 | 13.4 ± 0.7 | 6.2 ± 0.7 | **0** |
| **Baseline-0** | S1 (Traffic) | 9.3 ± 0.4 | 89.2 ± 4.5 | 28.8 ± 1.8 | **0** |
| **Baseline-1** | S1 (Traffic) | 8.2 ± 0.4 | 59.7 ± 4.1 | 21.2 ± 1.3 | **0** |
| **RoutePulse** | S1 (Traffic) | 6.8 ± 0.2 | 28.9 ± 2.6 | 12.9 ± 0.9 | **0** |
| **Baseline-0** | S2 (Vehicle Out) | 10.4 ± 0.7 | 110.0 ± 6.7 | 36.3 ± 2.2 | **0** |
| **Baseline-1** | S2 (Vehicle Out) | 8.7 ± 0.7 | 66.6 ± 5.9 | 23.5 ± 1.9 | **0** |
| **RoutePulse** | S2 (Vehicle Out) | 7.1 ± 0.4 | 34.0 ± 3.3 | 14.5 ± 0.9 | **0** |
| **Baseline-0** | S3 (Demand Surge) | 8.7 ± 0.5 | 97.1 ± 5.6 | 23.8 ± 1.5 | **0** |
| **Baseline-1** | S3 (Demand Surge) | 7.7 ± 0.3 | 59.9 ± 4.6 | 17.8 ± 1.1 | **0** |
| **RoutePulse** | S3 (Demand Surge) | 6.1 ± 0.3 | 22.2 ± 2.1 | 9.9 ± 0.7 | **0** |

---

## 3. Paired Differences & Statistical Significance (RoutePulse vs Baselines)

All metrics evaluated pairwise per seed ($N=20$) using two-sided Student's paired t-tests.

| Scenario | Comparison | P1 Wait Delta (min) | P2 Left-Behind Delta (pax) | P3 Missed Conn Delta (#) | p-value (Wait) |
|---|---|---|---|---|---|
| **S0 (Normal)** | RoutePulse vs Baseline-0 | -2.17 (+29.6%) | -33.6 (+71.5%) | -7.6 (+55.2%) | **p < 0.001** |
| **S0 (Normal)** | RoutePulse vs Baseline-1 | -0.97 (+15.8%) | -20.1 (+59.9%) | -5.7 (+48.1%) | **p < 0.001** |
| **S1 (Traffic Delay)** | RoutePulse vs Baseline-0 | -2.42 (+26.1%) | -60.4 (+67.7%) | -15.9 (+55.2%) | **p < 0.001** |
| **S1 (Traffic Delay)** | RoutePulse vs Baseline-1 | -1.32 (+16.2%) | -30.8 (+51.7%) | -8.3 (+39.0%) | **p < 0.001** |
| **S2 (Vehicle Breakdown)** | RoutePulse vs Baseline-0 | -3.29 (+31.5%) | -76.0 (+69.1%) | -21.8 (+60.1%) | **p < 0.001** |
| **S2 (Vehicle Breakdown)** | RoutePulse vs Baseline-1 | -1.56 (+17.9%) | -32.6 (+49.0%) | -9.0 (+38.2%) | **p < 0.001** |
| **S3 (Auditorium Surge)** | RoutePulse vs Baseline-0 | -2.61 (+30.0%) | -74.9 (+77.2%) | -13.9 (+58.4%) | **p < 0.001** |
| **S3 (Auditorium Surge)** | RoutePulse vs Baseline-1 | -1.64 (+21.2%) | -37.7 (+63.0%) | -7.9 (+44.3%) | **p < 0.001** |

---

## 4. Operational KPIs: P4 Overcrowding, P5 Tail Experience, P6 Fleet Utilization

| Metric | Baseline-0 | Baseline-1 (Reactive) | RoutePulse (Optimized) | Delta vs Baseline-0 |
|---|---|---|---|---|
| **P4: Overcrowded Trips (>85% cap)** | 8.2 trips | 4.8 trips | **2.0 trips** | **-76.0%** |
| **P5: P95 Passenger Wait (tail)** | 14.6 min | 12.7 min | **10.4 min** | **-29.0%** |
| **P6: Fleet Utilization Ratio** | 78.6% | 79.9% | **82.7%** | **+5.2%** |
| **P10: Plan Churn (# changed trips)** | 0 trips | 2 trips | **7 trips** | **n/a** |

*Scenario S0 (Normal Peak), mean over all replications. Utilization rises because RoutePulse deliberately adds reserve capacity; extra vehicle-km are the cost of the improvement.*

---

## 5. P7: ETA Accuracy and 80% Conformal Window Coverage

| ETA Method | Overall MAE (min) | MAE: 1 Stop Away | MAE: 3 Stops Away | MAE: 5+ Stops Away | 80% Window Coverage | Mean Width (min) |
|---|---|---|---|---|---|---|
| **Baseline-0 (Timetable)** | 3.19 min | 1.01 min | 3.12 min | 9.68 min | 42.0% | 3.0 min |
| **Baseline-1 (Last-Delay Carry-Forward)** | 3.14 min | 1.01 min | 3.09 min | 9.69 min | 49.5% | 4.0 min |
| **RoutePulse (Conformal Quantile)** | **0.8 min** | **0.69 min** | **0.84 min** | **1.05 min** | **79.7%** | **2.56 min** |

> **Conformal verification:** empirical coverage of **79.7%** is within the predeclared 78–82% target interval (mean window width 2.56 min).

---

## 6. P9: Demand Forecasting Performance (Test Split)

| Demand Model | WAPE | MAE (pax/slot) | Out-of-Sample Performance |
|---|---|---|---|
| **Baseline-0 (Historical Mean)** | 28.6% | 2.29 pax | Baseline profile; misses shocks |
| **RoutePulse (Poisson Nowcast + Event Multiplier)** | **23.9%** | **1.91 pax** | **+16.4% WAPE Reduction** |

---

## 7. Architectural Ablation Study (design-time estimates, not re-run)

> **Caveat:** the ablation rows are estimates defined in `eval/report.py::generate_ablation_data`; each variant was **not** re-simulated. Treat them as illustrative of expected component impact, not as measured results.

| Model Variant | Mean Wait | Left-Behind | Missed Conn | ETA MAE | Demand WAPE | Impact of Ablation |
|---|---|---|---|---|---|---|
| **Full RoutePulse** | 5.12 min | 12.4 | 6.2 | 1.42 min | 14.8% | Reference (Best) |
| **w/o Live ETA Adjustment** | 5.24 min | 12.8 | 6.4 | 2.18 min | 14.8% | +0.76 min ETA MAE (+53.5%) |
| **w/o Connection Constraint** | 5.68 min | 13.1 | 18.7 | 1.42 min | 14.8% | +12.5 missed connections (+201.6%) |
| **w/o Demand Nowcast** | 6.35 min | 31.8 | 9.4 | 1.42 min | 28.6% | +19.4 left-behind pax (+156.5%), +93% WAPE |

---

## 8. Objective Weight Sensitivity Analysis

| Operator Policy Profile | Baseline-0 Cost | Baseline-1 Cost | RoutePulse Cost | Cost Savings vs B0 | Cost Savings vs B1 |
|---|---|---|---|---|---|
| **Default Balanced** | 654.2 | 500.3 | **251.3** | **+61.6%** | **+49.8%** |
| **Passenger Wait Priority** | 529.5 | 404.1 | **206.4** | **+61.0%** | **+48.9%** |
| **Hub Connection Guarantee** | 688.2 | 545.5 | **283.5** | **+58.8%** | **+48.0%** |
| **Fleet Operational Efficiency** | 560.9 | 485.0 | **350.6** | **+37.5%** | **+27.7%** |

---

## 9. Comparison Against Predeclared Stretch Targets (Section 9.3)

| Target Metric | Predeclared Target | RoutePulse Actual | Target Achieved? |
|---|---|---|---|
| **Passenger Wait Reduction** | -20% | **-26.1% to -31.5%** | **YES** |
| **Left-Behind Pax Reduction** | -50% | **-67.7% to -77.2%** | **YES** |
| **Missed Connections Reduction** | -40% | **-55.2% to -60.1%** | **YES** |
| **ETA MAE vs Timetable** | -30% | **-74.9%** | **YES** |
| **ETA MAE vs Carry-Forward** | -10% | **-74.5%** | **YES** |
| **80% Window Coverage** | 78% – 82% | **79.7%** | **YES** |
| **Hard Constraint Violations** | 0 | **0** | **YES** |
| **Optimizer Solve Time** | < 10 s | asserted in `tests/test_optimizer.py` | see test |

---
*Generated by RoutePulse Evaluation Engine (`eval/run_eval.py`). All artifacts committed under reproducible master seeds.*
