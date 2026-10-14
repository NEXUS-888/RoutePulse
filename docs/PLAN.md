# RoutePulse Execution Plan & Task Ownership

## Timeline & Milestones
- **T0 (12:42):** Project kickoff.
- **T+45m (13:30):** Milestone 1 — Contracts & Skeleton frozen (`make test` passes, schemas, OpenAPI, fixtures, Makefile).
- **19:00:** Milestone 2 — Runnable End-to-End P0 Demo (Data, Simulator, Validator, Optimizer, API, SVG UI).
- **20:30:** Milestone 3 — Feature Freeze (P1 ML extensions, rolling disruptions, eval tagged `eval-freeze`).
- **21:15:** Milestone 4 — Submission Package (README, results, slides, demo script).
- **21:45:** Milestone 5 — Code Freeze & upload verification.
- **22:00:** Submission Deadline.

## Agent Responsibilities & Deliverables
| Agent | Role | Owned Directories | Done Criteria |
|---|---|---|---|
| **A0** | Lead Integrator | Root, `config/`, `core/`, Makefile | `make demo` and `make test` run smoothly across phases |
| **A1** | World & Data | `sim/`, `data/` | 30 simulated days (splits 1-20, 21-25, 26-30), S0-S3 scenarios, determinism verified |
| **A2** | ETA Engine | `eta/` | Map matching, Kalman smoothing, historical profiles, residual quantiles, conformal calibration |
| **A3** | Demand Forecaster | `demand/` | Historical mean baseline, LightGBM Poisson model, P50/P80/P90 bands, nowcasting |
| **A4** | Simulator & Detection | `sim/engine.py`, `detect/` | Discrete event engine, FIFO boarding, left-behind, missed connection tracking, alerts A1–A8 |
| **A5** | Hard Validator | `validate/` | 12 hard constraints (H1–H12), 40+ unit tests with invalid plans, property tests |
| **A6** | Optimizer | `optimize/` | CP-SAT formulation + greedy/local-search heuristic fallback, recommendation cards |
| **A7** | API Gateway | `api/` | FastAPI REST endpoints + SSE stream (`/api/live/stream`), fixture tests |
| **A8** | Frontend Dashboard | `web/` | React + TypeScript + Vite, offline SVG campus map, ETA board, alerts, recommendations, what-if |
| **A9** | Evaluation Harness | `eval/` | Predeclared evaluation protocol, 20 seeds, CI bounds, summary markdown, metric plots |
| **A10** | Adversarial QA | `tests/` | Independent test suite, split leakage assertion, stress testing |
| **A11** | Documentation & Pitch | `docs/`, `README.md`, slides | Executive README, DEMO_SCRIPT.md, slide deck |

## Task Checklist
- [x] Step 1.1: Initialize Git and directory tree
- [ ] Step 1.2: Write `config/default.yaml` from Appendix A
- [ ] Step 1.3: Write `core/schemas.py` with Pydantic v2 schemas for all Section 6 entities
- [ ] Step 1.4: Generate OpenAPI contract `api/openapi.json` and JSON fixtures for all Section 10 endpoints
- [ ] Step 1.5: Write `Makefile`, `pyproject.toml`, and `requirements.txt`
- [ ] Step 1.6: Write initial contract test suite in `tests/test_contracts.py`
- [ ] Step 1.7: Verify `make test` runs cleanly and commit Milestone 1
- [ ] Step 2.0: Parallel agent execution
