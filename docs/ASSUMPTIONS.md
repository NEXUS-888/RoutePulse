# RoutePulse — Assumptions & Design Decisions

## 1. Hackathon Execution Parameters
- **Current Local Start Time:** 2026-10-14 12:42:36
- **Deadline:** 2026-10-14 22:00:00
- **Time Remaining at Start:** ~9 hours 18 minutes (> 5 hours).
- **Scope Decision:** Build complete P0 (Mandatory MVP) target by 19:00, advance to P1 (LightGBM demand nowcasting, rolling disruption re-optimisation, student view, GTFS export) targeted by 20:30 (Feature Freeze).
- **Master Seed:** `20261014` enforced across all synthetic generation, simulation, training, conformal calibration, and optimization routines.
- **Python Runtime:** Python 3.11 (`C:\Users\Lenovo\miniconda3\envs\tracknet\python.exe`) with Make 4.4.1.

## 2. Modeling & Physics Assumptions
- **Campus Grid & Geography:** Metric coordinates (x, y in meters) are the ground-truth space. Fictional campus origin centered at lat: `12.9716`, lon: `77.5946`. Conversion utilizes equirectangular approximation around campus center (~111,320 m/deg lat, ~108,500 m/deg lon).
- **Route Tracking & Polylines:** Vehicles follow fixed piecewise linear polylines. No off-route detours in baseline normal operations.
- **Geofence & Stop Events:** A 25 m radial geofence defines stop arrival/dwell.
- **Dwell Coupling:** Dwell time is modeled by `max(6, 5 + 1.4 * boardings + 0.8 * alightings)` seconds.
- **GPS Noise & Dropouts:** 10 s pings, Gaussian noise σ = 8 m, 2% outliers up to 80 m, 3% dropouts, with map-matching via 1D progress along polyline + 1D Kalman smoothing.
- **Traffic Model:** Congestion multiplier follows morning bump (07:45–09:15, 1.25–1.40x) and evening bump (16:45–18:30, 1.20–1.35x), with lognormal travel time variance (σ = 0.12).
- **Passenger Balking:** FIFO boarding; passengers waiting > 20 minutes balk (marked as unmet demand).
- **Transfers:** Minimum transfer time is 4 minutes at Central Hub S03.
- **Validator Independence:** `validate/validator.py` has zero imports from `optimize/`. A plan with hard violations is strictly discarded or rejected from recommendation.
- **Eval Lockout:** Days 26–30 are test days, only accessed via `make eval`.
