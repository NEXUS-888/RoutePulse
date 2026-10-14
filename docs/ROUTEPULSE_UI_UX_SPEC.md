# RoutePulse — UI/UX Overhaul, Onboarding, User Guide & Map Layout Spec

> **Companion to `ROUTEPULSE_ARCHITECTURE.md`** (Sections 10, 11, 14). That file is the source of truth for the system; this file is the source of truth for everything the user sees.
> **Scope:** ./web only, plus docs. **Do NOT change** API contracts, schemas, validator, optimizer, or evaluation logic.
> **Deadline: 22:00 today. Feature freeze: 20:30.** Check the clock at the start of every phase and follow the tiers in Section 8.

---

## 0. Working Protocol (keeps context from being lost)

This is a long task. To avoid drifting or forgetting requirements:

1. **Re-read this file at the start of every phase** and before every major component. Do not rely on memory of earlier messages.
2. **Maintain `docs/UI_PROGRESS.md`**: a checklist copied from Section 9 (Acceptance Checklist). After every completed piece, tick it, add one line on what changed, and note anything cut or at risk. This file is the memory between phases.
3. **Maintain `docs/UI_DECISIONS.md`**: any design or technical decision made (fonts chosen, palette hex values, libraries added, why something was cut). Short bullets.
4. **Write `docs/UI_PLAN.md` first** (one page: components to replace or create, build order). Show it, then proceed without waiting if there is no reply within 5 minutes.
5. **Commit after each piece** with a clear message. Run `make test` and Playwright smoke tests after each piece. Never break API contracts or `make demo`.
6. If this file is edited by the user mid-task, the latest version wins. Re-read it and reconcile `UI_PROGRESS.md`.
7. Use the **frontend-design skill**, **Playwright / Browser MCP** (visual QA), **Context7 or equivalent** (current library docs), and **Filesystem/Git MCP**. If something is unavailable, use the closest equivalent and record it in `UI_DECISIONS.md`.

---

## 1. Design Direction: "Mission control meets transit map"

**Goal:** it should look like a premium transit-authority control room, not a template dashboard. A judge should remember it after 10 seconds.

**Core concept: "A subway map that is alive."** The hero is a full-bleed schematic transit map. Everything else is quiet and supports the map.

### 1.1 Identity
- **Signature motif: the Pulse Line.** A small ECG-style waveform in the top ribbon showing live network stress. Amplitude rises with load factor and delay; it beats in sync with the replay clock. Also used on the welcome screen and as the logo/favicon mark. Keep it small and tasteful: a signature, not a gimmick.
- **Logo lockup:** "RoutePulse" with the pulse line forming an underline or crossbar. Tagline: *"Plan the campus. Don't just watch it."*
- **Metro-map aesthetic:** the main map is a **schematic** diagram (45°/90° line segments, rounded corners, station ticks, a large interchange ring at the Central Hub S03). Station coordinates are **hand-authored** in `web/src/map/schematic.ts` (do not auto-generate the layout). A toggle switches to the true-geometry view.

### 1.2 Themes (both required)
- **"Control Room" dark (default):** deep ink background (around `#0B1020`), 1px hairline borders, subtle grain, soft glow only on live elements.
- **"Paper" light:** warm off-white for projectors and bright rooms. Same components, same hierarchy.
- All colours, radii, spacing, type scale and motion are CSS variables in `web/src/styles/tokens.css`. **No hard-coded colours in components.**

### 1.3 Colour and meaning
- Four route colours, **colour-blind-safe** (test with deuteranopia and protanopia simulation).
- Load language is the same everywhere: **teal** = comfortable, **amber** = 85% load or more, **coral** = over 100% / passengers left behind.
- **Never rely on colour alone:** add shape, pattern, icon or label redundancy (e.g., ring fill pattern, "FULL" label).
- Status colours are reserved for status. Do not use them for decoration.

### 1.4 Typography (self-hosted, offline)
- Install via `@fontsource` (no Google Fonts CDN). One distinctive geometric/grotesque **display face** for headings and big numbers, one clean **text face**, one **mono face** for IDs and codes.
- **Tabular numerals** for all times and counts. ETA times are **large and legible**.
- Do **not** use the default Inter/Roboto/system look.

### 1.5 Banned patterns
Uniform card grids; purple/blue gradient SaaS look; default component-library styling; emoji used as icons; lorem ipsum; centered-hero-with-three-feature-cards layouts; generic admin-template look.

### 1.6 Layout (desktop)
| Zone | Content |
|---|---|
| **Left: icon rail** | Slim navigation; hover to expand labels |
| **Top: status ribbon** | Logo, scenario chip, simulated clock, Pulse Line, **Network Health** score, theme toggle, Help (?) button, "Replay tour" |
| **Centre: map (hero)** | Full-bleed, never boxed into a small card |
| **Right: inspector drawer** | Slides in on selection (stop, vehicle, alert, recommendation) |
| **Bottom: time deck** | Scrubber, play/pause, speed (1x/10x/30x), demand heat-strip, event and disruption markers, "Now" playhead |

Panels: frosted-glass feel with hairline borders; restrained shadows; consistent 8px grid; generous spacing.

### 1.7 Network Health score (exact definition; show in a tooltip and in the guide)
```
Network Health = max(0, 100
    − 40 × (share of trips over capacity)
    − 30 × (share of passengers left behind)
    − 20 × (share of transferring passengers who missed their connection)
    − 10 × (share of trips delayed by more than 3 minutes))
```
Colour bands: 80–100 teal, 60–79 amber, below 60 coral.

---

## 2. Signature Interactions (the "unique attraction")

1. **Before / After reveal slider.** Drag a handle across the map; left half shows the **Baseline** plan (overloaded routes coral, passengers piling up), right half shows the **RoutePulse** plan (balanced). KPIs count up underneath. This is the hero moment of the demo.
2. **Vehicle glyphs.** Capsule markers with a **load ring** (fill = load factor); pulsing halo above 85%; a broken-down vehicle shows as a **ghost** with a dashed outline.
3. **ETA capsules.** A horizontal capsule showing the **p10–p90 window**, a bold tick for **p50**, and a faint ghost tick for **what the timetable promised**. Hover explains in plain words ("Bus is 2 min late, traffic ahead is easing").
4. **Recommendation "tickets".** Big animated count-up deltas (wait, left-behind, missed connections); a **Gain vs Cost** row; constraint chips **H1–H12** that tick green one by one; a **"Validated, 0 violations"** seal; buttons **Accept / Reject / Try what-if**.
5. **Command palette** (Ctrl/Cmd+K; P2): jump to any stop, vehicle, route, scenario or action ("Inject vehicle breakdown").
6. **Motion:** purposeful only, 150–250 ms, ease-out. Respect `prefers-reduced-motion`.

---

## 3. Quality Bars

- WCAG AA contrast, visible focus rings, full keyboard navigation, aria-labels on map elements, alt text on charts.
- **States on every screen:** skeleton loader, friendly empty state, and an error state with a recovery action (e.g., "ETA unavailable. Switch to baseline ETA"). Test each by simulating a failed API call in Playwright.
- Responsive: desktop-first (check 1280, 1440, 1920 widths); the Student view is mobile-first (390 × 844).
- Map stays smooth at 30x replay with 10 vehicles: memoise, never re-render the whole SVG each tick.
- Works fully offline; all assets bundled; Playwright asserts zero external network requests.
- Suggested libraries (add only if needed, all bundled): `framer-motion`, `zustand`, `d3-shape` + `d3-scale`, `driver.js` or a small custom spotlight component, `cmdk`, `@fontsource/*`. Keep Recharts only where it already works and restyle it with the tokens.

---

## 4. First-Run Experience

First run is detected with localStorage key `rp_onboarded_v1`. The Help menu has **Replay tour** and **Reset onboarding**.

### 4.1 Splash and welcome (about 6 seconds, then a card)
The Pulse Line draws across the screen, resolves into the logo and tagline, then fades into a **Welcome card** with three big choices (no long text):
1. **Take the 90-second tour** (guided spotlight tour)
2. **Watch the auto-demo** (hands-free showcase)
3. **Explore on my own** (a small "?" pulses once)

Also a **role selector** (Operator / Student / Judge-Reviewer) that sets the default screen and tour order.

### 4.2 Guided spotlight tour (11 steps; each ≤ 25 words; Back / Next / Skip; progress dots; Esc closes; resumable)
Dim the page, spotlight the element, and where possible perform a real action ("Try it"). If a target is missing, navigate to the right screen first.
1. Welcome: RoutePulse does not just show buses, it plans them.
2. Status ribbon: Network Health and the Pulse Line; what the colours mean.
3. The map: vehicles, load rings, hub; click a vehicle (auto-select one).
4. Time deck: scrub time, change speed; auto-jump to the morning peak.
5. ETA board: arrival windows vs timetable; hover a capsule.
6. Alerts: overcrowding, missed connection, schedule conflict; open one.
7. Recommendations: read a ticket: reason, impact, trade-off, constraints.
8. Accept one: watch chips tick, the "0 violations" seal, and KPIs update.
9. Scenario Lab: inject a traffic delay, breakdown or demand spike; watch detect → recommend → recover.
10. Results: Baseline vs RoutePulse with confidence ranges; the Before/After slider.
11. Help: where the guide, glossary, shortcuts and tour replay live.

A Playwright test must walk the tour end to end.

### 4.3 Showcase mode ("Watch the 90-second demo")
Hands-free, **deterministic** (fixed seed), captions at the bottom (one short sentence per step), progress bar, **"Take control"** button to exit anytime, **"Reset demo"** button. Script (matches `ROUTEPULSE_ARCHITECTURE.md` Section 17): morning-peak baseline overload → ETA windows → accept a recommendation → inject a disruption → recovery → Baseline vs RoutePulse results.

### 4.4 Contextual help
A small (i) next to every unfamiliar term opens a one-sentence plain-language popover. **One glossary source of truth**: `web/src/content/glossary.ts`, reused by the popovers, the in-app Help centre and the written guide.

### 4.5 Help centre
Opened with the **?** key or button; slide-over drawer with search, glossary, role guides, "How do I...?" recipes, shortcuts, and "Replay tour". **Esc** closes any drawer or tour.

---

## 5. User Guide (clear, short, not overwhelming)

**Rules:** write for a non-technical reader at about grade 7–8 reading level. Short sentences. No jargon without a definition the first time it appears. "You" language. One idea per paragraph. **No section longer than about 90–150 words.** Every screen section follows this pattern: **What you see / What you can do / Why it matters.**

Deliver, all generated from the same source content so they never disagree:

### 5.1 `docs/USER_GUIDE.md` (aim for roughly 3–5 printed pages)
1. **Start here:** what RoutePulse is (3 sentences), who it is for, and a **"Try it in 2 minutes"** box with 5 numbered steps.
2. **Pick your path:** Operator / Student / Reviewer, one short "Your first 3 minutes" each.
3. **The screen in one picture:** a single annotated screenshot with numbered callouts (map, ribbon, time deck, ETA capsule, alerts, recommendations).
4. **Screen by screen:** Command Centre, Live Map, ETA Board, Demand & Alerts, Recommendations, Scenario Lab, Results, Student View (pattern above).
5. **Colour and symbol legend:** one table.
6. **Key ideas in plain words:** arrival window, load, baseline, left-behind passenger, missed connection, hard rule (constraint), trade-off, Network Health (with the exact formula from Section 1.7).
7. **Common tasks (3–5 steps each):** "Why is a bus late?", "Fix an overcrowded route", "Test a breakdown", "Compare with the baseline", "Check a plan is valid".
8. **FAQ and troubleshooting:** e.g., "The map is empty", "Why is the ETA a range?", "Why can't I accept this recommendation?"
9. **Keyboard shortcuts and accessibility features** (`?` = Help, `Esc` = close, `Ctrl/Cmd+K` = palette if built).

Screenshots are captured automatically by a Playwright script (`npm run capture-guide`) into `docs/img/` with numbered callouts. Run it **after** the UI freeze (around 20:00).

### 5.2 In-app Help centre
Renders the same content (Section 4.5).

### 5.3 One-page cheat sheet
`docs/CHEATSHEET.md` and `docs/CHEATSHEET.png`: legend + 5 steps + shortcuts, printable and slide-ready.

---

## 6. Map Layout (two meanings; deliver both)

### 6.1 The campus map (in the app)
- **Two views, one toggle:** *Schematic* (default, subway-style, hand-authored) and *Geographic* (true local-metre geometry). Same data, same interactions.
- **Layers** (toggle in a compact legend panel): Routes, Stops, Vehicles, Load rings, Demand glow under stops, Alerts, Transfers/hub, Accessibility (ramp vehicles and accessible stops), Disruption zones (hatched overlay on affected segments), Plan comparison (baseline ghost lines).
- **Stops:** station ticks with collision-avoiding labels. **Central Hub S03** is a large interchange ring with the **4-minute walk transfer** as a dashed link. **Metro Station S13** is drawn as an "entry gate" to the campus.
- **Interaction:** hover = tooltip (next arrivals with windows); click = inspector drawer; double-click a route to isolate it; scroll to zoom; drag to pan; minimap in a corner; "Fit all" and "Follow vehicle" buttons.
- **Legend:** always available and collapsible; uses the same visual language as the guide's legend.
- **Rendering:** SVG only, no external tiles. An optional "OSM tiles" layer toggle may exist but is hidden when offline.

### 6.2 The app map (navigation and information architecture): `docs/APP_MAP.md`
A **Mermaid diagram** of screens and links plus an **ASCII wireframe** of the main layout (rail, ribbon, map, inspector, time deck) and of the Student bottom-sheet layout. For each screen: purpose, who uses it, primary action, entry points, links to other screens.

Screens: **Command Centre** (map hero + KPIs + top alerts) · **Live Map** · **ETA Board** · **Demand & Alerts** · **Recommendations** · **Scenario Lab** · **Results** (Baseline vs RoutePulse) · **Student View** · **Help Centre**.

### 6.3 Student view (mobile-first, 390 × 844)
A **bottom sheet** with from/to, a **large ETA window** (p50 big, window smaller), a transfer-safe indicator, an **accessibility toggle**, and "next bus is crowded" warnings with a later alternative. Same tokens, fonts and colour language as the operator UI.

---

## 7. Quality Gates (verify with screenshots, not opinions)

**Process:** build → Playwright screenshots (1440×900 and 390×844, both themes) → critique against this spec → fix. Minimum **3 rounds** on the Command Centre, and at least one round on each other screen.

**Distinctiveness tests**
- **Squint test:** blur a screenshot; the schematic map must still dominate and read as the product.
- **Cover-the-logo test:** if it could pass for a generic admin template, redo the shell.
- **5-second test:** the Command Centre screenshot must make obvious which route is in trouble and why.
- **Banned-list scan:** none of the patterns in Section 1.5.

**Usability tests**
- **Guide cold-read test:** spawn a fresh reviewer agent that has **not** seen the project. Give it only `docs/USER_GUIDE.md` and ask: *What is this? What do the colours mean? How do I fix an overcrowded route? What is an arrival window? How do I test a breakdown?* If any answer is wrong or hesitant, simplify that section and retest.
- **Readability check:** Flesch–Kincaid grade ≤ 8.
- **Tour test:** Playwright walks all tour steps; skip, resume and replay work.

**Technical**
- WCAG AA contrast; keyboard navigation; reduced-motion respected; colour-blind-safe palette.
- No layout breakage at 1280, 1440, 1920 and 390 (Student).
- Zero external requests (offline).
- `make test` and `make demo` still pass; existing API contracts unchanged.

---

## 8. Build Order and Priority Tiers (follow the clock)

**Build order:** tokens + themes + fonts → app shell (rail, ribbon, inspector, time deck) → map restyle → ETA capsules, alert list, recommendation tickets → states (loading/empty/error) → welcome + tour + Help drawer → Student view → Before/After slider → Pulse Line → showcase mode → guide and screenshots → cheat sheet and APP_MAP.

| Tier | Items | Time guide |
|---|---|---|
| **P0 (must)** | Tokens + both themes + fonts; new app shell; restyled schematic map with legend; ETA capsules; recommendation tickets; states (loading/empty/error); welcome + tour + Help drawer; Student view; `USER_GUIDE.md` + `APP_MAP.md` | about 60–70 min |
| **P1** | Before/After slider; Pulse Line; showcase auto-demo; glossary popovers everywhere; cheat sheet; cold-read test; role selector | about 30–40 min |
| **P2 (only if ahead)** | Command palette; geographic-view polish; follow-vehicle; minimap; optional tiles layer; Help search | remainder |

**Cut-lines:** if time is short, drop P2, then P1 from the bottom. **Never ship a half-styled app:** finish the shell and tokens consistently across **all** screens before starting any P1 item. If under about 3 hours remain, do P0 plus the auto-demo only.

---

## 9. Acceptance Checklist (copy into `docs/UI_PROGRESS.md` and tick as you go)

**P0**
- [ ] `docs/UI_PLAN.md` written
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

**P1**
- [ ] Before/After reveal slider on Baseline vs RoutePulse
- [ ] Pulse Line live in the ribbon, reacting to load and delay
- [ ] Showcase auto-demo (about 90 s), deterministic, with captions and "Take control"
- [ ] Glossary (i) popovers everywhere, single glossary source
- [ ] Cheat sheet (PNG + MD)
- [ ] Role selector (Operator / Student / Reviewer)
- [ ] Guide cold-read test passed; readability grade ≤ 8
- [ ] Squint, cover-the-logo and 5-second tests passed

**P2**
- [ ] Command palette
- [ ] Geographic-view polish, follow-vehicle, minimap
- [ ] Help search; optional tiles layer

---

## 10. Final Report (when done or at the 20:30 freeze)

Report with screenshots of: splash, welcome card, each tour step, Command Centre in both themes, the Before/After slider, a recommendation ticket, the Student mobile view. Include the cold-read test results, the ticked checklist from `UI_PROGRESS.md`, and a list of anything cut and why.
