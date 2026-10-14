# RoutePulse UI/UX Overhaul — Master Execution Plan

> **Specification Reference:** `docs/ROUTEPULSE_UI_UX_SPEC.md` & `ROUTEPULSE_ARCHITECTURE.md` (Sections 10, 11).
> **Execution Clock:** Started 14:38 local time | **Feature Freeze:** 20:30 (approx 5h 50m remaining) | **Hard Deadline:** 22:00.
> **Scope Guardrail:** `./web` and `docs/` ONLY. Backend API contracts, schemas, optimizer, validator, evaluation logic remain strictly untouched. Zero external network requests (100% self-hosted & offline).

---

## 1. System Vision & Aesthetic Guardrails
- **Core Theme:** "Mission Control meets Transit Map" — a subway map that is alive.
- **Visual Identity:** Signature Pulse Line ECG motif, custom RoutePulse lockup ("Plan the campus. Don't just watch it.").
- **Themes:** Dual-theme system in `web/src/styles/tokens.css`:
  - **"Control Room" Dark (Default):** Deep ink `#0B1020`, 1px hairline borders (`rgba(255,255,255,0.08)`), subtle depth, soft glows.
  - **"Paper" Light:** Warm off-white `#F8F9FA` with slate accents for projection & high-glare environments.
- **Typography:** Self-hosted via `@fontsource`:
  - Display & Key Numbers: **Space Grotesk**
  - Text & UI: **Plus Jakarta Sans**
  - Codes, Coordinates, Timetable Tabular Numerals: **JetBrains Mono**
- **Strictly Banned:** Generic SaaS gradients, uniform card grids, emoji icons, Inter/Roboto defaults, lorem ipsum.

---

## 2. Component Inventory & Architecture

### A. Layout Shell (`web/src/components/shell/`)
1. **`AppShell.tsx`**: 5-zone mission control layout:
   - **Left Icon Rail (`IconRail.tsx`):** Slim navigation rail with icon glyphs, badge indicators, expand-on-hover labels.
   - **Top Status Ribbon (`StatusRibbon.tsx`):** Logo lockup, active scenario chip, simulation clock, live **Pulse Line** waveform, **Network Health Score** capsule, Theme toggle, Help (`?`), Tour trigger.
   - **Centre Stage:** Hero view (full-bleed interactive SVG transit map or dedicated analytical screen).
   - **Right Inspector Drawer (`InspectorDrawer.tsx`):** Sliding slide-over panel inspecting selected stop, vehicle, alert, or recommendation card.
   - **Bottom Time Deck (`TimeDeck.tsx`):** Scrubber, play/pause, speed multipliers (1x / 10x / 30x), demand heat-strip, disruption pins, "Now" playhead.
2. **`PulseLine.tsx`**: Dynamic SVG/Canvas ECG pulse beating with replay clock; amplitude reacts dynamically to network stress, delays, and peak load factor.
3. **`NetworkHealthScore.tsx`**: Implements exact spec formula `max(0, 100 - 40*overcap - 30*leftbehind - 20*missedconn - 10*delays)`. Color bands: 80-100 Teal, 60-79 Amber, <60 Coral. Tooltip details exact penalty breakdown.

### B. Transit Map Engine (`web/src/map/` & `web/src/components/map/`)
1. **`schematic.ts`**: Hand-authored 45°/90° schematic layout for campus stops S01–S13:
   - Central Hub S03 large interchange ring with dashed 4-minute walk transfer corridor.
   - Metro Station S13 styled as campus entry gateway.
   - Station ticks, collision-avoiding callouts, clean angled transit corridors.
2. **`SchematicMap.tsx`**: High-performance memoized SVG renderer (smooth at 30x replay):
   - **Vehicle Glyphs:** Capsule shape with integrated load ring (teal/amber/coral), pulsing halo on >85% load, dashed ghost vehicle on breakdown (S2).
   - **Layer Controls:** Toggle Routes, Stops, Vehicles, Load Rings, Demand Glow, Alerts, Transfers/Hub, Accessibility, Disruption Zones, Plan Comparison.
   - **Interactivity:** Hover arrival windows, click to inspect in drawer, zoom/pan controls, "Fit All" and "Follow Vehicle" presets.
   - **View Toggle:** Seamless switch between *Schematic View* (default) and *Geographic View* (true coordinates).

### C. Signature Interactions & Widgets (`web/src/components/common/`)
1. **`EtaCapsule.tsx`**: Horizontal capsule showing p10–p90 confidence window, bold p50 marker, timetable ghost tick, and hover plain-language diagnosis.
2. **`RecommendationTicket.tsx`**: Operator decision ticket with animated count-up delta metrics (wait, left-behind, missed connections), Gain vs Cost summary, H1–H12 constraint checklist with animated green checks, "Validated: 0 violations" seal, and Accept / Reject / Try What-If actions.
3. **`BeforeAfterSlider.tsx`**: Interactive split-screen reveal slider comparing Baseline-0 plan (overcrowded, coral queues) vs RoutePulse plan (balanced load).
4. **`GlossaryPopover.tsx`**: Contextual `(i)` badges that trigger plain-language explanations from single-source glossary.
5. **`StateViews.tsx`**: Accessible skeleton loaders, friendly empty states, and error recovery banners for every screen.

### D. First-Run & Onboarding (`web/src/components/onboarding/` & `help/`)
1. **`glossary.ts` (`web/src/content/glossary.ts`)**: Single source of truth for transport terminology.
2. **`WelcomeModal.tsx`**: Pulse line draw animation, logo lockup, role selector (Operator / Student / Reviewer), 3 choices: 90s Tour, Auto-Demo, Explore.
3. **`SpotlightTour.tsx`**: 11-step spotlight walkthrough (<=25 words per step, Back/Next/Skip, Esc close, resumable, stored in `rp_onboarded_v1`).
4. **`ShowcaseDemo.tsx`**: Deterministic 90-second hands-free showcase script with bottom captions, progress indicator, "Take control" and "Reset demo".
5. **`HelpDrawer.tsx`**: Slide-over Help Centre (`?` shortcut) containing search, glossary, role guides, recipes, and keyboard shortcuts.

### E. Screens Overhaul (`web/src/components/screens/`)
1. **`Screen1NetworkMap.tsx` / `CommandCenter.tsx`**: Full-bleed hero map with status ribbon, time deck, and inspector drawer.
2. **`Screen2EtaBoard.tsx`**: Per-stop arrival board with large tabular ETA capsules and timetable deltas.
3. **`Screen3DemandAlerts.tsx`**: Stop x time demand heatmap, A1–A8 alert list sorted by affected passengers, map link highlights.
4. **`Screen4Recommendations.tsx`**: Ranked recommendation cards, trade-off analysis, live plan update on Accept with 0-violations guarantee.
5. **`Screen5Disruptions.tsx`**: Scenario lab (S0–S3), Baseline vs RoutePulse comparison table with confidence intervals, Before/After slider.
6. **`Screen6StudentView.tsx`**: Mobile-first bottom sheet (390x844 responsive), large readable ETA windows, accessibility ramp toggle, crowding alerts + alternative departure.

### F. Documentation & Quality Gates (`docs/`)
1. **`docs/UI_PLAN.md`**: This master plan.
2. **`docs/UI_PROGRESS.md`**: Section 9 acceptance checklist tracking progress.
3. **`docs/UI_DECISIONS.md`**: Architectural and design log.
4. **`docs/APP_MAP.md`**: Mermaid diagram and ASCII wireframes.
5. **`docs/USER_GUIDE.md`**: Non-technical user guide (grade 7-8 reading level, What you see / What you can do / Why it matters).
6. **`docs/CHEATSHEET.md`**: One-page cheat sheet.
7. **`web/scripts/capture_screenshots.js`**: Playwright automated visual QA and screenshot capture.

---

## 3. Phased Build Order (Following Section 8 Tiers)

```
[Phase 1: Foundation] (P0) -> Tokens, themes, self-hosted fonts, glossary source.
[Phase 2: App Shell] (P0) -> Icon rail, status ribbon, time deck, inspector drawer, Pulse Line, Network Health.
[Phase 3: Map Engine] (P0) -> Hand-authored schematic coordinates, SVG renderer, load rings, ghost vehicles, legend.
[Phase 4: Core Widgets] (P0) -> ETA capsules, recommendation tickets, state views (loading/empty/error).
[Phase 5: Onboarding & Help] (P0) -> Welcome screen, 11-step spotlight tour, Help drawer.
[Phase 6: Student Mobile] (P0) -> 390x844 bottom sheet, ETA windows, accessibility toggle.
[Phase 7: Interactive Signatures] (P1) -> Before/After reveal slider, Showcase auto-demo, Glossary popovers.
[Phase 8: Documentation & Visual QA] (P0/P1) -> USER_GUIDE.md, APP_MAP.md, CHEATSHEET.md, Playwright automated capture & tests.
[Phase 9: Polish & Verification] (P2) -> Command palette (Ctrl+K), final dark/light AA contrast pass, build test.
```

---

## 4. Verification & Quality Gates
- **Offline Integrity:** All fonts and assets bundled; 0 external HTTP/CDN requests.
- **Contract Safety:** All API fixtures and real endpoints continue to work seamlessly.
- **Automated Testing:** `pytest tests/ -v` and `npm run build` must pass after every phase.
- **Visual QA:** Playwright tests for desktop (1440x900) and mobile (390x844) in both Dark and Light themes.
