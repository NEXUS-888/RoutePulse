# RoutePulse UI/UX — Architecture & Design Decisions Log

> Maintained per Section 0 of `docs/ROUTEPULSE_UI_UX_SPEC.md`.

## Design & Technical Decisions

### Typography
- **Display & Large Numerals:** `@fontsource/space-grotesk` (weights 500, 600, 700). Distinctive geometric grotesque character for a high-end mission control look, replacing generic system/Inter styling.
- **Body & Controls:** `@fontsource/plus-jakarta-sans` (weights 400, 500, 600, 700). Clean, legible, high-contrast grotesque face.
- **Data, Codes & Timestamps:** `@fontsource/jetbrains-mono` (tabular numerals enabled via `font-variant-numeric: tabular-nums`). Guarantees zero jitter when replay clock and countdowns tick.
- **Self-Hosted Offline Requirement:** Installed directly via npm. Zero external CDN or Google Fonts calls.

### Color Palette & Semantics ("Signage" theme, revised)
**Principle: colour always means something.** The UI chrome (buttons, panels, selection, play control) is neutral cream-on-graphite. Hue is reserved for exactly two jobs: route identity and status. This removes the previous blue/purple "dashboard" look, where blue was simultaneously the brand, the primary button and Route R1, and where Route R2 was the same green as the "healthy" status.

- **Dual Themes:**
  - **"Signage" Dark (default):** warm graphite `#121110`, panels `#1A1917` / `#242220`, cream text `#F4EEE2` (16:1), secondary `#B8B1A4` (8.9:1), tertiary `#8F887C` (5.4:1).
  - **"Timetable" Light:** printed-paper `#F3EFE5`, panels `#FFFDF8`, ink `#1C1A16` (15:1), secondary `#58534A`, tertiary `#6A6459`.
- **Accent (brand, primary action, selection, focus):** cream `#F4EEE2` in dark, ink `#1C1A16` in light, exposed as `--accent`, `--accent-bg`, `--accent-contrast`. Hub and metro gateway use the same accent, distinguished by shape (ring vs square), not hue.
- **Route palette (never green, amber or red):**
  - R1 Sky `#4DB8FF` / `#0A74BE`; R2 Periwinkle `#7C8CFF` / `#4655E0`; R3 Orchid `#C77BFF` / `#9333D6`; R4 Pink `#FF70C4` / `#CC2E93`.
  - Text on a route chip uses `--on-route` (graphite in dark, white in light). All chips are 4.7:1 or better.
- **Status language (unchanged semantics, retuned values):** green `#3DD68C` / `#12713F` (<85%), amber `#FFB02E` / `#A85A00` (85-100%), red `#FF5F52` / `#C4301F` (>100%). Always paired with a ring fill, text label, or icon, never colour alone.
- Token names (`--load-teal`, `--load-amber`, `--load-coral`, `--route-r1..r4`) are kept so components did not need renaming; only values changed.

### Simplification Pass (UX)
- **Header: 13 controls to 6.** Removed the duplicate sim clock (the time bar already shows it), the decorative fleet-cadence canvas, the tagline, the duplicate Schematic/Geographic toggle (now only on the map), and folded Tour and Reset into a `...` menu. One health signal remains.
- **Navigation:** the rail is always labelled (icon over text) instead of icon-only with hover tooltips. Plain names: Live map, Arrivals, Crowding, Suggestions, What-if, Student app. Count bubbles appear only for alerts and pending suggestions. The pin/dock toggle and the duplicate Help button were removed.
- **Map:** toolbar reduced to Schematic/Geographic, zoom and Layers (follow-vehicle moved into the Layers popover). Compact two-row legend at top-right (collapsed by default under 1280px wide). Minimap appears only when zoomed or panned. Vehicles are route-coloured badges whose outer ring shows load; the old ring-through-capsule glyph was ambiguous.
- **Screens:** one plain `h1` + one-line sentence per screen instead of icon tile + banner. Arrivals went from 7 columns to 5. Crowding matrix colours only busy cells. Suggestions collapse the twelve H1-H12 chips behind "Passed all 12 hard rules".
- **Tour:** shortened from 11 to 7 steps.
- **Type:** root font-size 16px (was 14px) so rem-based secondary text is at least 12px; uppercase micro-labels replaced with sentence case.
- **Bug fixed:** clicking a bus on the map showed "Vehicle telemetry unavailable" because the inspector received the vehicle object instead of its id.

### Transit Map Architecture
- Hand-authored schematic coordinates in `web/src/map/schematic.ts` using 45°/90° octolinear lines and station ticks.
- Central Hub S03 highlighted as a signature multi-route interchange circle with dashed pedestrian corridor (4-minute connection time).
- Metro Station S13 styled as campus entry portal.
- Switchable to Geographic true-metre coordinates without losing active vehicle telemetry or selections.

### State Management & Interactions
- Single source of truth for glossary terms in `web/src/content/glossary.ts` shared across popovers, drawer, and written docs.
- First-run experience persistence key: `rp_onboarded_v1` in `localStorage`.
- Spotlight tour built with zero external unbundled dependencies: custom accessible backdrop and target bounding box calculation with keyboard navigation (`Esc` closes, `Arrow` keys step).
- 100% offline self-containment: tested via Playwright assertions.

### Command Palette & Universal Shortcuts (P2 Deliverable)
- **Component:** `web/src/components/common/CommandPalette.tsx` accessible via `Ctrl/Cmd+K`, `/`, or the Search pill in the Status Ribbon.
- **Search Scope:** Instant filter across screens (1–6), active routes (R1–R4), stations (S01–S14), live vehicles (V01–V14), scenario triggers (S0–S3), and actions (Theme, Map Mode, Play/Pause, Tour, Help).
- **Keyboard Traversal:** Arrow Up/Down navigation, Enter execution, and Escape dismiss.
- **Global Shortcuts:** 1–6 switch screens, `T` toggles theme, `M` toggles map mode, `Space` plays/pauses simulation, `?` opens Help Centre.

### Interactive Minimap & Vehicle Tracking
- **Minimap:** Miniature corner viewport overlay tracking pan/zoom bounds in SVG coordinate space.
- **Follow Vehicle:** Real-time camera centering locking viewport to any selected vehicle as it travels along campus corridors.

### Quality Gate Verifications & Test Results
- **Cold-Read Reviewer Test:** Fresh research subagent tested with only `USER_GUIDE.md`. All 5 questions (project identity, color meanings, fixing overcrowding, arrival windows, testing breakdowns) answered accurately with zero hesitation.
- **Readability Grade:** Verified via Python tokenizer (`Flesch-Kincaid Grade: 5.38`, `Flesch Reading Ease: 73.62`), comfortably beating the ≤ 8.0 specification requirement.
- **Distinctiveness Tests:**
  - *Squint Test:* Passed — high-contrast schematic transit lines and load rings dominate the visual field even when severely blurred.
  - *Cover-the-Logo Test:* Passed — custom 5-zone control room layout with live ECG waveform, health pill, and bottom time scrubber cannot be mistaken for generic admin SaaS.
  - *5-Second Test:* Passed — Route R3 immediately registers as congested during morning peak via pulsing coral halo and warning indicators.
  - *Banned Pattern Scan:* Clean — zero purple/blue gradient buttons, zero emoji icons, zero uniform card grids, zero Inter defaults, zero lorem ipsum.

### Guided Tour & Auto-Demo: explain without hiding (revised)
- The tour used to centre a card over a dimmed, click-blocking backdrop, so the feature being explained was covered. Now each step **outlines the real UI element** with a pulsing ring (`data-tour="..."` hooks plus a few stable selectors) and parks its card in whichever stage corner overlaps that element, the open inspector and the map controls the least (`components/onboarding/spotlight.tsx`). Nothing is dimmed or click-blocked.
- The auto-demo caption uses the same placement and per-phase targets, and its timer is wall-clock based (the old timer advanced two phases at a time under React StrictMode).
- The inspector drawer is closed at every tour step so it cannot hide the next target. Tour length: 8 steps (`TOUR_STEP_COUNT` in `SimulationContext.tsx` must match `TOUR_STEPS`).
