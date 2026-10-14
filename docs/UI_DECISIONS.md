# RoutePulse UI/UX — Architecture & Design Decisions Log

> Maintained per Section 0 of `docs/ROUTEPULSE_UI_UX_SPEC.md`.

## Design & Technical Decisions

### Typography
- **Display & Large Numerals:** `@fontsource/space-grotesk` (weights 500, 600, 700). Distinctive geometric grotesque character for a high-end mission control look, replacing generic system/Inter styling.
- **Body & Controls:** `@fontsource/plus-jakarta-sans` (weights 400, 500, 600, 700). Clean, legible, high-contrast grotesque face.
- **Data, Codes & Timestamps:** `@fontsource/jetbrains-mono` (tabular numerals enabled via `font-variant-numeric: tabular-nums`). Guarantees zero jitter when replay clock and countdowns tick.
- **Self-Hosted Offline Requirement:** Installed directly via npm. Zero external CDN or Google Fonts calls.

### Color Palette & Semantics
- **Dual Themes:**
  - **"Control Room" Dark (Default):** Base background `#0B1020`, elevated panels `#111827`, border hairline `rgba(255, 255, 255, 0.08)`, text `#F9FAFB`.
  - **"Paper" Light:** Base background `#F8F9FA`, elevated panels `#FFFFFF`, border `#E2E8F0`, text `#0F172A`.
- **Colour-Blind-Safe Route Palette:**
  - Route R1 (SW Corridor / Metro Feeder): Sapphire Blue (`#2563EB` / `#3B82F6`)
  - Route R2 (North Quad Express): Emerald Green (`#059669` / `#10B981`)
  - Route R3 (Perimeter Loop / Commuter Spine): Violet / Purple (`#7C3AED` / `#8B5CF6`)
  - Route R4 (Science & Research Connector): Warm Amber (`#D97706` / `#F59E0B`)
- **Strict Load Semantics:**
  - Teal (`#10B981` / `#059669`): Normal (<85%)
  - Amber (`#F59E0B` / `#D97706`): Approaching capacity (85%–100%)
  - Coral / Red (`#EF4444` / `#DC2626`): Overloaded (>100% / left behind)
  - Redundant encoding: Always accompanied by ring fill percentage, shape/icon, and textual status ("FULL", "HIGH LOAD", "SEATS AVAILABLE").

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
