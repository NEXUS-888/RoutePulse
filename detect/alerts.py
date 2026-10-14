"""
RoutePulse Conflict Detector & Alerts Engine (detect/alerts.py)
Implements Section 8.5 & Appendix A conflict detection.
Consumes simulation results, plan schedules, and disruptions.
Emits typed Alert instances conforming to core/schemas.py:
- A1: Overcrowding (soft, load >= 85%)
- A2: Capacity violation (hard-risk, demand exceeds rated capacity, pax left behind)
- A3: Unmet demand (balked pax > threshold per stop-hour)
- A4: Missed connection (transfer buffer < 4 min at hub S03)
- A5: Schedule conflict (overlapping trips on same vehicle or layover < 4 min)
- A6: Bunching / gap (headway < 40% or > 160% of planned)
- A7: Service gap (headway > max_headway or no accessible vehicle in route-hour)
- A8: Vehicle unavailable (assigned vehicle outside availability window / disruption)
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.schemas import (
    Alert,
    Disruption,
    NetworkResponse,
    Plan,
    Route,
    ServiceRules,
    Stop,
    Trip,
    Vehicle,
)
from sim.engine import SimulationResult, load_default_network

PLANNED_HEADWAYS: dict[str, float] = {
    "R1": 12.0,
    "R2": 15.0,
    "R3": 12.0,
    "R4": 30.0,
}


class ConflictDetector:
    """
    Detects operational and schedule conflicts across simulation results and plans.
    """

    def __init__(
        self,
        network: Optional[NetworkResponse] = None,
        rules: Optional[ServiceRules] = None,
        bunching_low_ratio: float = 0.40,
        gap_high_ratio: float = 1.60,
        soft_load_threshold: float = 0.85,
        balk_threshold_per_hour: int = 1,
        min_transfer_min: float = 4.0,
        min_layover_min: float = 4.0,
    ):
        self.network = network or load_default_network()
        self.rules = rules or ServiceRules()
        self.bunching_low_ratio = bunching_low_ratio
        self.gap_high_ratio = gap_high_ratio
        self.soft_load_threshold = soft_load_threshold
        self.balk_threshold_per_hour = balk_threshold_per_hour
        self.min_transfer_min = min_transfer_min
        self.min_layover_min = min_layover_min

        self.vehicles: dict[str, Vehicle] = {v.vehicle_id: v for v in self.network.vehicles}
        self.routes: dict[str, Route] = {r.route_id: r for r in self.network.routes}
        self.stops: dict[str, Stop] = {s.stop_id: s for s in self.network.stops}

    def detect(
        self,
        plan: Plan,
        sim_result: Optional[SimulationResult] = None,
        disruptions: Optional[list[Disruption]] = None,
    ) -> list[Alert]:
        """
        Runs comprehensive conflict detection on the plan and optional simulation results.
        Returns a sorted list of typed Alert objects.
        """
        alerts: list[Alert] = []
        alert_counter = 0

        def make_alert(
            code: Any,
            severity: str,
            title: str,
            detail: str,
            entity_type: str,
            entity_id: str,
            time_min: int,
            pax_affected: int,
        ) -> Alert:
            nonlocal alert_counter
            alert_counter += 1
            return Alert(
                alert_id=f"ALT-{alert_counter:03d}",
                code=code,
                severity=severity,  # type: ignore
                title=title,
                detail=detail,
                entity_type=entity_type,  # type: ignore
                entity_id=entity_id,
                time_min=time_min,
                pax_affected=max(0, pax_affected),
            )

        disruptions = disruptions or []

        # -------------------------------------------------------------------
        # 1. Simulation-backed Alerts: A1, A2, A3, A4
        # -------------------------------------------------------------------
        if sim_result is not None:
            # A1: Overcrowding (soft, load >= 85% of rated capacity)
            for t_id, tm in sim_result.trip_metrics.items():
                threshold = int(math.ceil(self.soft_load_threshold * tm.capacity))
                if tm.max_load >= threshold:
                    pct = (tm.max_load / max(1, tm.capacity)) * 100.0
                    alerts.append(make_alert(
                        code="A1",
                        severity="soft",
                        title=f"Overcrowding on Route {tm.route_id}",
                        detail=(
                            f"Trip {tm.trip_id} reached peak load of {tm.max_load}/{tm.capacity} pax "
                            f"({pct:.1f}%), exceeding the 85% comfort threshold."
                        ),
                        entity_type="trip",
                        entity_id=tm.trip_id,
                        time_min=tm.departure_min,
                        pax_affected=tm.max_load,
                    ))

            # A2: Capacity violation (hard-risk, demand exceeds capacity, pax left behind)
            for t_id, tm in sim_result.trip_metrics.items():
                if tm.left_behind_count > 0 or tm.max_load > tm.capacity:
                    affected = tm.left_behind_count if tm.left_behind_count > 0 else (tm.max_load - tm.capacity)
                    alerts.append(make_alert(
                        code="A2",
                        severity="hard-risk",
                        title=f"Capacity Risk on Route {tm.route_id}",
                        detail=(
                            f"Demand exceeded rated capacity ({tm.capacity} pax) on trip {tm.trip_id} "
                            f"departing at {tm.departure_min//60:02d}:{tm.departure_min%60:02d}; "
                            f"{affected} passengers left behind at stops."
                        ),
                        entity_type="trip",
                        entity_id=tm.trip_id,
                        time_min=tm.departure_min,
                        pax_affected=affected,
                    ))

            # A3: Unmet demand (balked passengers > threshold per stop-hour)
            balks_by_stop_hour: dict[Tuple[str, int], int] = defaultdict(int)
            for b in sim_result.balked_passengers:
                s_id = b["stop_id"]
                hour_bin = int(b["time_min"] // 60) * 60
                balks_by_stop_hour[(s_id, hour_bin)] += 1

            for (s_id, hour_bin), count in balks_by_stop_hour.items():
                if count >= self.balk_threshold_per_hour:
                    severity = "hard-risk" if count >= 10 else "soft"
                    alerts.append(make_alert(
                        code="A3",
                        severity=severity,
                        title=f"Unmet Demand at Stop {s_id}",
                        detail=(
                            f"Stop {s_id} experienced {count} balked passengers "
                            f"(waiting > 20 min patience limit) during hour "
                            f"{hour_bin//60:02d}:00–{hour_bin//60+1:02d}:00."
                        ),
                        entity_type="stop",
                        entity_id=s_id,
                        time_min=hour_bin,
                        pax_affected=count,
                    ))

            # A4: Missed connections (transfer buffer < 4 min)
            missed_by_conn: dict[Tuple[str, str], list[dict]] = defaultdict(list)
            for mc in sim_result.missed_connections:
                f_trip = mc["feeder_trip_id"]
                c_trip = mc["connecting_trip_id"]
                missed_by_conn[(f_trip, c_trip)].append(mc)

            for (f_trip, c_trip), records in missed_by_conn.items():
                count = len(records)
                first_rec = records[0]
                arr_min = first_rec["hub_arrival_min"]
                sched_dep = first_rec["connecting_scheduled_dep"]
                buf = first_rec["buffer_min"]
                alerts.append(make_alert(
                    code="A4",
                    severity="soft" if count < 20 else "hard-risk",
                    title="Tight Connection / Missed Connection at Hub",
                    detail=(
                        f"Feeder trip {f_trip} arrived at S03 at {int(arr_min//60):02d}:{int(arr_min%60):02d}; "
                        f"connecting trip {c_trip} departs at {int(sched_dep//60):02d}:{int(sched_dep%60):02d} "
                        f"(transfer buffer {buf:.1f} min < 4.0 min). {count} passengers missed connection."
                    ),
                    entity_type="trip",
                    entity_id=c_trip,
                    time_min=int(sched_dep),
                    pax_affected=count,
                ))

        # -------------------------------------------------------------------
        # 2. Schedule-based Alerts: A5, A6, A7, A8
        # -------------------------------------------------------------------

        # A5: Schedule conflict (overlapping trips or layover < min_layover)
        trip_lookup = {t.trip_id: t for t in plan.trips}
        vehicle_trips: dict[str, list[Trip]] = defaultdict(list)
        for t in plan.trips:
            vehicle_trips[t.vehicle_id].append(t)

        for v_id, trips in vehicle_trips.items():
            trips.sort(key=lambda t: t.departure_min)
            veh = self.vehicles.get(v_id)
            cap = veh.capacity if veh else 45

            for i in range(len(trips) - 1):
                t1 = trips[i]
                t2 = trips[i + 1]

                # Calculate t1 arrival/end time
                if t1.scheduled_stop_times:
                    t1_end = max(t1.scheduled_stop_times.values())
                else:
                    # Estimate based on route
                    t1_end = t1.departure_min + 20

                layover = t2.departure_min - t1_end
                if layover < self.min_layover_min:
                    alerts.append(make_alert(
                        code="A5",
                        severity="hard-risk",
                        title=f"Schedule Conflict for Vehicle {v_id}",
                        detail=(
                            f"Vehicle {v_id} has insufficient turnaround layover "
                            f"({layover:.1f} min < {self.min_layover_min} min) between trip {t1.trip_id} "
                            f"(ends {t1_end//60:02d}:{t1_end%60:02d}) and trip {t2.trip_id} "
                            f"(departs {t2.departure_min//60:02d}:{t2.departure_min%60:02d})."
                        ),
                        entity_type="vehicle",
                        entity_id=v_id,
                        time_min=t2.departure_min,
                        pax_affected=cap,
                    ))

        # A6: Bunching / Headway Gap (headway < 40% or > 160% of planned)
        # Group trips by (route_id, direction)
        route_trips: dict[Tuple[str, int], list[Trip]] = defaultdict(list)
        for t in plan.trips:
            route_trips[(t.route_id, t.direction)].append(t)

        for (r_id, direction), trips in route_trips.items():
            trips.sort(key=lambda t: t.departure_min)
            planned_h = PLANNED_HEADWAYS.get(r_id, 15.0)

            for i in range(len(trips) - 1):
                t1 = trips[i]
                t2 = trips[i + 1]
                h = t2.departure_min - t1.departure_min

                if h < self.bunching_low_ratio * planned_h:
                    alerts.append(make_alert(
                        code="A6",
                        severity="soft",
                        title=f"Bus Bunching on Route {r_id}",
                        detail=(
                            f"Headway between trips {t1.trip_id} and {t2.trip_id} is {h:.1f} min "
                            f"(< 40% of planned {planned_h:.1f} min), causing vehicle bunching."
                        ),
                        entity_type="route",
                        entity_id=r_id,
                        time_min=t2.departure_min,
                        pax_affected=int(h * 3),
                    ))
                elif h > self.gap_high_ratio * planned_h:
                    alerts.append(make_alert(
                        code="A6",
                        severity="soft",
                        title=f"Headway Gap on Route {r_id}",
                        detail=(
                            f"Headway between trips {t1.trip_id} and {t2.trip_id} is {h:.1f} min "
                            f"(> 160% of planned {planned_h:.1f} min), creating an uneven service gap."
                        ),
                        entity_type="route",
                        entity_id=r_id,
                        time_min=t2.departure_min,
                        pax_affected=int(h * 3),
                    ))

        # A7: Service gap (headway > max_headway or accessibility deficit)
        for (r_id, direction), trips in route_trips.items():
            trips.sort(key=lambda t: t.departure_min)
            for i in range(len(trips) - 1):
                t1 = trips[i]
                t2 = trips[i + 1]
                h = t2.departure_min - t1.departure_min
                is_peak = (450 <= t1.departure_min <= 630) or (990 <= t1.departure_min <= 1170)
                max_h = self.rules.max_headway_peak if is_peak else self.rules.max_headway_offpeak

                if h > max_h:
                    alerts.append(make_alert(
                        code="A7",
                        severity="hard-risk",
                        title=f"Service Gap on Route {r_id}",
                        detail=(
                            f"Headway of {h:.1f} min between trips {t1.trip_id} and {t2.trip_id} "
                            f"exceeds maximum permitted headway ({max_h} min)."
                        ),
                        entity_type="route",
                        entity_id=r_id,
                        time_min=t2.departure_min,
                        pax_affected=int(h * 4),
                    ))

            # Accessibility check: at least 1 accessible vehicle per route-hour
            # Divide plan into 60-min hours
            if trips:
                min_dep = min(t.departure_min for t in trips)
                max_dep = max(t.departure_min for t in trips)
                start_h = (min_dep // 60) * 60
                end_h = ((max_dep // 60) + 1) * 60

                for h_start in range(start_h, end_h, 60):
                    h_end = h_start + 60
                    hour_trips = [t for t in trips if h_start <= t.departure_min < h_end]
                    if hour_trips:
                        accessible_trips = [
                            t for t in hour_trips
                            if self.vehicles.get(t.vehicle_id) and self.vehicles[t.vehicle_id].accessible
                        ]
                        if len(accessible_trips) < self.rules.accessible_min_per_route_hour:
                            alerts.append(make_alert(
                                code="A7",
                                severity="hard-risk",
                                title=f"Accessibility Gap on Route {r_id}",
                                detail=(
                                    f"Route {r_id} has no accessible vehicle scheduled during "
                                    f"hour {h_start//60:02d}:00–{h_end//60:02d}:00 "
                                    f"(violates rule of minimum 1 accessible vehicle per route-hour)."
                                ),
                                entity_type="route",
                                entity_id=r_id,
                                time_min=h_start,
                                pax_affected=15,
                            ))

        # A8: Vehicle unavailable
        for trip in plan.trips:
            v_id = trip.vehicle_id
            veh = self.vehicles.get(v_id)
            if not veh:
                alerts.append(make_alert(
                    code="A8",
                    severity="hard-risk",
                    title=f"Unknown Vehicle {v_id}",
                    detail=f"Trip {trip.trip_id} is assigned to unknown vehicle {v_id}.",
                    entity_type="vehicle",
                    entity_id=v_id,
                    time_min=trip.departure_min,
                    pax_affected=45,
                ))
                continue

            # Availability window
            if trip.departure_min < veh.available_from or trip.departure_min > veh.available_to:
                alerts.append(make_alert(
                    code="A8",
                    severity="hard-risk",
                    title=f"Vehicle Outside Operating Hours: {v_id}",
                    detail=(
                        f"Vehicle {v_id} assigned to trip {trip.trip_id} departing at {trip.departure_min} min "
                        f"is outside operating window ({veh.available_from}–{veh.available_to} min)."
                    ),
                    entity_type="vehicle",
                    entity_id=v_id,
                    time_min=trip.departure_min,
                    pax_affected=veh.capacity,
                ))

            # Disruption vehicle_out
            for d in disruptions:
                if d.type == "vehicle_out":
                    out_vid = d.params.get("vehicle_id")
                    if out_vid == v_id and (d.start_min <= trip.departure_min <= d.end_min):
                        alerts.append(make_alert(
                            code="A8",
                            severity="hard-risk",
                            title=f"Vehicle Unavailable (Disruption): {v_id}",
                            detail=(
                                f"Vehicle {v_id} assigned to trip {trip.trip_id} at {trip.departure_min} min "
                                f"is out of service due to active disruption from {d.start_min} to {d.end_min} min."
                            ),
                            entity_type="vehicle",
                            entity_id=v_id,
                            time_min=trip.departure_min,
                            pax_affected=veh.capacity,
                        ))

        # Sort alerts: hard-risk first, then by pax_affected descending, then by time_min
        alerts.sort(key=lambda a: (0 if a.severity == "hard-risk" else 1, -a.pax_affected, a.time_min))

        # Re-index alert IDs sequentially after sorting
        for idx, a in enumerate(alerts, 1):
            a.alert_id = f"ALT-{idx:03d}"

        return alerts


def detect_conflicts(
    plan: Plan,
    sim_result: Optional[SimulationResult] = None,
    network: Optional[NetworkResponse] = None,
    rules: Optional[ServiceRules] = None,
    disruptions: Optional[list[Disruption]] = None,
) -> list[Alert]:
    """Convenience functional interface for conflict detection."""
    detector = ConflictDetector(network=network, rules=rules)
    return detector.detect(plan=plan, sim_result=sim_result, disruptions=disruptions)
