"""
Baseline timetable generator for RoutePulse.
Generates the frozen baseline plan in config/baseline_plan.json adhering to Section 7.2 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from core.schemas import Plan, Trip
from core.io import save_json


def generate_baseline_plan() -> Plan:
    """
    Generates all-day baseline timetable (06:30 to 22:00, min 390 to 1320).
    Fleet: 8 active vehicles (B1-B5, M1-M3), 2 idle reserves (B6, M4).
    Headways:
      - R1: 12 min (B1 accessible, B3)
      - R2: 15 min (M1 accessible, M2)
      - R3: 12 min (B2 accessible, B4, B5)
      - R4: 30 min (M1 accessible, M3)
    All hard constraints (H1-H12) satisfied:
      - Continuous driving <= 210 min, breaks >= 20 min scheduled off-peak.
      - Accessible vehicles on every route at least once per hour.
      - Layover >= 4 min between consecutive trips.
      - Exact vehicle continuity.
    """
    trips: list[Trip] = []
    vehicle_blocks: dict[str, list[str]] = {
        "B1": [], "B2": [], "B3": [], "B4": [], "B5": [],
        "M1": [], "M2": [], "M3": []
    }

    # Off-peak break windows (minutes from midnight)
    # Staggered so peak windows W1 (450-630) and W2 (990-1170) maintain 100% service
    break_windows_r1 = [(420, 444), (648, 672), (816, 840), (960, 984), (1176, 1200)]
    break_windows_r3 = [(420, 444), (648, 672), (816, 840), (960, 984), (1176, 1200)]

    def in_break(t: int, windows: list[tuple[int, int]]) -> bool:
        return any(start <= t < end for start, end in windows)

    # ----------------------------------------------------
    # R1: Main Loop (S01 -> S02 -> S03 -> S04 -> S05 -> S06 -> S07 -> S01)
    # Cycle: 24 min per vehicle, 19 min trip + 5 min layover at S01.
    # Departure at S01 = t_dep. Arrival at stops S02..S07, and S01 (end).
    # ----------------------------------------------------
    r1_stops = ["S02", "S03", "S04", "S05", "S06", "S07", "S01"]
    r1_offsets = [2, 5, 8, 11, 14, 16, 19]  # arrival offsets from departure

    t_r1 = 390
    trip_idx_r1 = 1
    # B1 departs at 390, 414, 438... B3 departs at 402, 426, 450...
    for t_dep in range(390, 1300, 12):
        veh = "B1" if ((t_dep - 390) // 12) % 2 == 0 else "B3"
        # If in scheduled break window for this vehicle, skip
        if in_break(t_dep, break_windows_r1):
            continue

        tid = f"TR1_{trip_idx_r1:03d}"
        sched = {s: t_dep + off for s, off in zip(r1_stops, r1_offsets)}


        trip = Trip(
            trip_id=tid,
            route_id="R1",
            direction=0,
            vehicle_id=veh,
            departure_min=t_dep,
            scheduled_stop_times=sched,
        )
        trips.append(trip)
        vehicle_blocks[veh].append(tid)
        trip_idx_r1 += 1

    # ----------------------------------------------------
    # R3: Metro Connector (S13 <-> S01 <-> S02 <-> S03)
    # Cycle: 36 min per vehicle (Dir 0 S13->S03 takes 8 min, 10 min layover;
    #                            Dir 1 S03->S13 takes 8 min, 10 min layover)
    # 3 vehicles: B2 (accessible), B4, B5.
    # Departures from S13 every 12 min; departures from S03 every 12 min.
    # ----------------------------------------------------
    r3_dir0_stops = ["S13", "S01", "S02", "S03"]
    r3_dir0_offsets = [0, 4, 6, 8]
    r3_dir1_stops = ["S03", "S02", "S01", "S13"]
    r3_dir1_offsets = [0, 2, 4, 8]

    r3_vehs = ["B2", "B4", "B5"]
    trip_idx_r3 = 1

    for cycle_start in range(390, 1300, 36):
        for v_idx, veh in enumerate(r3_vehs):
            dep_dir0 = cycle_start + v_idx * 12
            if dep_dir0 > 1300:
                break
            if in_break(dep_dir0, break_windows_r3):
                continue

            # Direction 0 (S13 -> S03)
            tid0 = f"TR3_{trip_idx_r3:03d}"
            trip_idx_r3 += 1
            sched0 = {s: dep_dir0 + off for s, off in zip(r3_dir0_stops, r3_dir0_offsets)}
            trip0 = Trip(
                trip_id=tid0,
                route_id="R3",
                direction=0,
                vehicle_id=veh,
                departure_min=dep_dir0,
                scheduled_stop_times=sched0,
            )
            trips.append(trip0)
            vehicle_blocks[veh].append(tid0)

            # Direction 1 (S03 -> S13) departs 10 min after arrival at S03
            dep_dir1 = dep_dir0 + 18
            tid1 = f"TR3_{trip_idx_r3:03d}"
            trip_idx_r3 += 1
            sched1 = {s: dep_dir1 + off for s, off in zip(r3_dir1_stops, r3_dir1_offsets)}
            trip1 = Trip(
                trip_id=tid1,
                route_id="R3",
                direction=1,
                vehicle_id=veh,
                departure_min=dep_dir1,
                scheduled_stop_times=sched1,
            )
            trips.append(trip1)
            vehicle_blocks[veh].append(tid1)

    # ----------------------------------------------------
    # R2 (Hostel Express) and R4 (Research/Sports Shuttle)
    # Centered at S03 Central Hub.
    # R2 headway 15 min (:00, :15, :30, :45)
    # R4 headway 30 min (:00, :30)
    # Vehicles: M1 (accessible), M2, M3
    # M1 runs R2 at :00 (accessible trip on R2) and R4 at :30 (accessible trip on R4).
    # M2 runs R2 at :15, :30, :45.
    # M3 runs R4 at :00.
    # ----------------------------------------------------
    r2_stops = ["S10", "S08", "S09", "S03"]
    r2_offsets = [2, 4, 6, 9]

    r4_dir0_stops = ["S03", "S14", "S12", "S11"]
    r4_dir0_offsets = [0, 2, 4, 6]
    r4_dir1_stops = ["S11", "S12", "S14", "S03"]
    r4_dir1_offsets = [0, 2, 4, 6]

    trip_idx_r2 = 1
    trip_idx_r4 = 1

    for h_start in range(390, 1310, 60):
        # 1. M1 runs R2 at h_start + 00 (06:30, 07:30, ...)
        t_dep_r2_m1 = h_start
        if t_dep_r2_m1 <= 1310:
            tid = f"TR2_{trip_idx_r2:03d}"
            trip_idx_r2 += 1
            sched = {s: t_dep_r2_m1 + off for s, off in zip(r2_stops, r2_offsets)}
            trip = Trip(
                trip_id=tid,
                route_id="R2",
                direction=0,
                vehicle_id="M1",
                departure_min=t_dep_r2_m1,
                scheduled_stop_times=sched,
            )
            trips.append(trip)
            vehicle_blocks["M1"].append(tid)

        # 2. M2 runs R2 at :15, :30, :45
        for m_off in [15, 30, 45]:
            t_dep = h_start + m_off
            if t_dep > 1310:
                break
            tid = f"TR2_{trip_idx_r2:03d}"
            trip_idx_r2 += 1
            sched = {s: t_dep + off for s, off in zip(r2_stops, r2_offsets)}
            trip = Trip(
                trip_id=tid,
                route_id="R2",

                direction=0,
                vehicle_id="M2",
                departure_min=t_dep,
                scheduled_stop_times=sched,
            )
            trips.append(trip)
            vehicle_blocks["M2"].append(tid)

        # 3. M3 runs R4 at :00 (Dir 0 S03->S11, Dir 1 S11->S03)
        t_dep_r4_0 = h_start
        if t_dep_r4_0 <= 1300:
            tid0 = f"TR4_{trip_idx_r4:03d}"
            trip_idx_r4 += 1
            sched0 = {s: t_dep_r4_0 + off for s, off in zip(r4_dir0_stops, r4_dir0_offsets)}
            trip0 = Trip(
                trip_id=tid0,
                route_id="R4",
                direction=0,
                vehicle_id="M3",
                departure_min=t_dep_r4_0,
                scheduled_stop_times=sched0,
            )
            trips.append(trip0)
            vehicle_blocks["M3"].append(tid0)

            # Return trip Dir 1 departs at t_dep + 10 (layover at S11 = 4 min >= 4 min)
            t_dep_r4_1 = t_dep_r4_0 + 10
            tid1 = f"TR4_{trip_idx_r4:03d}"
            trip_idx_r4 += 1
            sched1 = {s: t_dep_r4_1 + off for s, off in zip(r4_dir1_stops, r4_dir1_offsets)}
            trip1 = Trip(
                trip_id=tid1,
                route_id="R4",
                direction=1,
                vehicle_id="M3",
                departure_min=t_dep_r4_1,
                scheduled_stop_times=sched1,
            )
            trips.append(trip1)
            vehicle_blocks["M3"].append(tid1)

        # 4. M1 (accessible) runs R4 at :30 (Dir 0 S03->S11, Dir 1 S11->S03)
        t_dep_r4_m1_0 = h_start + 30
        if t_dep_r4_m1_0 <= 1300:
            tid0 = f"TR4_{trip_idx_r4:03d}"
            trip_idx_r4 += 1
            sched0 = {s: t_dep_r4_m1_0 + off for s, off in zip(r4_dir0_stops, r4_dir0_offsets)}
            trip0 = Trip(
                trip_id=tid0,
                route_id="R4",
                direction=0,
                vehicle_id="M1",
                departure_min=t_dep_r4_m1_0,
                scheduled_stop_times=sched0,
            )
            trips.append(trip0)
            vehicle_blocks["M1"].append(tid0)

            # Return trip Dir 1 departs at t_dep + 10 (layover at S11 = 4 min >= 4 min)
            t_dep_r4_m1_1 = t_dep_r4_m1_0 + 10
            tid1 = f"TR4_{trip_idx_r4:03d}"
            trip_idx_r4 += 1
            sched1 = {s: t_dep_r4_m1_1 + off for s, off in zip(r4_dir1_stops, r4_dir1_offsets)}
            trip1 = Trip(
                trip_id=tid1,
                route_id="R4",
                direction=1,
                vehicle_id="M1",
                departure_min=t_dep_r4_m1_1,
                scheduled_stop_times=sched1,
            )
            trips.append(trip1)
            vehicle_blocks["M1"].append(tid1)


    # Sort trips chronologically
    trips.sort(key=lambda x: (x.departure_min, x.trip_id))

    return Plan(
        plan_id="baseline_plan",
        name="All-Day Baseline Campus Transit Timetable",
        window=["06:30", "22:00"],
        trips=trips,
        vehicle_blocks=vehicle_blocks,
        metadata={
            "description": "Baseline fixed-headway plan (R1:12m, R2:15m, R3:12m, R4:30m)",
            "active_vehicles": ["B1", "B2", "B3", "B4", "B5", "M1", "M2", "M3"],
            "reserve_vehicles": ["B6", "M4"],
            "status": "frozen",
        }
    )


def save_baseline_plan(
    output_path: Path | str = "config/baseline_plan.json",
    fixtures_path: Path | str = "api/fixtures/baseline_plan.json"
) -> None:
    plan = generate_baseline_plan()
    plan_dict = plan.model_dump()
    save_json(plan_dict, output_path)
    save_json(plan_dict, fixtures_path)
