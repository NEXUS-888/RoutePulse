# RoutePulse — Architecture, System Design & Build Instructions

> **Audience:** Antigravity (the building agent).
> **Hackathon deadline: 22:00 today. Hard feature freeze: 20:30. Submission package ready: 21:15. Upload buffer: 21:15–21:45. Do not touch code after 21:45.**
> **Problem:** PS 02 — Optimise campus transport under real constraints (estimate arrival windows, forecast demand, detect capacity/connection/schedule problems, recommend feasible adjustments, prove improvement vs a frozen baseline on common simulated data).

---

## 0. Instructions to Antigravity (READ FIRST)

1. Read this entire file before writing code. Do not ask clarifying questions; where something is unspecified, use the defaults in this document and record the choice in `docs/ASSUMPTIONS.md`.
2. **Contracts first.** In the first 45 minutes, create and freeze: Pydantic schemas (`core/schemas.py`), the OpenAPI contract (Section 10), the config file (`config/default.yaml`, Appendix A) and sample JSON fixtures. Then parallelise work across agents (Section 14). Never change a frozen contract without updating the fixtures and tests together.
3. **Work in vertical slices, always keeping a runnable demo.** After every phase, `make demo` must work end to end. A working simple system beats a broken ambitious one.
4. **Offline-first.** The demo must run with no internet (venue wifi is unreliable). No CDN-only assets, no hosted map tiles as a hard dependency (Section 11 specifies an offline SVG map with optional tiles).
5. **Determinism.** Every random process takes an explicit seed. Same seed gives byte-identical data and metrics. Master seed: `20261014`.
6. **The hard-constraint validator is independent from the optimizer.** The optimizer never certifies its own output. Everything that is shown as a "plan" must pass `validator.validate(plan)` with zero hard violations, or it is not shown as a recommendation.
7. **Honesty rule.** Report whatever the evaluation produces. Do not tune on the test split. Do not hide metrics where we lose. Judges reward credibility.
8. Use the skills, agents and MCP servers listed in Section 14 where they are available.
9. Commit after every working step with clear messages. Tag `eval-freeze` when the evaluation manifest is frozen (Section 9).

---

## 1. Problem → Judging Criteria → Design Decisions

| Criterion (weight) | What judges check | Design response |
|---|---|---|
| Plan feasibility & constraint compliance (20) | Zero invalid capacity allocations, impossible trips, schedule conflicts | Independent `validator` with a published list of hard constraints (H1–H12, Section 8.6); property-based tests; a "violations = 0" badge on every plan; baseline also validated |
| ETA quality (15) | Error vs simulated ground truth, consistent metric | Two honest baselines (timetable, last-delay carry-forward); MAE/MedAE by horizon, interval coverage and sharpness; conformally calibrated 80% windows |
| Demand & capacity handling (15) | Overcrowding, unmet demand, feasible allocation | Stop×15-min demand forecast with P50/P80 bands; load simulation with left-behind passengers; conflict detector |
| Operational improvement (20) | Measured change vs baseline in a predeclared objective | Frozen baseline + frozen eval windows + 20 stochastic replications + CIs; headline KPIs predeclared |
| Robustness to disruptions (10) | Quality of recommendations under change | 3 disruption scenarios + rolling-horizon re-optimisation with minimal-change penalty |
| Engineering & reproducibility (10) | Reliable data handling, reproducible scenarios | Seeded generator, data hashes, `make all`, Docker, tests, schema validation at every boundary |
| Explainability & commercial relevance (10) | Clear trade-offs, credible operator workflow | Recommendation cards with reason codes, binding constraints, before/after deltas, alternatives rejected; operator Accept/Reject/What-if flow; GTFS import/export; SaaS model |

---

## 2. Perspectives Analysed (and what each forces on the design)

| Perspective | Concern | Consequence |
|---|---|---|
| **Judge** | Can I verify the claims quickly? | One-page results table, `make eval` reproduces it, violation counter, side-by-side baseline vs proposed |
| **Transport operator** | Will this change my day, safely? | Human-in-the-loop: system recommends, operator approves. Minimal-change penalty so schedules do not churn. Every action has cost and risk shown |
| **Student** | When does my bus come? Can I make my connection? | ETA as a window ("arrives 08:14–08:19"), confidence, transfer feasibility, accessible alternatives |
| **Driver** | Is the plan humane and legal? | Layover, break and continuous-driving constraints are hard constraints; no impossible turnarounds |
| **Accessibility user** | Is there a ramp-equipped vehicle? | Accessible vehicles flag; hard constraint of minimum accessible service per route-hour; accessible-only routing filter |
| **Engineer / ops** | GPS is noisy; data is missing; models drift | Map-matching + smoothing, dropout handling, cold-start fallbacks, drift monitor, graceful degradation to baseline ETA |
| **Business / buyer** | Why pay for this? | Fleet-hours saved, complaints reduced, overcrowding incidents avoided; GTFS-compatible so it plugs into existing systems |
| **Risk / ethics / privacy** | Passenger data | Only aggregate anonymous counts (APC); no personal IDs; documented in `docs/PRIVACY.md` |
| **Skeptic** | "Your simulator is rigged." | Baselines are strong and documented; ground-truth model differs structurally from the ETA model's features; test split untouched; seeds shown |

---

## 3. Scope Tiers and Cut-Lines

Build in this order. If time runs short, cut from the bottom. **P0 is the submission.**

**P0 — Mandatory MVP (must be demo-ready by 19:00)**
- Data model + synthetic generator + frozen scenarios (normal + 3 disruptions)
- GPS processing → ETA windows with stated assumptions
- Load simulation + conflict detector (overcrowding, capacity violations, missed connections, schedule conflicts)
- Optimizer producing ≥ 3 feasible recommendation types with trade-off explanation
- Independent validator
- Evaluation harness: baseline vs proposed with measurable KPIs
- Operator dashboard (map, ETA board, alerts, recommendations, comparison)

**P1 — High-value extensions (target by 20:00)**
- Demand forecasting (LightGBM + nowcast correction)
- Disruption re-optimisation (rolling horizon)
- Student view with alternatives + accessibility toggle
- GTFS export

**P2 — Only if ahead of schedule (stretch)**
- Event-schedule demand features (already in generator; use in model), what-if sliders
- Edge APC ingest endpoint + mock counter script
- Optional online map tiles

---

## 4. System Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │               OPERATOR / STUDENT UI           │
                         │  React + Vite + TS · SVG campus map · charts  │
                         └───────────────▲──────────────────▲───────────┘
                                 REST/JSON│            SSE (live pings,
                                          │            ETAs, alerts)
┌──────────────────────────────────────────┴──────────────────┴────────────┐
│                          API GATEWAY  (FastAPI)                           │
│   /network /eta /demand /alerts /plans /recommendations /eval /ingest     │
└──▲────────▲─────────────▲────────────────▲───────────────▲───────────▲──┘
   │        │             │                │               │           │
┌──┴───┐ ┌──┴────────┐ ┌──┴─────────┐ ┌────┴────────┐ ┌────┴─────┐ ┌───┴─────────┐
│ DATA │ │ GPS/ETA   │ │ DEMAND     │ │ LOAD SIM &  │ │ OPTIMIZER│ │ VALIDATOR   │
│ LAYER│ │ ENGINE    │ │ FORECASTER │ │ CONFLICT    │ │ (CP-SAT +│ │ (hard       │
│      │ │ map-match │ │ LightGBM + │ │ DETECTOR    │ │ heuristic│ │ constraints,│
│      │ │ + profile │ │ nowcast    │ │ (discrete-  │ │ + rolling│ │ independent)│
│      │ │ + quantile│ │            │ │ event)      │ │ horizon) │ │             │
└──▲───┘ └───▲───────┘ └─────▲──────┘ └──────▲──────┘ └────▲─────┘ └──────▲──────┘
   │         │               │               │             │              │
┌──┴─────────┴───────────────┴───────────────┴─────────────┴──────────────┴──┐
│   STORAGE: Parquet (traces, APC, trips) + DuckDB (queries) + YAML configs   │
└──▲─────────────────────────────────────────────────────────────────────────┘
   │
┌──┴──────────────────────────────┐    ┌────────────────────────────────────┐
│ SYNTHETIC WORLD GENERATOR        │    │ EVALUATION HARNESS                  │
│ network · demand · traffic · GPS │───▶│ baseline vs proposed · N seeds · CI │
│ ground truth · disruptions       │    │ results.json + report.md + charts   │
└──────────────────────────────────┘    └────────────────────────────────────┘
        ▲
        │  Replayer service streams recorded pings at accelerated speed
        │  (stands in for the live GPS feed; same schema as a real feed adapter)
```

**Key design principle:** *Sense → Estimate → Detect → Decide → Verify → Explain.*
1. **Sense:** ingest GPS pings and passenger counts (simulated feed, real-feed-compatible adapter).
2. **Estimate:** ETA windows and demand forecasts.
3. **Detect:** simulate the plan forward against forecast demand, flag problems.
4. **Decide:** optimizer proposes adjustments under hard constraints.
5. **Verify:** independent validator + stochastic simulation confirm feasibility and benefit.
6. **Explain:** recommendation card with trade-offs; operator approves.

---

## 5. Tech Stack and Rationale

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Fast to build; best ecosystem for optimisation + ML |
| Env | `uv` (or pip + `requirements.lock`) | Reproducible installs |
| Schemas | Pydantic v2 | Single source of truth; validate at all boundaries |
| API | FastAPI + Uvicorn, SSE for live stream | Typed, auto OpenAPI, simple |
| Storage | Parquet + DuckDB (embedded) | Zero infra, fast analytics; mention Postgres/TimescaleDB for production |
| Numerics | numpy, pandas, scipy | Standard |
| Simulation | Custom discrete-event simulator (heapq), no heavy framework | Control, speed, determinism |
| ETA/Demand ML | LightGBM (quantile + Poisson objectives), scikit-learn | Strong on small tabular data, fast to train |
| Optimisation | OR-Tools CP-SAT (primary), greedy + local search (fallback) | Explicit constraints, anytime solution with time limit |
| Frontend | React + Vite + TypeScript, Recharts, **custom SVG campus map** (Leaflet optional) | Offline-safe; fast to iterate |
| Testing | pytest, hypothesis (property tests), Playwright (UI smoke) | Judges value reproducibility |
| Packaging | Docker Compose (api + web), Makefile | One-command run |
| Interop | GTFS static export, GTFS-RT-shaped ingest | Real-world adoption story |

Fallback if frontend time is critical: Streamlit single-file UI reading the same API. Decide at the Phase 2 checkpoint; do not switch later.

---

## 6. Data Model

All entities are Pydantic models in `core/schemas.py`, persisted as Parquet/YAML. Times are minutes-from-midnight (int) or ISO-8601 in API payloads. Coordinates: local metric (x, y metres) as truth + derived WGS84 lat/lon around origin (12.9716, 77.5946, fictional campus).

| Entity | Key fields |
|---|---|
| `Stop` | `stop_id`, `name`, `x`, `y`, `lat`, `lon`, `is_hub`, `accessible`, `capacity_waiting` (optional) |
| `Route` | `route_id`, `name`, `type` (`loop` or `linear`), `stop_sequence[]`, `polyline[]` (x,y), `segment_lengths_m[]`, `free_flow_speed_mps` |
| `Vehicle` | `vehicle_id`, `type` (`bus`/`minibus`), `capacity` (rated, hard limit), `seated`, `accessible`, `depot_stop`, `available_from`, `available_to` |
| `Trip` | `trip_id`, `route_id`, `direction`, `vehicle_id`, `departure_min`, `scheduled_stop_times{stop_id: min}` |
| `Plan` | `plan_id`, `name`, `window`, `trips[]`, `vehicle_blocks{vehicle_id: [trip_id…]}`, `metadata` |
| `GpsPing` | `vehicle_id`, `t_sec`, `lat`, `lon`, `speed_mps`, `heading` |
| `ApcRecord` | `trip_id`, `stop_id`, `boardings`, `alightings`, `load_after` |
| `DemandObs` | `stop_id`, `slot_start`, `arrivals` (generated), `od_destination` |
| `Event` | `event_id`, `venue_stop_id`, `start_min`, `end_min`, `attendance`, `outflow_profile` |
| `Transfer` | `from_route`, `to_route`, `hub_stop_id`, `min_transfer_min` (4) |
| `ServiceRules` | `min_headway`, `max_headway_peak`, `max_headway_offpeak`, `min_layover`, `max_continuous_drive_min`, `min_break_min`, `max_departure_shift`, `min_accessible_per_route_hour` |
| `Scenario` | `scenario_id`, `day`, `window`, `disruptions[]`, `seed`, `description` |
| `Disruption` | `type` (`traffic`/`vehicle_out`/`demand_spike`), `params`, `start_min`, `end_min` |
| `Recommendation` | see Section 8.7 |
| `Violation` | `code` (H1…), `severity` (`hard`/`soft`), `entity`, `time`, `detail` |

**Data quality rules (enforced by `data/validate_dataset.py`):** stop IDs referenced exist; route polylines pass within 25 m of their stops; segment lengths sum to polyline length ±1%; capacities positive; timestamps monotonic per vehicle; no ping teleports above 40 m/s; APC `load_after` consistent with boardings/alightings.

---

## 7. Synthetic World Specification (frozen defaults)

The generator (`sim/generate_world.py`) produces **30 simulated service days** (06:30–22:00). Same code path produces training data, validation, and test.

### 7.1 Network (defaults; configurable)
- **14 stops:** S01 Main Gate, S02 Admin Block, S03 **Central Hub** (transfer), S04 Library, S05 Engineering, S06 Science, S07 Auditorium, S08 Hostel A, S09 Hostel B, S10 Food Court, S11 Sports Complex, S12 Research Park, S13 Metro Station (≈1.8 km off-campus), S14 Medical Centre. Place on a plausible 2.5 km × 2 km layout with road-like polylines (piecewise, not straight lines).
- **4 routes:**
  - R1 Main Loop (loop): S01→S02→S03→S04→S05→S06→S07→S01 (~22 min)
  - R2 Hostel Express (loop): S03→S10→S08→S09→S03 (~14 min)
  - R3 Metro Connector (linear, bidirectional): S13↔S01↔S02↔S03 (~12 min one way)
  - R4 Research/Sports Shuttle (linear, bidirectional): S03↔S14↔S12↔S11 (~13 min one way)
- **Transfers at S03:** min transfer time 4 min (walk + boarding buffer).
- **Fleet: 10 vehicles** — B1–B6 buses (capacity 45, B1 and B2 accessible), M1–M4 minibuses (capacity 22, M1 accessible). Depot at S01.

### 7.2 Baseline timetable (documented, frozen)
Fixed all-day headways, static vehicle-to-route assignment (typical real campus practice): R1≈12 min, R2≈15 min, R3≈12 min, R4≈30 min; the generator derives exact headways so the baseline uses 8–9 of 10 vehicles, leaving ≥1 idle reserve. Written to `config/baseline_plan.json` and **hashed**.

### 7.3 Traffic / travel-time ground truth
Segment time = `length / free_flow_speed × congestion(t, segment) × LogNormal(0, 0.12)` plus intersection delay events (Poisson, 2–25 s). `congestion(t)` has a morning bump (07:45–09:15, ×1.25–1.4 on gate and metro corridor), an evening bump (16:45–18:30, ×1.2–1.35), and weekday variation (Friday ×0.95). Dwell time = `max(6, 5 + 1.4·boardings + 0.8·alightings)` seconds. **Note for realism:** the ground-truth process includes dwell coupling to passenger load and day-level random "bad day" factors, which a simple profile-based ETA cannot see — that is what the learned residual and live-delay correction must capture.

### 7.4 Demand ground truth
Per stop and minute, Poisson arrivals with rate `λ = base(stop) × profile(time) × weekday × event(t) × dayNoise`. Profile peaks follow class changes (arrivals at :50/:00 surges, morning arrival wave 07:45–09:30 at S13/S01, evening wave 16:30–18:30 outbound, meal peaks at S10 around 12:30 and 19:30). Origin–destination matrix per stop pair (heavier flow to/from S03 and S13). Roughly 6,000 boardings/day; morning peak 07:30–09:30 produces **15–25% of baseline peak trips exceeding rated capacity on R3** and some on R1 — baseline must visibly struggle but not absurdly. Passengers board the first vehicle with space (FIFO); passengers waiting > 20 min balk (counted as **unmet demand**). ~25% of itineraries involve a transfer at S03 with a connection requirement.

### 7.5 GPS traces
10-second pings; position noise σ = 8 m Gaussian (with 2% outliers at 40–80 m); 3% random dropout; occasional 30–90 s outage bursts (≈2 per vehicle-day); reported speed noise σ = 0.7 m/s. Output Parquet, schema `GpsPing`.

### 7.6 Events
5 recurring events across the 30 days: one evening auditorium event per test-adjacent day (e.g., 17:30 end, attendance 600–1,200 at S07), one fest day with all-day load elevation. Published in `events.csv` so forecasters can use it.

### 7.7 Splits and windows (**declared now, frozen at git tag `eval-freeze`**)
| Split | Days | Use |
|---|---|---|
| Train | 1–20 | ETA profiles, demand model fit |
| Validation | 21–25 | Hyperparameters, conformal calibration |
| **Test (locked)** | 26–30 | Only touched by `make eval` |

Evaluation windows (on test days): **W1 = 07:30–10:30 (morning peak)** and **W2 = 16:30–19:30 (evening peak)**.

### 7.8 Scenarios (all on test days)
| ID | Name | Definition |
|---|---|---|
| **S0** | Normal operation | Days 26–30, no disruptions |
| **S1** | Traffic delay | Day 27: travel-time ×1.35 on the Metro corridor + Main Gate segments, 08:00–09:30 |
| **S2** | Vehicle unavailable | Day 28: bus B2 out of service from 08:15 to end of W1; reserve vehicles available |
| **S3** | Demand spike | Day 29: auditorium event ends 17:30, +1,000 passengers surge at S07 over 25 min, 3× baseline arrival at S07 for the hour |
| (S4, optional) | Combined | Day 30: S1 + S3 |

Each scenario runs **20 stochastic replications** (seeds 1–20) that vary arrival noise, travel-time noise, and dwell noise while holding the "world" fixed.

---

## 8. Core Modules

### 8.1 Data layer (`core/`, `data/`)
- Loaders and writers for Parquet/YAML; DuckDB views for fast aggregation (`v_segment_times`, `v_apc_by_slot`).
- `validate_dataset.py` enforces the rules in Section 6.
- `gtfs_export.py` writes `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt` (P1). `gtfs_rt_adapter.py` maps GTFS-RT-style VehiclePosition to `GpsPing` (documented interface; stub OK).

### 8.2 GPS processing → progress-along-route (`eta/gps_processing.py`)
1. **Map matching (lightweight HMM / Viterbi on 1-D progress):** project each ping onto the vehicle's route polyline; candidate progress values `s`; emission cost = distance to polyline; transition cost penalises backward motion and implausible jumps (`|Δs| > v_max·Δt`). Output monotone `s(t)`.
2. **Smoothing:** 1-D constant-velocity Kalman filter on `s(t)`; handles dropouts by prediction with growing variance. Flag segments where gap > 60 s as `low_confidence`.
3. **Stop events:** arrival = first time `s` enters the stop's 25 m geofence (interpolated); departure = last time within it; dwell = difference. Also emit segment traversal times between consecutive stops.
4. **Output:** `segment_times` table (vehicle, trip, segment, entry time, duration, quality flag).

### 8.3 ETA engine (`eta/`)
**Goal:** for any vehicle and downstream stop, produce `{eta_p10, eta_p50, eta_p90}` (the arrival *window*), confidence and reasons.

Methods (three levels, evaluated against each other):
- **B0 Timetable ETA (baseline):** scheduled time.
- **B1 Last-delay carry-forward (strong baseline):** scheduled time + current observed delay.
- **RoutePulse ETA:**
  1. *Historical profile:* median and spread of segment times by `(segment, 15-min bucket, day type)` with shrinkage to route-level and segment-level means for sparse buckets.
  2. *Live adjustment:* online delay ratio `ρ` = exponentially weighted ratio of observed/expected segment time over the last 2–3 segments; applied to downstream segments with decay `ρ_k = 1 + (ρ−1)·γ^k` (γ = 0.85).
  3. *Dwell prediction:* expected boardings at upcoming stops from the demand forecast and the live load → predicted dwell.
  4. *Residual quantile model:* LightGBM quantile regression (0.1, 0.5, 0.9) on remaining stops, time bucket, current delay, ρ, load, GPS quality flag, congestion indicators, weekday. Predicts the residual of the profile+live estimate.
  5. *Conformal calibration:* split-conformal on validation days to widen/narrow `[q10, q90]` so empirical coverage ≈ 80%.
  6. *Fallbacks:* if GPS stale > 120 s → degrade to B1 with widened window and "stale GPS" flag; if no history → timetable window.

**Assumptions to list explicitly in `docs/ASSUMPTIONS.md` and in the UI info panel:** vehicles follow fixed polylines; no unplanned detours; dwell depends on boarding counts; traffic regime changes slowly relative to the 3-segment look-back; GPS error ≤ 80 m 98% of the time; stop events defined by 25 m geofence.

**ETA metrics (consistent across all methods):** MAE and median AE of p50 vs ground-truth arrival, bucketed by horizon (next stop, 3 stops, 5+ stops); **window coverage** (target 80%, accept 75–85%); **mean window width**; **interval (Winkler) score**; % of "late by > 3 min" misses. Win condition: lower MAE than B1 and B0 *at comparable or better coverage*.

### 8.4 Demand forecaster (`demand/`) — P1
- **Target:** boardings (arrivals) per `(stop, 15-min slot)`, plus OD split.
- **Features:** hour/minute, weekday, stop ID, route, lagged same-slot values (previous days), rolling mean, event indicator and expected attendance with time-since-event-end, class-change proximity (minutes to :00/:50), weather proxy (optional/none).
- **Model:** LightGBM Poisson objective for the mean; negative-binomial dispersion fit on validation to derive **P50/P80/P90** bands; baseline = mean of same stop-slot-weekday.
- **Nowcast correction:** real-time multiplier `m = (observed last 30 min + ε) / (predicted last 30 min + ε)` clipped to [0.7, 1.8], applied with decay over the next 60 min.
- **Metrics:** WAPE, MAE, bias, peak-slot recall (does it flag the true top 10% slots?), pinball loss at 0.8, event-slot error separately.
- **Fallback if model not ready:** historical mean + event multiplier (still passes MVP).

### 8.5 Load simulator and conflict detector (`sim/`, `detect/`)
**Discrete-event simulator** (`sim/engine.py`): given a `Plan`, a demand realisation (or forecast quantile), and travel-time model (ground truth for evaluation, forecast for planning), simulate every trip: arrivals queue at stops; vehicle arrives; alighting first, then boarding up to capacity (FIFO); left-behind passengers continue waiting; patience limit 20 min; transfers tracked; outputs per-trip loads, per-passenger wait, left-behind counts, missed connections, vehicle-km, seat-km used.

**Conflict detector** consumes simulator output (using P80 demand when planning, realised demand when evaluating) and emits typed alerts:
| Code | Alert | Rule |
|---|---|---|
| A1 | Overcrowding (soft) | load ≥ 85% of capacity at any stop departure |
| A2 | Capacity violation (hard-risk) | demand exceeds rated capacity → passengers left behind |
| A3 | Unmet demand | left-behind or balked passengers > threshold per stop-hour |
| A4 | Missed connection | arrival at hub after connecting departure − min transfer time |
| A5 | Schedule conflict | one vehicle assigned to overlapping trips, or insufficient layover |
| A6 | Bunching / gap | headway < 40% or > 160% of planned |
| A7 | Service gap | headway above `max_headway`, or no accessible vehicle in a route-hour |
| A8 | Vehicle unavailable | assigned vehicle outside availability |

Each alert carries a severity score and the affected passenger estimate.

### 8.6 Hard-constraint validator (`validate/validator.py`) — **independent module**
Pure function `validate(plan, fleet, rules, travel_time_model) → list[Violation]`. It must not import optimizer code. **Published hard constraints:**

| ID | Constraint |
|---|---|
| H1 | Every trip has exactly one assigned vehicle available at that time |
| H2 | A vehicle cannot run two trips that overlap in time |
| H3 | Minimum layover (4 min) between consecutive trips of a vehicle |
| H4 | Vehicle continuity: next trip starts at the stop where the previous trip ended, or deadhead time to the next start is feasible |
| H5 | Departure within operating hours (06:30–22:00) |
| H6 | Fleet size: concurrent vehicles in use ≤ vehicles available |
| H7 | Headway on each route-direction ≥ min_headway (3 min) and ≤ max_headway (12 peak / 20 off-peak) |
| H8 | Departure shift from published baseline ≤ 5 min for retimed trips; added trips are allowed within H1–H7 |
| H9 | Driver rules: ≤ 3.5 h continuous driving, then ≥ 20 min break |
| H10 | Accessible vehicle on each route at least once per hour |
| H11 | Trip duration feasible: scheduled stop times ≥ P90 free-flow travel time (no impossible trips) |
| H12 | **Capacity allocation:** forecast P80 load on a trip ≤ rated capacity of the assigned vehicle (no capacity-infeasible allocation); vehicle type must serve the route (e.g., minibus not on a route where it fails turning constraints, if defined) |

Validator also returns *soft* violations (A1, A4, A6) with scores. Unit tests: ≥ 40 hand-built invalid plans, each expected to raise a specific code; hypothesis property tests (random valid plans → 0 hard violations; mutated plans → ≥ 1).

### 8.7 Optimizer and recommendation engine (`optimize/`)

**Decision flow (two stages, tractable in seconds):**

*Stage A — Service-level sizing (per route, per 5-min slot in the window):* use P80 forecast demand per route segment/direction to compute required departures. Minimise expected wait + unmet demand subject to H7, H8 and capacity.

*Stage B — Vehicle blocking (CP-SAT):*
- Variables: `x[t]` ∈ {0,1} trip operated (for candidate trips: baseline trips, shifted by −5…+5 min in 1-min steps, and added candidate trips every 2 minutes); `a[v,t]` ∈ {0,1} vehicle-to-trip assignment; slack `u[r,k]` ≥ 0 unmet demand in slot `k`; `y[t,s]` transfer-feasibility indicator.
- Constraints: H1–H12 encoded explicitly; fluid capacity balance `Σ cap(v)·a[v,t] covering slot k + u[r,k] ≥ D80[r,k]`; connection-protect constraints (`y` = 1 if arrival at hub + 4 min ≤ connecting departure).
- Objective (weights in config; normalised):
  `min  w_wait·ΣWait + w_unmet·Σu + w_conn·Σ(1−y)·pax + w_km·VehicleKm + w_dev·Σ|shift| + w_chg·#changes_vs_current`
  Default weights: unmet 10, connections 6, wait 1, vehicle-km 0.3, deviation 0.5, change 1.5 (documented; sensitivity analysis shown in appendix chart).
- Solver: CP-SAT, `max_time_in_seconds = 10`, 8 workers, fixed random seed; returns best feasible; **warm start from the current plan**.
- **Fallback heuristic:** greedy "add trip where overload is worst, using nearest idle vehicle" + local-search retiming; always yields a valid plan (verified by validator) so the demo never has an empty result.

**Recommendation types** (each emitted as a card):
1. `ADD_TRIP` — add an extra departure (using an idle reserve vehicle) on an overloaded route at a given time.
2. `RETIME_TRIP` — shift a departure ≤ 5 min to protect a connection or smooth bunching.
3. `SWAP_VEHICLE` — assign a larger/accessible vehicle to a high-load trip, smaller one to a low-load trip.
4. `REALLOCATE_VEHICLE` — move a vehicle from a low-demand route to a high-demand one for a window.
5. `SHORT_TURN` — turn a loop trip early / skip low-demand tail to recover delay (disruption mode).
6. `HOLD_FOR_CONNECTION` — hold a departure ≤ 2 min at the hub if a delayed feeder carries ≥ N transferring passengers (disruption mode).

**Recommendation card schema (explainability):**
```json
{
  "id": "rec-0007",
  "type": "ADD_TRIP",
  "summary": "Add an R3 departure at 08:21 from S13 using bus B5 (idle reserve)",
  "reason_codes": ["A2_CAPACITY_RISK", "A4_MISSED_CONNECTION"],
  "evidence": {"p80_load_before": 1.34, "p80_load_after": 0.91, "pax_affected": 62},
  "impact": {"avg_wait_min": -1.8, "left_behind": -41, "missed_connections": -17, "vehicle_km": +14.2},
  "tradeoff": "Uses a reserve bus for 52 min (+14 vehicle-km). Reduces R3 left-behind passengers by 41. R1 headway unchanged.",
  "binding_constraints": ["H6 fleet size at 08:30", "H3 layover for B5"],
  "alternatives_rejected": [{"option": "retime 08:24 trip earlier", "why": "violates H8 and still leaves load at 1.12"}],
  "validated": true, "violations": [],
  "confidence": "high"
}
```

**Disruption mode (rolling horizon):** every 5 simulated minutes (or on event trigger) re-run the optimizer over the next 60 min, with the next 10 min of departures frozen, a heavy `w_chg` to avoid churn, and updated availability/ETA/demand. Outputs delta recommendations only (what changed and why).

### 8.8 Evaluation harness (`eval/`) — see Section 9.

---

## 9. Evaluation Protocol (predeclared)

**Frozen artifacts** (committed, hashed, tagged `eval-freeze` *before* running final evaluation): `config/baseline_plan.json`, `config/eval_manifest.yaml` (windows, scenarios, seeds, KPI list, weights, split days), dataset hash, model hash.

### 9.1 Compared systems
| Label | Plan | ETA |
|---|---|---|
| **Baseline-0** | Published fixed timetable, static vehicle assignment | Timetable |
| **Baseline-1 (strong, reactive)** | Baseline-0 + simple rule: when observed load > 90% on a trip, dispatch an idle reserve on that route after ≥ 5 min | Last-delay carry-forward |
| **RoutePulse** | Optimised plan (and rolling re-opt in disruptions) | RoutePulse ETA |

All use the **same fleet, same demand realisation, same travel-time realisation** per seed. No system sees the future.

### 9.2 Predeclared KPIs (primary first)
| KPI | Definition |
|---|---|
| **P1: Mean passenger wait (min)** | Average (boarding time − arrival time at stop), incl. waits caused by left-behind |
| **P2: Left-behind / unmet demand (pax)** | Passengers who could not board the first arriving vehicle, plus balked |
| **P3: Missed connections (count & %)** | Transferring pax who miss their connecting departure |
| P4: Overcrowded trips (#) | Trips with any segment load > 100% rated capacity (hard) and > 85% (soft) |
| P5: P95 wait (min) | Tail experience |
| P6: Fleet utilisation | seat-km used ÷ seat-km offered; plus vehicle-km and vehicles in service |
| P7: ETA MAE / coverage | Section 8.3 |
| P8: Hard-constraint violations | Must be **0** for RoutePulse and for the baseline (baseline validity shown too) |
| P9: Demand forecast WAPE | Section 8.4 |
| P10: Plan churn (disruptions) | Number of changed trips vs current plan |

Primary objective, declared in advance: **a weighted composite of P1, P2, P3** with P8 = 0 as a gate. Per-scenario results reported with mean ± 95% CI over 20 seeds and paired differences.

### 9.3 Stretch targets (aspirational, not promises; report actuals)
Wait −20%, left-behind −50%, missed connections −40%, ETA MAE −30% vs timetable and −10% vs carry-forward, window coverage 78–82%, 0 hard violations, solver time < 10 s.

### 9.4 Outputs
`make eval` writes `results/results.json`, `results/summary.md` (table), and charts (`wait_by_scenario.png`, `load_profile_R3.png`, `eta_error_by_horizon.png`, `coverage.png`) used directly in the UI and pitch deck. Include an **ablation table** (ETA without live adjustment; optimiser without connection constraint; without nowcast) and a **sensitivity chart** for objective weights.

---

## 10. API Contract (FastAPI)

| Method & path | Purpose |
|---|---|
| `GET /api/network` | Stops, routes, vehicles, transfers |
| `GET /api/plans/{plan_id}` | Baseline or proposed plan with trips and vehicle blocks |
| `POST /api/plans/validate` | Body: plan → list of violations (hard and soft) |
| `GET /api/live/stream` (SSE) | Replay of pings, ETAs, alerts at accelerated speed (`?speed=30`) |
| `GET /api/eta?stop_id=&t=` | Next arrivals with p10/p50/p90 windows, confidence, reasons |
| `GET /api/eta/vehicle/{vehicle_id}` | Downstream ETAs for a vehicle |
| `GET /api/demand?stop_id=&date=` | Forecast bands (P50/P80/P90) vs actual (if available) |
| `GET /api/alerts?plan_id=&scenario_id=` | Typed alerts A1–A8 with severity |
| `POST /api/recommendations` | Body: scenario, plan, time → ranked recommendation cards |
| `POST /api/recommendations/{id}/apply` | Apply to a working copy of the plan; re-validate; return new plan and KPI delta |
| `POST /api/whatif` | Body: modifications (add/remove trip, change vehicle) → validation + simulated KPIs |
| `POST /api/scenarios/{id}/run` | Run simulation for baseline/proposed with seed |
| `GET /api/eval/results` | Latest evaluation summary and chart paths |
| `POST /api/ingest/gps` / `POST /api/ingest/apc` | Real-feed-compatible ingest (accepts `GpsPing[]`/`ApcRecord[]`) |
| `GET /api/student/route?from=&to=&t=&accessible=` | Passenger-facing options: direct/transfer, ETA window, transfer-safe probability |
| `GET /api/health` | Versions, data hashes, model hashes |

All request/response bodies are Pydantic models; invalid input returns RFC-7807 problem JSON. CORS locked to the web origin.

---

## 11. UI Specification

**Principle:** a credible operator workflow in 4 screens plus a student screen. Optimise for the 3-minute demo.

1. **Network map (offline SVG, optional tiles):** stops, route polylines (colour-coded), vehicles moving at accelerated replay, load as vehicle fill-ring (green→amber→red), hub highlighted. Time scrubber and speed control.
2. **ETA board:** per stop, upcoming vehicles with window bar (p10–p90), confidence badge, and a baseline comparison tooltip ("timetable said 08:12, actual window 08:17–08:22").
3. **Demand & alerts:** heatmap (stop × time) of forecast vs capacity; alert list A1–A8 sorted by passengers affected; click an alert to highlight on the map and timeline.
4. **Recommendations:** cards (Section 8.7 schema) with *Accept / Reject / What-if*; before/after sparkline of load; constraint-check checklist (✓ H1–H12); "validated: 0 violations" badge. Accept updates the working plan and KPIs live.
5. **Scenario comparison:** scenario selector (S0–S3), baseline vs RoutePulse side-by-side KPI table with CI whiskers, charts, and the "violations = 0" gate display.
6. **Disruption simulator:** buttons to inject S1/S2/S3 live; shows detection → recommendation → effect timeline.
7. **Student view (P1):** from/to, "now/time" and accessibility toggle; shows ETA windows, transfer probability, and fallback alternatives ("next R3 is crowded — 8 min later R3 is predicted 60% full").

Design: use the `frontend-design` skill guidance: clear hierarchy, colour-blind-safe palette, large readable ETA numbers, dark/light mode, mobile-responsive student view, no placeholder lorem text, loading and empty states everywhere.

---

## 12. Real-World Hardening (what makes this credible beyond the hackathon)

| Real-world issue | Handling in design |
|---|---|
| Noisy / missing GPS | Map-matching, Kalman, dropout flags, stale-feed fallback to B1 ETA |
| Cold start on a new campus | Timetable-based window + route-level priors; model activates after N days of data |
| Concept drift (semester change, construction) | Drift monitor: rolling coverage and MAE; auto-alert if coverage < 70% or WAPE > threshold; retrain command |
| Data standards | GTFS static export; GTFS-RT-shaped ingest adapter |
| Passenger counting | APC schema supports camera/door sensors; optional edge counter prototype posts to `/ingest/apc` (Raspberry Pi + person-detector → MQTT/HTTP) |
| Privacy | Aggregate anonymous counts only; no faces, no IDs stored; documented |
| Operator trust | Human approval, full explanation, validated plans only, one-click rollback to baseline |
| Driver / union rules | Hard constraints H3, H9; minimal-change penalty avoids chaotic reschedules |
| Latency | Solver ≤ 10 s with warm start; ETA inference < 50 ms; precomputed profiles |
| Failure modes | Optimizer failure → heuristic fallback → baseline plan; every fallback is visible in UI |
| Scale | Stateless API; stateful stores swap to Postgres/TimescaleDB; per-route decomposition of the optimizer for larger fleets |

---

## 13. Repository Structure and Commands

```
routepulse/
├─ README.md                  # 1-page overview + results table + quickstart
├─ Makefile                   # all, data, train, eval, demo, test, lint
├─ docker-compose.yml
├─ pyproject.toml / requirements.lock
├─ config/
│   ├─ default.yaml           # all parameters (Appendix A)
│   ├─ baseline_plan.json     # frozen baseline
│   └─ eval_manifest.yaml     # frozen windows/scenarios/seeds/KPIs
├─ core/                      # schemas.py, config.py, io.py, geometry.py
├─ sim/                       # generate_world.py, traffic.py, demand_gen.py,
│                             # gps_gen.py, engine.py (discrete-event), scenarios.py
├─ eta/                       # gps_processing.py, profiles.py, live.py, model.py, conformal.py, baselines.py
├─ demand/                    # features.py, model.py, nowcast.py, baselines.py
├─ detect/                    # alerts.py
├─ validate/                  # validator.py, constraints.py
├─ optimize/                  # candidates.py, cpsat_model.py, heuristic.py, rolling.py, explain.py
├─ eval/                      # run_eval.py, metrics.py, report.py, charts.py
├─ api/                       # main.py, routers/*, sse.py, replayer.py
├─ web/                       # React app (Vite, TS)
├─ tests/                     # unit, property (hypothesis), integration, e2e
├─ docs/                      # ARCHITECTURE.md (this), ASSUMPTIONS.md, CONSTRAINTS.md,
│                             # PRIVACY.md, DEMO_SCRIPT.md, SUBMISSION.md
└─ results/                   # generated; committed for judges
```

**Make targets:** `make data` (generate world; writes hashes) → `make train` (ETA + demand models) → `make eval` (full evaluation) → `make demo` (API + web + replayer) → `make test` → `make all` (= data, train, eval, test). Docker: `docker compose up` brings up the demo.

---

## 14. How Antigravity Should Execute (agents, skills, MCPs)

> Use whichever of these exist in your environment; if a named tool is unavailable, use the closest equivalent and note it in `docs/ASSUMPTIONS.md`. If your version supports project rules, workflows and skills folders (e.g., `.agent/rules`, `.agent/workflows`, `.agent/skills`), put the rules in Section 0 and the contracts in Section 6/10 there so every agent inherits them.

### 14.1 Agent roles (run in parallel after the contracts are frozen)
| Agent | Owns | Starts after | Done when |
|---|---|---|---|
| **A0 Planner / Integrator** | Contracts, repo skeleton, Makefile, integration, merge order, daily checklist | t0 | `make demo` runs end-to-end after each phase |
| **A1 World & Data** | `sim/` (generator, scenarios), dataset validation, hashes | contracts | 30 days + 4 scenarios generated, validated, deterministic |
| **A2 ETA** | `eta/` | A1 first dataset | ETA metrics table vs B0/B1 on validation |
| **A3 Demand** | `demand/` | A1 first dataset | WAPE table vs baseline; P80 bands |
| **A4 Simulator & Detection** | `sim/engine.py`, `detect/` | contracts + sample plan | Loads, left-behind, missed connections, alerts A1–A8 |
| **A5 Validator** | `validate/` | contracts | 40+ invalid-plan tests pass; property tests pass |
| **A6 Optimizer** | `optimize/` | A4 + A5 stubs | Valid recommendations in S0–S3; heuristic fallback working |
| **A7 API** | `api/` | contracts | All endpoints return fixtures first, then real data |
| **A8 Frontend** | `web/` | API fixtures | Screens 1–6 working on fixtures, then real API |
| **A9 Evaluation** | `eval/` | A4 + A6 | `make eval` outputs table and charts; ablations |
| **A10 QA / Reviewer (adversarial)** | tests, review, "break it" scenarios | continuous | Independent review of each merged module; fails the build on any hard violation, nondeterminism, or test-set leakage |
| **A11 Docs & Pitch** | README, DEMO_SCRIPT, deck, screenshots | results ready | Submission package complete by 21:15 |

Merge rules: small PRs/commits; A10 reviews anything touching constraints, evaluation or splits; A0 resolves contract changes.

### 14.2 Skills to use (if available)
- **frontend-design** — for the web UI (distinctive, accessible, responsive; avoid generic templates).
- **webapp-testing / Playwright skill** — UI smoke tests and screenshots for the deck.
- **pptx** — build the pitch deck; **docx/pdf** — only if the submission requires those formats.
- **xlsx / data-analysis** — optional results tables or CSV exports for judges.
- **product-self-knowledge** — only if any Claude/Anthropic product facts are referenced (probably not needed).
- A code-review skill/agent for A10, and a debugging/systematic-debugging skill when tests fail.

### 14.3 MCP servers to use (if available)
- **Filesystem** — project files.
- **GitHub / Git** — commits, tagging `eval-freeze`, branch protection for the frozen artifacts.
- **Context7 (or any up-to-date documentation MCP)** — current docs for OR-Tools CP-SAT, FastAPI, LightGBM, Pydantic v2, Vite/React, Recharts.
- **Playwright / Browser MCP** — drive the UI, verify screens, capture screenshots for the deck.
- **Sequential-thinking MCP** — for the optimizer formulation and constraint reasoning.
- **Fetch/Web** — only for reading documentation; **no runtime dependency on any external service.**

### 14.4 Task protocol for every agent
1. Re-read the relevant Sections and the frozen contracts.
2. Write tests first for constraints and metrics.
3. Implement; run tests; run `make demo` smoke.
4. Self-review against the **Definition of Done** (Section 16).
5. Update docs if any assumption changed.

---

## 15. Timeline (deadline 22:00 — work backwards; adjust if you start late)

| Phase | Time budget | Output | Checkpoint |
|---|---|---|---|
| 0. Contracts & skeleton | first 45 min | Schemas, config, fixtures, OpenAPI, Makefile, repo | `make test` runs (empty ok) |
| 1. World + baseline + simulator | next 1.5 h | Generated data, baseline plan, load sim, alerts | Baseline KPIs computed; baseline visibly overloaded on R3 |
| 2. ETA engine + validator | parallel, 1.5 h | ETA metrics vs B0/B1, validator + tests | Table of ETA results |
| 3. Optimizer + recommendations | next 1.5 h | Valid recs in S0; heuristic fallback | KPI improvement shows on S0 |
| 4. API + UI wiring | parallel with 3 | Screens 1–5 on real data | Live demo path works |
| 5. Demand forecaster + disruptions | 1 h | Forecast + S1–S3 re-opt | Results across S0–S3 |
| 6. Eval freeze → final run | 30 min | Tag `eval-freeze`, `make eval`, charts, ablations | **Feature freeze at 20:30** |
| 7. Polish, README, demo, deck | 45 min | Submission package | **Ready by 21:15** |
| 8. Buffer & upload | 30 min | Dry-run on a clean checkout/Docker, upload | Submitted by 21:45 |

**If time is short:** collapse to P0 only (Section 3), use the heuristic optimizer + historical-mean demand forecast, and spend the saved time on the evaluation and demo quality. Never cut the validator, the baseline, or reproducibility.

---

## 16. Testing and Definition of Done

**Tests that must exist**
- Generator determinism: same seed → identical hashes.
- Dataset validation catches injected corrupt data.
- Map-matching: recovers progress within 15 m RMSE on noisy synthetic traces; handles dropouts.
- ETA: coverage within 75–85% on validation; no NaNs; monotone ETAs by stop.
- Validator: 40+ invalid plans each trigger the intended code; baseline plan passes hard constraints.
- Optimizer: output passes validator in 100% of S0–S3 runs across 20 seeds; solver time bound honoured; deterministic under fixed seed.
- Evaluation: no test-day data touched by training code (assert on split IDs); paired seeds identical across systems.
- API: contract tests against fixtures; UI smoke test (Playwright) loads each screen.

**Definition of Done (whole project)**
- [ ] `make all` and `docker compose up` work from a clean clone, offline
- [ ] Baseline plan, evaluation windows and scenarios are frozen and hashed before the final run (`eval-freeze` tag)
- [ ] RoutePulse has 0 hard-constraint violations in every evaluated run; baseline validity also reported
- [ ] KPI table shows measured deltas vs both baselines with CIs, including cases where we do not win
- [ ] ETA windows shown in UI with documented assumptions
- [ ] ≥ 3 recommendation types demonstrated with trade-off explanations
- [ ] Disruptions S1–S3 handled with re-optimisation or documented fallback
- [ ] README with 1-page overview, quickstart, results, limitations
- [ ] Demo script rehearsed (≤ 3 min) and a recorded fallback video/GIF

---

## 17. Submission Package and Demo Script

**Package:** repository link/zip, `README.md`, `docs/ASSUMPTIONS.md`, `docs/CONSTRAINTS.md`, `results/summary.md` + charts, short pitch deck (6–8 slides), demo video/GIF fallback, screenshot set.

**Deck outline:** (1) Problem & why tracking ≠ planning; (2) Solution overview (Sense→Estimate→Detect→Decide→Verify→Explain); (3) Data model & constraints; (4) ETA windows & results; (5) Demand/capacity detection; (6) Recommendation with trade-off (R3 morning peak example); (7) Baseline vs RoutePulse results table incl. disruptions; (8) Real-world path, business model, limitations.

**3-minute live demo flow:**
1. (0:00) Map replay of S0 morning peak. Baseline plan: R3 turns red, alerts A2/A4 fire.
2. (0:30) ETA board: baseline timetable vs RoutePulse window (with actual arrival revealed) — show error difference.
3. (1:00) Open recommendation card: add trip using idle reserve; show constraint checklist and trade-off. Accept → KPIs update; "0 violations" badge.
4. (1:45) Inject S2 (vehicle breakdown) or S3 (event spike): system re-optimises with minimal changes; show hold-for-connection or reallocation.
5. (2:30) Scenario comparison table: wait, left-behind, missed connections, utilisation with CIs. Close with deployment/commercial line.

---

## 18. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Simulator seen as rigged | Strong baseline-1, documented ground truth, structural mismatch (dwell coupling, bad-day factors), paired seeds, show losses honestly |
| Optimizer too slow or infeasible | Candidate-trip pruning, 10 s limit, warm start, heuristic fallback verified by validator |
| ETA model overfits | Validation-based conformal calibration; evaluate on locked test only once |
| Time overrun | Tiered scope; fallbacks for every ML component; Streamlit UI fallback decided at Phase 4 start |
| Test leakage | Split IDs asserted in code; `eval-freeze` tag; A10 audits |
| Offline venue | No CDN/tile dependency; assets bundled; recorded demo fallback |
| Merge chaos among agents | Contracts frozen early; A0 integrator; small commits |
| Over-claiming | Stretch targets labelled as aspirational; report actuals |

---

## 19. Commercial Model (one slide + README paragraph)

- **Product:** RoutePulse SaaS — planning workspace for campus and institutional transport operators (ETA service, demand forecasting, plan optimisation, disruption copilot).
- **Customers:** universities, corporate/IT parks, hospitals, townships, school-bus contractors, fleet operators serving institutions.
- **Pricing:** per-vehicle/month subscription (tiers: ETA-only, Planning, Planning + Disruption); onboarding/integration fee; optional edge-counter hardware bundle.
- **Value:** fewer peak failures (left-behind, missed connections), fewer idle vehicle-hours, better passenger information; ROI shown via the evaluation KPIs converted to fleet-hours saved and complaint reduction.
- **Go-to-market:** pilot on one campus with 2–4 weeks of historical GPS + APC; operator-in-the-loop trial; expand through contractors. Integrates via GTFS/GTFS-RT so existing fleet software stays in place.

---

## Appendix A — `config/default.yaml` (starting values)

```yaml
master_seed: 20261014
service_hours: {start: "06:30", end: "22:00"}
days: {total: 30, train: [1,20], validation: [21,25], test: [26,30]}
windows: {W1: ["07:30","10:30"], W2: ["16:30","19:30"]}
replications: 20
gps: {ping_s: 10, noise_m: 8.0, outlier_rate: 0.02, dropout_rate: 0.03, outage_bursts_per_vehicle_day: 2}
traffic: {lognormal_sigma: 0.12, morning_mult: [1.25,1.40], evening_mult: [1.20,1.35]}
dwell: {base_s: 5, min_s: 6, per_board_s: 1.4, per_alight_s: 0.8}
demand: {boardings_per_day: 6000, patience_min: 20, transfer_share: 0.25}
vehicles: {buses: 6, bus_capacity: 45, minibuses: 4, minibus_capacity: 22, accessible: [B1, B2, M1]}
rules:
  min_headway: 3
  max_headway_peak: 12
  max_headway_offpeak: 20
  min_layover: 4
  max_departure_shift: 5
  max_continuous_drive_min: 210
  min_break_min: 20
  min_transfer_min: 4
  accessible_min_per_route_hour: 1
alerts: {soft_load: 0.85, hard_load: 1.00, bunching_low: 0.4, gap_high: 1.6}
eta: {geofence_m: 25, decay_gamma: 0.85, lookback_segments: 3, target_coverage: 0.80, stale_gps_s: 120}
demand_model: {slot_min: 15, nowcast_clip: [0.7, 1.8], quantiles: [0.5, 0.8, 0.9]}
optimizer:
  time_limit_s: 10
  workers: 8
  weights: {unmet: 10, connection: 6, wait: 1, vehicle_km: 0.3, deviation: 0.5, change: 1.5}
  candidate_shift_range: [-5, 5]
  candidate_extra_trip_step_min: 2
  rolling: {replan_every_min: 5, horizon_min: 60, freeze_min: 10}
```

## Appendix B — Pseudocode of Key Algorithms

**Live ETA for vehicle v at progress s, downstream stops k = 1..K**
```
rho  = EWMA(observed_seg_time / expected_seg_time, last 3 segments)
t    = now
for k in 1..K:
    seg_mu  = profile_median(seg_k, bucket(t), daytype)
    seg_adj = seg_mu * (1 + (rho - 1) * gamma**k)
    dwell_k = f(expected_boardings(stop_k, t), current_load)
    t      += seg_adj + dwell_k
    base_k  = t
    q10,q50,q90 = lgbm_quantiles(features_k) + base_k      # residual model
    window_k = conformal_adjust(q10, q90)                 # calibrated to 80%
```

**Simulator boarding rule at a stop**
```
alight(vehicle, stop)
space = capacity - load
board = min(space, len(queue[stop][route/direction]))   # FIFO
leftbehind += len(queue) - board
for passenger in queue waiting > patience: balk, count unmet
dwell = max(6, 5 + 1.4*board + 0.8*alight)
```

**Recommendation ranking**
```
score = w_unmet*Δunmet + w_conn*Δconn + w_wait*Δwait - w_km*Δkm - w_chg*changes
keep only recommendations with validator.hard_violations == 0
rank by score; show top-N with trade-off text generated from the deltas and binding constraints
```

---

*End of specification. Build P0 first, keep the demo runnable at every step, keep the validator independent, and never touch the test split before `eval-freeze`.*
