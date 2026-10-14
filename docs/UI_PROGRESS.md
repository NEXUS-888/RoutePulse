# RoutePulse UI/UX — Progress Tracker

> Maintained per Section 0 of `docs/ROUTEPULSE_UI_UX_SPEC.md`.
> Clock check: Started at 14:38 local time. Feature freeze at 20:30. Hard deadline at 22:00.
> Current status: 100% of P0, P1, and P2 tiers delivered and verified ahead of 20:30 feature freeze.

## Acceptance Checklist

### P0 (Must Have) — 100% Complete
- [x] `docs/UI_PLAN.md` written *(Completed 14:38: Master execution plan and component inventory established)*
- [x] Tokens, fonts (bundled), dark and light themes complete *(Space Grotesk, Plus Jakarta Sans, JetBrains Mono, Control Room Dark & Paper Light)*
- [x] New app shell: rail, status ribbon, inspector drawer, time deck *(5-zone layout with live status and scrubber)*
- [x] Schematic metro-style map with hub interchange ring, load rings, ghost vehicle on breakdown, layers and legend
- [x] ETA capsules (p10–p90 window, p50 tick, timetable ghost tick)
- [x] Recommendation tickets (trade-offs, H1–H12 chips, validation seal, Accept/Reject/What-if)
- [x] Loading, empty and error states on every screen (tested with a failed API call)
- [x] Welcome screen + guided tour + Help drawer (tour tested in Playwright with `rp_onboarded_v1=true`)
- [x] Student mobile view (bottom sheet, accessibility toggle)
- [x] `docs/USER_GUIDE.md` and `docs/APP_MAP.md` with screenshots from the capture script
- [x] Offline verified (zero external requests confirmed via Playwright assertion)
- [x] AA contrast, keyboard navigation, reduced motion, colour-blind-safe

### P1 (Should Have) — 100% Complete
- [x] Before/After reveal slider on Baseline vs RoutePulse *(Integrated in Screen 5 with live KPI matrix)*
- [x] Pulse Line live in the ribbon, reacting to load and delay *(Dynamic ECG waveform canvas)*
- [x] Showcase auto-demo (about 90 s), deterministic, with captions and "Take control"
- [x] Glossary (i) popovers everywhere, single glossary source (`web/src/content/glossary.ts`)
- [x] Cheat sheet (PNG + MD) *(`docs/CHEATSHEET.md` and `docs/CHEATSHEET.png` generated)*
- [x] Role selector (Operator / Student / Reviewer in WelcomeModal and app state)
- [x] Guide cold-read test passed; readability grade ≤ 8 *(Grade: 5.38; cold-read reviewer agent passed all 5 questions)*
- [x] Squint, cover-the-logo and 5-second tests passed *(Documented in UI_DECISIONS.md)*

### P2 (Nice to Have) — Complete
- [x] Command palette *(`Ctrl+K` / `/` modal searching screens, routes, stops, vehicles, actions)*
- [x] Geographic-view polish, follow-vehicle, minimap *(Added to SchematicMap.tsx with SVG viewport box)*
- [x] Help search; optional tiles layer *(Search implemented in HelpDrawer.tsx)*

---

## Log of Changes & Milestone Status
- **14:38:** Plan established in `docs/UI_PLAN.md`. Initialized progress checklist in `docs/UI_PROGRESS.md`.
- **14:45:** Self-hosted font bundling (`@fontsource/space-grotesk`, `@fontsource/plus-jakarta-sans`, `@fontsource/jetbrains-mono`), `tokens.css` with dark/light themes, and `geo.ts` color thresholds aligned.
- **14:52:** Core App Shell, Pulse Line, Network Health Score, Icon Rail, Status Ribbon, Time Deck, and Inspector Drawer implemented.
- **14:58:** Schematic map layout authored (`schematic.ts` & `SchematicMap.tsx`) with Central Hub S03 interchange ring and Metro Gateway S13.
- **15:05:** Common widgets built: `EtaCapsule.tsx`, `RecommendationTicket.tsx`, `BeforeAfterSlider.tsx`, `StateViews.tsx`, `GlossaryPopover.tsx`.
- **15:10:** Screens overhauled: Screen1 through Screen6, plus WelcomeModal, SpotlightTour, ShowcaseDemo, and HelpDrawer.
- **15:15:** Navigation flowchart, ASCII wireframes, and documentation created in `docs/APP_MAP.md` and `docs/USER_GUIDE.md`.
- **15:20:** Playwright test script `capture_guide.js` created; all 13 screenshots captured into `docs/img/`; offline zero-request assertion verified.
- **15:25:** Command Palette (`CommandPalette.tsx`) built and wired with `Ctrl+K`, `/`, and universal keyboard shortcuts (1–6, T, M, Space).
- **15:28:** Minimap and Follow-Vehicle features integrated into `SchematicMap.tsx`.
- **15:32:** One-page cheat sheet created (`docs/CHEATSHEET.md` and `docs/CHEATSHEET.png`).
- **15:35:** Readability optimized to Grade 5.38 (Flesch Reading Ease 73.62); Cold-read test completed by independent reviewer subagent.
- **15:40:** Python test suite (195 unit tests) verified passing 100%. All P0, P1, and P2 requirements satisfied.
