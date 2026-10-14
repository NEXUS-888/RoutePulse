# RoutePulse UI/UX — Progress Tracker

> Maintained per Section 0 of `docs/ROUTEPULSE_UI_UX_SPEC.md`.
> Clock check: Started at 14:38 local time. Feature freeze at 20:30. Hard deadline at 22:00.

## Acceptance Checklist

### P0 (Must Have)
- [x] `docs/UI_PLAN.md` written *(Completed 14:38: Master execution plan and component inventory established)*
- [ ] Tokens, fonts (bundled), dark and light themes complete
- [ ] New app shell: rail, status ribbon, inspector drawer, time deck
- [ ] Schematic metro-style map with hub interchange ring, load rings, ghost vehicle on breakdown, layers and legend
- [ ] ETA capsules (p10–p90 window, p50 tick, timetable ghost tick)
- [ ] Recommendation tickets (trade-offs, H1–H12 chips, validation seal, Accept/Reject/What-if)
- [ ] Loading, empty and error states on every screen (tested with a failed API call)
- [ ] Welcome screen + guided tour + Help drawer (tour tested in Playwright)
- [ ] Student mobile view (bottom sheet, accessibility toggle)
- [ ] `docs/USER_GUIDE.md` and `docs/APP_MAP.md` with screenshots from the capture script
- [ ] Offline verified (zero external requests)
- [ ] AA contrast, keyboard navigation, reduced motion, colour-blind-safe

### P1 (Should Have)
- [ ] Before/After reveal slider on Baseline vs RoutePulse
- [ ] Pulse Line live in the ribbon, reacting to load and delay
- [ ] Showcase auto-demo (about 90 s), deterministic, with captions and "Take control"
- [ ] Glossary (i) popovers everywhere, single glossary source
- [ ] Cheat sheet (PNG + MD)
- [ ] Role selector (Operator / Student / Reviewer)
- [ ] Guide cold-read test passed; readability grade ≤ 8
- [ ] Squint, cover-the-logo and 5-second tests passed

### P2 (Nice to Have - Time Permitting)
- [ ] Command palette
- [ ] Geographic-view polish, follow-vehicle, minimap
- [ ] Help search; optional tiles layer

---

## Log of Changes & Milestone Status
- **14:38:** Plan established in `docs/UI_PLAN.md`. Initialized progress checklist in `docs/UI_PROGRESS.md`.
