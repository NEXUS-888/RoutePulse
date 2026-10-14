"""
RoutePulse Accelerated Live Replayer
Simulates kinematic vehicle progression, GPS pings, APC occupancy, ETAs, and dynamic alerts.
Supports live accelerated SSE streaming, scenario injection, and real-feed ingestion.
"""
from __future__ import annotations
import asyncio
import json
import math
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from core.geometry import xy_to_latlon, euclidean_dist
from core.schemas import (
    Stop, Route, Vehicle, Transfer, Trip, Plan, GpsPing, ApcRecord,
    Alert, EtaPrediction, EtaResponse, VehicleEtaResponse, NetworkResponse
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class Replayer:
    """
    Kinematic replayer for RoutePulse transport simulation.
    Replays vehicle movements along network route polylines at accelerated speeds.
    """
    def __init__(self, fixtures_dir: Path = FIXTURES_DIR):
        self.fixtures_dir = fixtures_dir
        self.network: Optional[NetworkResponse] = None
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, Route] = {}
        self.vehicles: dict[str, Vehicle] = {}
        self.transfers: list[Transfer] = []
        self.baseline_plan: Optional[Plan] = None

        # Route cumulative distance geometries
        self._route_cum_dists: dict[str, list[float]] = {}
        self._route_total_len: dict[str, float] = {}
        self._stop_route_progress: dict[str, dict[str, float]] = {} # route_id -> {stop_id: progress_m}

        # Simulation state
        self.current_time_sec: float = 450 * 60.0 # 07:30:00 (27000s)
        self.speed: int = 30
        self.scenario_id: str = "S0"
        self.is_running: bool = False

        # Live vehicle states: vehicle_id -> state dict
        self.vehicle_states: dict[str, dict[str, Any]] = {}

        # Disruption flags
        self.traffic_multiplier: float = 1.0 # >1.0 in S1
        self.disabled_vehicles: set[str] = set() # {"B3"} in S2
        self.demand_spike_stop: Optional[str] = None # "S07" in S3

        # External ingested feeds
        self.ingested_pings: list[GpsPing] = []
        self.ingested_apc: list[ApcRecord] = []

        self._load_network()
        self._init_simulation()

    def _load_network(self) -> None:
        net_path = self.fixtures_dir / "network.json"
        if net_path.exists():
            with open(net_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.network = NetworkResponse(**data)
            self.stops = {s.stop_id: s for s in self.network.stops}
            self.routes = {r.route_id: r for r in self.network.routes}
            self.vehicles = {v.vehicle_id: v for v in self.network.vehicles}
            self.transfers = self.network.transfers
        else:
            from api.fixtures.create_fixtures import STOPS, ROUTES, VEHICLES, TRANSFERS
            self.network = NetworkResponse(
                stops=STOPS, routes=ROUTES, vehicles=VEHICLES, transfers=TRANSFERS
            )
            self.stops = {s.stop_id: s for s in STOPS}
            self.routes = {r.route_id: r for r in ROUTES}
            self.vehicles = {v.vehicle_id: v for v in VEHICLES}
            self.transfers = TRANSFERS

        # Compute polyline cumulative distances and stop progress along each route
        for r_id, route in self.routes.items():
            polyline = route.polyline
            cum = [0.0]
            for i in range(len(polyline) - 1):
                p1 = polyline[i]
                p2 = polyline[i + 1]
                d = euclidean_dist(p1, p2)
                cum.append(cum[-1] + d)
            self._route_cum_dists[r_id] = cum
            self._route_total_len[r_id] = cum[-1] if cum else 1.0

            # Map each stop in stop_sequence to its cumulative distance along the polyline
            stop_prog = {}
            for idx, sid in enumerate(route.stop_sequence):
                if idx < len(cum):
                    stop_prog[sid] = cum[idx]
            self._stop_route_progress[r_id] = stop_prog

        # Load baseline plan if available
        plan_path = self.fixtures_dir / "baseline_plan.json"
        if plan_path.exists():
            with open(plan_path, "r", encoding="utf-8") as f:
                self.baseline_plan = Plan(**json.load(f))

    def _init_simulation(self) -> None:
        """Initialise active vehicle operational states with realistic offsets."""
        self.vehicle_states = {}

        # Default vehicle assignment across routes
        assignments = [
            ("B1", "R1", 0.0, "T_R1_01"),
            ("B2", "R1", 0.5, "T_R1_02"),
            ("M1", "R2", 0.1, "T_R2_01"),
            ("M2", "R2", 0.6, "T_R2_02"),
            ("B3", "R3", 0.15, "T_R3_01"),
            ("B4", "R3", 0.65, "T_R3_02"),
            ("M3", "R4", 0.25, "T_R4_01"),
            ("M4", "R4", 0.75, "T_R4_02"),
            ("B5", "R3", 0.0, "T_R3_RES"), # Reserve / idle
            ("B6", "R1", 0.0, "T_R1_RES"), # Reserve / idle
        ]

        for vid, rid, offset_pct, trip_id in assignments:
            tot_len = self._route_total_len.get(rid, 1000.0)
            initial_prog = offset_pct * tot_len
            x, y, heading = self._interpolate_position(rid, initial_prog)
            lat, lon = xy_to_latlon(x, y)
            cap = self.vehicles[vid].capacity if vid in self.vehicles else 45

            # Initial load estimation
            init_load = 28 if vid == "B1" else (48 if vid == "B3" else 14)
            if vid in ("B5", "B6"):
                init_load = 0

            self.vehicle_states[vid] = {
                "vehicle_id": vid,
                "route_id": rid,
                "trip_id": trip_id,
                "progress_m": initial_prog,
                "x": x,
                "y": y,
                "lat": lat,
                "lon": lon,
                "heading": heading,
                "speed_mps": 7.5,
                "load": init_load,
                "capacity": cap,
                "status": "idle" if vid in ("B5", "B6") else "in_transit",
                "last_stop_id": self.routes[rid].stop_sequence[0] if rid in self.routes else "S01",
                "next_stop_id": self.routes[rid].stop_sequence[1] if rid in self.routes and len(self.routes[rid].stop_sequence) > 1 else "S02"
            }

    def _interpolate_position(self, route_id: str, progress_m: float) -> tuple[float, float, float]:
        """Interpolates (x, y, heading_degrees) along route polyline at progress_m."""
        cum = self._route_cum_dists.get(route_id, [0.0, 1000.0])
        polyline = self.routes[route_id].polyline if route_id in self.routes else [[0.0, 0.0], [1000.0, 0.0]]
        total_len = self._route_total_len.get(route_id, 1000.0)

        prog = progress_m % total_len
        for i in range(len(cum) - 1):
            if cum[i] <= prog <= cum[i + 1]:
                seg_len = cum[i + 1] - cum[i]
                u = (prog - cum[i]) / seg_len if seg_len > 0 else 0.0
                p1 = polyline[i]
                p2 = polyline[i + 1]
                x = p1[0] + u * (p2[0] - p1[0])
                y = p1[1] + u * (p2[1] - p1[1])

                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                # Heading in degrees clockwise from North
                angle_rad = math.atan2(dy, dx)
                heading = (450.0 - math.degrees(angle_rad)) % 360.0
                return round(x, 2), round(y, 2), round(heading, 1)

        p_last = polyline[-1] if polyline else [0.0, 0.0]
        return p_last[0], p_last[1], 0.0

    def reset(self, scenario_id: str = "S0", start_time_min: int = 450, speed: int = 30) -> None:
        """Reset replayer to initial or scenario state."""
        self.scenario_id = scenario_id
        self.current_time_sec = float(start_time_min * 60)
        self.speed = speed

        # Configure disruption scenarios
        self.traffic_multiplier = 1.0
        self.disabled_vehicles = set()
        self.demand_spike_stop = None

        if scenario_id == "S1":
            # S1: Traffic congestion around Main Gate / S01 corridor
            self.traffic_multiplier = 0.55
        elif scenario_id == "S2":
            # S2: Vehicle breakdown on bus B3
            self.disabled_vehicles.add("B3")
        elif scenario_id == "S3":
            # S3: Auditorium demand surge at S07
            self.demand_spike_stop = "S07"

        self._init_simulation()

    def ingest_gps(self, pings: list[GpsPing]) -> None:
        """Feed external GPS pings directly into vehicle state."""
        self.ingested_pings.extend(pings)
        for p in pings:
            vid = p.vehicle_id
            if vid in self.vehicle_states:
                self.vehicle_states[vid]["lat"] = p.lat
                self.vehicle_states[vid]["lon"] = p.lon
                self.vehicle_states[vid]["speed_mps"] = p.speed_mps
                self.vehicle_states[vid]["heading"] = p.heading
                self.vehicle_states[vid]["status"] = "in_transit"

    def ingest_apc(self, records: list[ApcRecord]) -> None:
        """Feed external APC passenger counts directly into vehicle state."""
        self.ingested_apc.extend(records)
        for r in records:
            # Find vehicle currently associated with trip_id
            for vid, st in self.vehicle_states.items():
                if st.get("trip_id") == r.trip_id:
                    st["load"] = r.load_after
                    st["last_stop_id"] = r.stop_id

    def step(self, dt_sec: float = 1.0) -> dict[str, Any]:
        """
        Advance simulation time by dt_sec * speed and compute current frame.
        Returns a rich tick payload.
        """
        sim_dt = dt_sec * self.speed
        self.current_time_sec += sim_dt

        pings: list[dict[str, Any]] = []
        active_count = 0

        for vid, st in self.vehicle_states.items():
            if vid in self.disabled_vehicles:
                st["status"] = "breakdown"
                st["speed_mps"] = 0.0
                continue

            if st["status"] == "idle":
                continue

            active_count += 1
            rid = st["route_id"]
            tot_len = self._route_total_len.get(rid, 1000.0)
            base_speed = self.routes[rid].free_flow_speed_mps if rid in self.routes else 8.0

            # Traffic multiplier applied
            eff_speed = base_speed * self.traffic_multiplier
            # Slight random kinematic variation
            jitter = (hash((vid, int(self.current_time_sec))) % 7 - 3) * 0.1
            eff_speed = max(2.5, eff_speed + jitter)

            st["progress_m"] = (st["progress_m"] + eff_speed * sim_dt) % tot_len
            x, y, heading = self._interpolate_position(rid, st["progress_m"])
            lat, lon = xy_to_latlon(x, y)

            st["x"] = x
            st["y"] = y
            st["lat"] = lat
            st["lon"] = lon
            st["heading"] = heading
            st["speed_mps"] = round(eff_speed, 2)

            # Determine nearest upcoming stop
            stop_seq = self.routes[rid].stop_sequence if rid in self.routes else []
            stop_progs = self._stop_route_progress.get(rid, {})
            next_stop = stop_seq[0] if stop_seq else "S01"
            for sid in stop_seq:
                if stop_progs.get(sid, 0.0) >= st["progress_m"]:
                    next_stop = sid
                    break
            st["next_stop_id"] = next_stop

            # Load evolution based on time of morning peak and stop
            t_min = self.current_time_sec / 60.0
            peak_factor = math.exp(-((t_min - 490.0) ** 2) / (2 * (40.0 ** 2))) # Peak around 08:10 (490 min)
            if rid == "R3":
                # High commuter ingress from Metro S13
                target_load = int(32 + 30 * peak_factor)
            elif rid == "R1":
                target_load = int(22 + 18 * peak_factor)
                if self.demand_spike_stop == "S07" and st["next_stop_id"] in ("S07", "S01"):
                    target_load += 15
            else:
                target_load = int(12 + 10 * peak_factor)

            # Smoothly drift load towards target_load
            curr_load = st["load"]
            st["load"] = max(0, curr_load + (1 if target_load > curr_load else (-1 if target_load < curr_load else 0)))

            pings.append({
                "vehicle_id": vid,
                "t_sec": int(self.current_time_sec),
                "lat": lat,
                "lon": lon,
                "speed_mps": st["speed_mps"],
                "heading": heading,
                "route_id": rid,
                "load": st["load"],
                "capacity": st["capacity"]
            })

        # Generate dynamic alerts based on current state
        alerts = self._detect_alerts()

        # Compute sample ETAs for central transfer hub S03
        etas = self.get_stop_eta("S03", int(self.current_time_sec / 60.0)).arrivals

        time_str = self.format_time(self.current_time_sec)

        return {
            "t_sec": int(self.current_time_sec),
            "time_str": time_str,
            "speed": self.speed,
            "scenario_id": self.scenario_id,
            "active_vehicles": active_count,
            "pings": pings,
            "alerts_count": len(alerts),
            "alerts": [a.model_dump() for a in alerts],
            "etas": [eta.model_dump() for eta in etas[:4]]
        }

    def _detect_alerts(self) -> list[Alert]:
        """Detect current real-time alerts A1-A8 based on vehicle loads, schedules, disruptions."""
        alerts: list[Alert] = []
        t_min = int(self.current_time_sec / 60.0)

        # Check vehicle capacity and overcrowding
        for vid, st in self.vehicle_states.items():
            if vid in self.disabled_vehicles:
                alerts.append(Alert(
                    alert_id=f"ALT-BRK-{vid}",
                    code="A7",
                    severity="hard-risk",
                    title=f"Vehicle Breakdown: {vid}",
                    detail=f"Vehicle {vid} has experienced a breakdown on {st['route_id']}. Reserve vehicle dispatch recommended.",
                    entity_type="vehicle",
                    entity_id=vid,
                    time_min=t_min,
                    pax_affected=35
                ))
                continue

            load = st["load"]
            cap = st["capacity"]
            if load > cap:
                alerts.append(Alert(
                    alert_id=f"ALT-CAP-{vid}",
                    code="A2",
                    severity="hard-risk",
                    title=f"Capacity Risk on {st['route_id']}",
                    detail=f"Passenger load ({load}) exceeds rated capacity ({cap}) on vehicle {vid}.",
                    entity_type="trip",
                    entity_id=st["trip_id"],
                    time_min=t_min,
                    pax_affected=load - cap + 15
                ))
            elif load >= 0.85 * cap:
                alerts.append(Alert(
                    alert_id=f"ALT-CROWD-{vid}",
                    code="A1",
                    severity="soft",
                    title=f"Heavy Load on {st['route_id']}",
                    detail=f"Vehicle {vid} is at {int((load / cap) * 100)}% capacity approaching {st['next_stop_id']}.",
                    entity_type="vehicle",
                    entity_id=vid,
                    time_min=t_min,
                    pax_affected=load
                ))

        # Check tight transfer connection at Hub S03
        if t_min in range(460, 480):
            alerts.append(Alert(
                alert_id="ALT-TIGHT-S03",
                code="A4",
                severity="soft",
                title="Tight Transfer Window at Hub S03",
                detail="Incoming Route R3 arrival is projected with < 3.5 min buffer before connecting Route R2 departure.",
                entity_type="stop",
                entity_id="S03",
                time_min=t_min,
                pax_affected=14
            ))

        # Check S3 demand spike
        if self.demand_spike_stop == "S07":
            alerts.append(Alert(
                alert_id="ALT-DEMAND-S07",
                code="A6",
                severity="hard-risk",
                title="Surge Queue at Auditorium S07",
                detail="Auditorium event outflow exceeds baseline capacity; projected wait time exceeds 15 minutes.",
                entity_type="stop",
                entity_id="S07",
                time_min=t_min,
                pax_affected=85
            ))

        return alerts

    def get_stop_eta(self, stop_id: str, t_min: Optional[int] = None) -> EtaResponse:
        """Computes upcoming vehicle arrivals at stop_id with P10/P50/P90 confidence windows."""
        query_min = t_min if t_min is not None else int(self.current_time_sec / 60.0)
        arrivals: list[EtaPrediction] = []

        # Find routes that serve this stop
        for r_id, route in self.routes.items():
            if stop_id not in route.stop_sequence:
                continue
            target_prog = self._stop_route_progress.get(r_id, {}).get(stop_id, 0.0)
            tot_len = self._route_total_len.get(r_id, 1000.0)

            # Find vehicles running on this route
            for vid, st in self.vehicle_states.items():
                if st.get("route_id") != r_id or st.get("status") in ("idle", "breakdown"):
                    continue

                curr_prog = st["progress_m"]
                dist = (target_prog - curr_prog) % tot_len
                if dist < 50.0 and curr_prog > target_prog:
                    dist += tot_len

                speed = max(3.0, st["speed_mps"])
                travel_time_sec = dist / speed
                travel_time_min = travel_time_sec / 60.0

                eta_p50 = round(query_min + travel_time_min, 1)
                eta_p10 = round(max(query_min + 0.5, eta_p50 - 0.2 * travel_time_min), 1)
                eta_p90 = round(eta_p50 + 0.3 * travel_time_min, 1)

                reasons = []
                confidence: Any = "high"
                if self.traffic_multiplier < 0.7:
                    confidence = "medium"
                    reasons.append("Corridor traffic congestion detected")
                else:
                    reasons.append("Normal campus flow")

                if st["load"] > st["capacity"]:
                    reasons.append("High dwell time expected due to boarding queue")

                arrivals.append(EtaPrediction(
                    stop_id=stop_id,
                    route_id=r_id,
                    vehicle_id=vid,
                    trip_id=st.get("trip_id", f"T_{r_id}_{vid}"),
                    scheduled_time_min=int(eta_p50),
                    eta_p10_min=eta_p10,
                    eta_p50_min=eta_p50,
                    eta_p90_min=eta_p90,
                    confidence=confidence,
                    reasons=reasons,
                    stale_gps=False
                ))

        arrivals.sort(key=lambda a: a.eta_p50_min)
        return EtaResponse(
            stop_id=stop_id,
            query_time_min=query_min,
            arrivals=arrivals
        )

    def get_vehicle_eta(self, vehicle_id: str, t_min: Optional[int] = None) -> VehicleEtaResponse:
        """Computes downstream stop arrivals for a specific vehicle."""
        query_min = t_min if t_min is not None else int(self.current_time_sec / 60.0)
        st = self.vehicle_states.get(vehicle_id)
        if not st:
            return VehicleEtaResponse(
                vehicle_id=vehicle_id,
                trip_id=None,
                current_progress_m=0.0,
                speed_mps=0.0,
                downstream_stops=[]
            )

        rid = st["route_id"]
        route = self.routes.get(rid)
        downstream: list[EtaPrediction] = []
        if route:
            curr_prog = st["progress_m"]
            tot_len = self._route_total_len.get(rid, 1000.0)
            stop_progs = self._stop_route_progress.get(rid, {})

            for sid in route.stop_sequence:
                sprog = stop_progs.get(sid, 0.0)
                dist = (sprog - curr_prog) % tot_len
                travel_min = (dist / max(3.0, st["speed_mps"])) / 60.0
                eta_p50 = round(query_min + travel_min, 1)

                downstream.append(EtaPrediction(
                    stop_id=sid,
                    route_id=rid,
                    vehicle_id=vehicle_id,
                    trip_id=st["trip_id"],
                    scheduled_time_min=int(eta_p50),
                    eta_p10_min=round(eta_p50 - 0.2 * travel_min, 1),
                    eta_p50_min=eta_p50,
                    eta_p90_min=round(eta_p50 + 0.3 * travel_min, 1),
                    confidence="high",
                    reasons=["Vehicle on schedule"],
                    stale_gps=False
                ))

        return VehicleEtaResponse(
            vehicle_id=vehicle_id,
            trip_id=st.get("trip_id"),
            current_progress_m=round(st["progress_m"], 1),
            speed_mps=st["speed_mps"],
            downstream_stops=downstream
        )

    async def stream(
        self,
        speed: int = 30,
        scenario_id: str = "S0",
        start_time_min: int = 450,
        interval_sec: float = 1.0,
        max_ticks: Optional[int] = None
    ) -> AsyncGenerator[dict, None]:
        """SSE streaming generator yielding tick events at accelerated speed."""
        self.speed = speed
        self.scenario_id = scenario_id
        if start_time_min is not None:
            self.current_time_sec = float(start_time_min * 60)

        tick_count = 0
        while True:
            payload = self.step(dt_sec=interval_sec)
            yield {
                "event": "tick",
                "data": json.dumps(payload)
            }
            tick_count += 1
            if max_ticks is not None and tick_count >= max_ticks:
                break
            await asyncio.sleep(interval_sec)

    @staticmethod
    def format_time(t_sec: float) -> str:
        s = int(t_sec)
        h = (s // 3600) % 24
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"


# Global Replayer instance
_replayer_instance: Optional[Replayer] = None


def get_replayer() -> Replayer:
    global _replayer_instance
    if _replayer_instance is None:
        _replayer_instance = Replayer()
    return _replayer_instance
