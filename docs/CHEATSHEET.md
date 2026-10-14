# RoutePulse — Quick Reference Cheat Sheet

> **One-Page Operator & Reviewer Reference** · Single Source of Truth for RoutePulse UI/UX
> Printable & Slide-Ready · 100% Offline Transit Planning Workspace

---

```
+========================================================================================================+
|                                  ROUTEPULSE OPERATOR CHEAT SHEET                                      |
|                             "Plan the campus. Don't just watch it."                                    |
+========================================================================================================+
```

## 1. Visual & Symbol Legend

| Category | Indicator | Visual Marker | Plain Language Meaning |
|---|---|---|---|
| **Passenger Load** | **Comfortable** | `● Teal Ring (<85%)` | Seats available; passengers board freely |
| | **Crowded** | `● Amber Ring (85–100%)` | High load; standing room only; monitor closely |
| | **Overcrowded** | `● Coral Ring (>100%)` | Over capacity; passengers left behind at stop |
| **Corridors** | **Route R1** | `━━ Sapphire Blue (#3B82F6)` | Main Loop: Main Gate ↔ Admin ↔ Central Hub ↔ Science |
| | **Route R2** | `━━ Emerald Green (#10B981)` | Hostel Express: High-frequency loop serving student dorms |
| | **Route R3** | `━━ Radiant Purple (#8B5CF6)`| Metro Connector: Primary commuter spine linking rail to campus |
| | **Route R4** | `━━ Amber Gold (#F59E0B)` | Research Shuttle: Central Hub ↔ Research Quad & Sports |
| **Key Nodes** | **Central Hub (S03)** | `◎ Double Purple Ring` | Main interchange with dashed 4-minute walking corridor |
| | **Metro Station (S13)** | `■ Cyan Gate Square` | Regional commuter rail entry gateway into campus |
| | **Breakdown Bus** | `◌ Dashed Coral Ghost` | Mechanical vehicle breakdown (Scenario S2 event) |

---

## 2. Five-Step Workflows

```
+--------------------------------------------------------------------------------------------------------+
|                                     5-STEP OPERATOR QUICKSTART                                         |
+--------------------------------------------------------------------------------------------------------+
| 1. MONITOR HEALTH   | Check Top Ribbon: Watch live Pulse Line and Network Health (target > 80 Teal).   |
| 2. SPOT BOTTLENECK  | Look at Schematic Map: Observe which corridor turns coral during peak rush.     |
| 3. REVIEW TICKET    | Open Recommendations: Check delta metrics (saved wait time and riders rescued). |
| 4. VERIFY & APPLY   | Confirm 0 Hard Rule Violations (H1–H12); click "Accept & Apply Live".            |
| 5. REVEAL GAIN      | Open Scenario Lab: Drag Before/After slider to confirm left-behind drop of 66%.  |
+--------------------------------------------------------------------------------------------------------+
```

```
+--------------------------------------------------------------------------------------------------------+
|                                      5-STEP STUDENT QUICKSTART                                         |
+--------------------------------------------------------------------------------------------------------+
| 1. OPEN STUDENT VIEW| Click graduation cap in Left Rail (opens mobile 390x844 bottom sheet).           |
| 2. SELECT STOPS     | Pick start (Metro Gateway S13) and destination (Library S04).                    |
| 3. ARRIVAL WINDOW   | Read reliable p10–p90 time band (e.g. 08:27–08:33 AM) instead of fragile single min.|
| 4. CHECK CROWDING   | If next bus is crowded (88%), check "Next Bus" recommendation 8 min later.       |
| 5. ACCESSIBILITY    | Toggle wheelchair ramp filter to display only accessible low-floor shuttles.      |
+--------------------------------------------------------------------------------------------------------+
```

---

## 3. Keyboard Shortcuts & Controls

| Key Shortcut | Action | Where Used |
|---|---|---|
| **`?`** or **`h`** | Open / Close Help Centre & Glossary Drawer | Anywhere |
| **`Esc`** | Close Inspector Drawer, Modal, Tour, or Command Palette | Anywhere |
| **`Ctrl+K`** or **`/`** | Open Command Palette (Jump to screens, stops, buses) | Anywhere |
| **`Spacebar`** | Play / Pause Simulation Replay Clock | Anywhere |
| **`1`, `2`, `3`, `4`, `5`, `6`** | Jump to Screen 1 (Map) through Screen 6 (Student) | Anywhere |
| **`T`** | Toggle Theme (Paper Light ↔ Control Room Dark) | Anywhere |
| **`M`** | Toggle Map View (Subway Schematic ↔ Geographic) | Anywhere |
| **Click Stop / Bus** | Open detailed Inspector Drawer telemetry | Map & ETA Board |
| **Double-Click Route**| Isolate and spotlight selected route | Map |

---

## 4. Operational Guardrails & Core Math

- **Network Health Formula:**
  $$\text{Health} = \max(0, 100 - 40 \times \text{overcap} - 30 \times \text{leftbehind} - 20 \times \text{missedconn} - 10 \times \text{delays})$$
  - `80 – 100`: **Teal (Optimal)** · Smooth operations, comfortable seating
  - `60 – 79`:  **Amber (Strained)** · High load, standing room only
  - `< 60`:     **Coral (Critical)** · Overcrowding, left-behind queues
- **Hard Constraints (H1–H12):** Always 0 violations allowed (fleet capacity limits, driver breaks, battery bounds, 4-minute transfer walk).
- **Offline Guarantee:** 100% self-hosted, bundled local fonts (`Space Grotesk`, `JetBrains Mono`, `Plus Jakarta Sans`), 0 outside network calls.
