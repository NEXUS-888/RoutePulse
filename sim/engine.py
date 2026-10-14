"""
RoutePulse Discrete-Event Simulator (sim/engine.py)
Implements Section 8.5 & Appendix B:
- Discrete-event simulation using heapq.
- Simulates Plan forward against passenger demand and travel time model.
- Models FIFO queueing, boarding up to rated vehicle capacity, left-behind passengers.
- Passenger patience limit (20 min) -> balking / unmet demand.
- Dwell time coupling: max(6, 5 + 1.4*boardings + 0.8*alightings) seconds.
- Hub S03 transfer tracking with 4 min buffer; detects missed connections.
- Emits detailed KPIs, per-trip metrics, ApcRecords, and passenger traces.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from core.config import load_config
from core.io import load_json
from core.schemas import (
    ApcRecord,
    DemandObs,
    Disruption,
    NetworkResponse,
    Plan,
    Route,
    Stop,
    Transfer,
    Trip,
    Vehicle,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "api" / "fixtures"


# ---------------------------------------------------------------------------
# Data classes for discrete event simulation
# ---------------------------------------------------------------------------

@dataclass
class Passenger:
    """Represents a passenger journey in the simulator."""
    pax_id: str
    origin: str
    destination: str
    arrival_time_min: float
    route_id: str
    direction: int
    needs_transfer: bool = False
    connecting_route_id: Optional[str] = None
    connecting_direction: Optional[int] = None
    final_destination: Optional[str] = None

    # Lifecycle state
    status: str = "waiting"  # "waiting", "boarded", "completed", "balked"
    leg: int = 1             # 1 = first leg, 2 = after transfer at S03
    board_time_min: Optional[float] = None
    alight_time_min: Optional[float] = None
    transfer_arrival_min: Optional[float] = None
    connecting_board_min: Optional[float] = None
    final_alight_min: Optional[float] = None
    balk_time_min: Optional[float] = None
    left_behind_count: int = 0
    missed_connection: bool = False
    connecting_trip_expected: Optional[str] = None

    @property
    def total_wait_min(self) -> float:
        """Total time spent waiting across all legs."""
        wait = 0.0
        if self.board_time_min is not None:
            wait += max(0.0, self.board_time_min - self.arrival_time_min)
        elif self.balk_time_min is not None and self.leg == 1:
            wait += max(0.0, self.balk_time_min - self.arrival_time_min)

        if self.needs_transfer and self.transfer_arrival_min is not None:
            if self.connecting_board_min is not None:
                wait += max(0.0, self.connecting_board_min - self.transfer_arrival_min)
            elif self.balk_time_min is not None and self.leg == 2:
                wait += max(0.0, self.balk_time_min - self.transfer_arrival_min)
        return wait


@dataclass(order=True)
class SimEvent:
    """Event in the discrete-event min-heap."""
    time: float
    priority: int       # 1: PASSENGER_ARRIVAL, 2: VEHICLE_ARRIVAL, 3: VEHICLE_DEPARTURE, 4: PASSENGER_BALK
    counter: int        # Tie breaker
    event_type: str = field(compare=False)
    payload: Any = field(compare=False)


@dataclass
class TripMetrics:
    """Detailed load and operational statistics for a single trip."""
    trip_id: str
    route_id: str
    vehicle_id: str
    direction: int
    departure_min: int
    actual_departure: Optional[float] = None
    actual_arrival: Optional[float] = None
    capacity: int = 45
    seated: int = 30
    accessible: bool = False
    stop_arrivals: dict[str, float] = field(default_factory=dict)
    stop_departures: dict[str, float] = field(default_factory=dict)
    stop_boardings: dict[str, int] = field(default_factory=dict)
    stop_alightings: dict[str, int] = field(default_factory=dict)
    stop_loads: dict[str, int] = field(default_factory=dict)
    max_load: int = 0
    passengers_boarded: int = 0
    left_behind_count: int = 0
    distance_km: float = 0.0
    seat_km_offered: float = 0.0
    seat_km_used: float = 0.0

    @property
    def is_overcrowded(self) -> bool:
        """True if maximum load reached or exceeded 85% rated capacity."""
        return self.max_load >= int(math.ceil(0.85 * self.capacity))

    @property
    def is_capacity_violated(self) -> bool:
        """True if passengers were left behind due to lack of space or load > capacity."""
        return self.left_behind_count > 0 or self.max_load > self.capacity


@dataclass
class SimulationResult:
    """Summary and granular outputs of a simulation run."""
    plan_id: str
    seed: int
    kpis: dict[str, float]
    trip_metrics: dict[str, TripMetrics]
    apc_records: list[ApcRecord]
    passengers: list[Passenger]
    missed_connections: list[dict[str, Any]]
    balked_passengers: list[dict[str, Any]]
    vehicle_km: float
    seat_km_offered: float
    seat_km_used: float
    fleet_utilization: float


# ---------------------------------------------------------------------------
# Default Network Loader & Route Topology Helpers
# ---------------------------------------------------------------------------

def load_default_network() -> NetworkResponse:
    """Loads network definition from fixtures."""
    net_path = FIXTURES_DIR / "network.json"
    if net_path.exists():
        data = load_json(net_path)
        return NetworkResponse(**data)
    raise FileNotFoundError(f"Network fixture not found at {net_path}")


class NetworkTopology:
    """Helper to inspect route sequences, transfer logic, and segment lengths."""

    def __init__(self, network: NetworkResponse):
        self.network = network
        self.stops: dict[str, Stop] = {s.stop_id: s for s in network.stops}
        self.routes: dict[str, Route] = {r.route_id: r for r in network.routes}
        self.vehicles: dict[str, Vehicle] = {v.vehicle_id: v for v in network.vehicles}
        self.transfers: list[Transfer] = network.transfers
        self.hub_id = "S03"

    def get_trip_stop_sequence(self, route_id: str, direction: int) -> list[str]:
        route = self.routes[route_id]
        if route.type == "linear" and direction == 1:
            return list(reversed(route.stop_sequence))
        return list(route.stop_sequence)

    def get_trip_segment_lengths(self, route_id: str, direction: int) -> list[float]:
        route = self.routes[route_id]
        if route.type == "linear" and direction == 1:
            return list(reversed(route.segment_lengths_m))
        return list(route.segment_lengths_m)

    def find_direct_route(self, origin: str, destination: str) -> Optional[Tuple[str, int]]:
        """Finds if a direct route connects origin and destination."""
        for r_id, route in self.routes.items():
            if route.type == "linear":
                # Check direction 0
                seq0 = route.stop_sequence
                if origin in seq0 and destination in seq0:
                    if seq0.index(origin) < seq0.index(destination):
                        return (r_id, 0)
                # Check direction 1
                seq1 = list(reversed(route.stop_sequence))
                if origin in seq1 and destination in seq1:
                    if seq1.index(origin) < seq1.index(destination):
                        return (r_id, 1)
            else:
                # Loop route
                seq = route.stop_sequence
                # Origin and destination in loop
                indices = [i for i, s in enumerate(seq) if s == origin]
                dest_indices = [i for i, s in enumerate(seq) if s == destination]
                for o_idx in indices:
                    for d_idx in dest_indices:
                        if o_idx < d_idx:
                            return (r_id, 0)
        return None

    def plan_itinerary(self, origin: str, destination: str) -> Tuple[str, int, bool, Optional[str], Optional[int]]:
        """
        Returns (route_id, direction, needs_transfer, connecting_route, connecting_dir).
        """
        direct = self.find_direct_route(origin, destination)
        if direct:
            return (direct[0], direct[1], False, None, None)

        # Must transfer at S03
        leg1 = self.find_direct_route(origin, self.hub_id)
        leg2 = self.find_direct_route(self.hub_id, destination)
        if leg1 and leg2:
            return (leg1[0], leg1[1], True, leg2[0], leg2[1])

        # Fallback if topology doesn't explicitly match
        return ("R1", 0, False, None, None)


# ---------------------------------------------------------------------------
# Travel Time Model (Section 7.3 & Traffic Realization)
# ---------------------------------------------------------------------------

class TravelTimeModel:
    """
    Computes segment traversal times based on free-flow speed, time-of-day
    congestion profiles, lognormal noise, and disruptions.
    """

    def __init__(
        self,
        network: Optional[NetworkResponse] = None,
        deterministic: bool = True,
        lognormal_sigma: float = 0.12,
        morning_mult: tuple[float, float] = (1.25, 1.40),
        evening_mult: tuple[float, float] = (1.20, 1.35),
        disruptions: Optional[list[Disruption]] = None,
        seed: int = 20261014,
    ):
        self.network = network or load_default_network()
        self.deterministic = deterministic
        self.lognormal_sigma = lognormal_sigma
        self.morning_mult = morning_mult
        self.evening_mult = evening_mult
        self.disruptions = disruptions or []
        self.rng = np.random.default_rng(seed)

    def get_segment_travel_time_min(
        self,
        route_id: str,
        from_stop: str,
        to_stop: str,
        departure_time_min: float,
        length_m: float,
        free_flow_speed_mps: float = 8.0,
    ) -> float:
        """Calculates travel time across a segment in minutes."""
        base_sec = length_m / max(1.0, free_flow_speed_mps)

        # Time-of-day congestion profile
        # Morning peak: 07:45 - 09:15 (465 - 555 min)
        # Evening peak: 16:45 - 18:30 (1005 - 1110 min)
        congestion = 1.0
        is_metro_or_gate = (
            (from_stop in ["S13", "S01"] and to_stop in ["S01", "S02", "S13"]) or
            (from_stop in ["S01", "S02"] and to_stop in ["S01", "S13"])
        )

        if 465 <= departure_time_min <= 555:
            # Morning peak
            congestion = self.morning_mult[1] if is_metro_or_gate else self.morning_mult[0]
        elif 1005 <= departure_time_min <= 1110:
            # Evening peak
            congestion = self.evening_mult[1] if is_metro_or_gate else self.evening_mult[0]

        # Apply active disruptions (e.g. S1 traffic disruption)
        for d in self.disruptions:
            if d.type == "traffic":
                if d.start_min <= departure_time_min <= d.end_min:
                    affected_corridor = d.params.get("corridor", "metro_gate")
                    if affected_corridor == "metro_gate" and is_metro_or_gate:
                        mult = float(d.params.get("multiplier", 1.35))
                        congestion *= mult

        # Noise component
        if not self.deterministic:
            noise = float(self.rng.lognormal(0.0, self.lognormal_sigma))
            intersection_delay_sec = float(self.rng.exponential(4.0))
            total_sec = base_sec * congestion * noise + intersection_delay_sec
        else:
            total_sec = base_sec * congestion

        return max(0.1, total_sec / 60.0)


# ---------------------------------------------------------------------------
# Synthetic Demand Generator
# ---------------------------------------------------------------------------

def generate_peak_demand(
    topology: NetworkTopology,
    window_start_min: int = 450,  # 07:30
    window_end_min: int = 630,    # 10:30
    total_arrivals: int = 1500,
    seed: int = 20261014,
) -> list[Passenger]:
    """
    Generates realistic morning peak passenger arrivals (07:30-10:30)
    focused on Metro (S13) -> Campus, creating realistic peak loading on R3 and R1.
    """
    rng = np.random.default_rng(seed)
    passengers: list[Passenger] = []

    # Stop weights during morning peak (Metro S13 and Main Gate S01 dominate)
    origin_weights = {
        "S13": 0.40,  # Metro station influx
        "S01": 0.20,  # Main Gate influx
        "S08": 0.10,  # Hostel A
        "S09": 0.08,  # Hostel B
        "S03": 0.07,  # Central Hub
        "S10": 0.05,  # Food court
        "S04": 0.02,
        "S05": 0.02,
        "S06": 0.02,
        "S07": 0.01,
        "S11": 0.01,
        "S12": 0.01,
        "S14": 0.01,
        "S02": 0.00,
    }
    stops = list(origin_weights.keys())
    weights = [origin_weights[s] for s in stops]

    dest_weights = {
        "S03": 0.25,
        "S05": 0.20,  # Engineering
        "S06": 0.15,  # Science
        "S04": 0.15,  # Library
        "S07": 0.10,  # Auditorium
        "S02": 0.05,  # Admin
        "S12": 0.05,  # Research
        "S11": 0.03,  # Sports
        "S10": 0.02,
        "S08": 0.00,
        "S09": 0.00,
        "S13": 0.00,
        "S14": 0.00,
        "S01": 0.00,
    }
    dest_stops = list(dest_weights.keys())
    d_weights = [dest_weights[s] for s in dest_stops]

    for i in range(total_arrivals):
        orig = rng.choice(stops, p=weights)
        dest = rng.choice(dest_stops, p=d_weights)
        while dest == orig:
            dest = rng.choice(dest_stops, p=d_weights)

        # Arrival time: morning peak wave centered around 08:00 - 08:45
        t_arr = float(rng.uniform(window_start_min, window_end_min))
        # Surge between 470 and 520 (07:50 - 08:40)
        if rng.random() < 0.45:
            t_arr = float(rng.uniform(470, 520))

        route_id, direction, needs_transfer, conn_route, conn_dir = topology.plan_itinerary(orig, dest)

        pax = Passenger(
            pax_id=f"PAX_{i+1:05d}",
            origin=orig,
            destination=topology.hub_id if needs_transfer else dest,
            arrival_time_min=round(t_arr, 2),
            route_id=route_id,
            direction=direction,
            needs_transfer=needs_transfer,
            connecting_route_id=conn_route,
            connecting_direction=conn_dir,
            final_destination=dest if needs_transfer else None,
        )
        passengers.append(pax)

    passengers.sort(key=lambda p: p.arrival_time_min)
    return passengers


def generate_passengers_from_demand_obs(
    demand_obs: list[DemandObs],
    topology: NetworkTopology,
    seed: int = 20261014,
) -> list[Passenger]:
    """Converts a list of DemandObs (15-min aggregate slots) into individual Passenger arrivals."""
    rng = np.random.default_rng(seed)
    passengers: list[Passenger] = []
    pax_counter = 0

    for obs in demand_obs:
        slot_start = obs.slot_start
        slot_end = slot_start + 15
        destinations = obs.od_destination or {topology.hub_id: obs.arrivals}

        total_dest_pax = sum(destinations.values())
        if total_dest_pax == 0:
            continue

        for dest, count in destinations.items():
            if dest == obs.stop_id:
                continue
            for _ in range(count):
                pax_counter += 1
                t_arr = float(rng.uniform(slot_start, slot_end))
                r_id, direction, needs_transfer, conn_r, conn_dir = topology.plan_itinerary(obs.stop_id, dest)

                pax = Passenger(
                    pax_id=f"PAX_{pax_counter:05d}",
                    origin=obs.stop_id,
                    destination=topology.hub_id if needs_transfer else dest,
                    arrival_time_min=round(t_arr, 2),
                    route_id=r_id,
                    direction=direction,
                    needs_transfer=needs_transfer,
                    connecting_route_id=conn_r,
                    connecting_direction=conn_dir,
                    final_destination=dest if needs_transfer else None,
                )
                passengers.append(pax)

    passengers.sort(key=lambda p: p.arrival_time_min)
    return passengers


# ---------------------------------------------------------------------------
# Main Discrete-Event Simulator Engine
# ---------------------------------------------------------------------------

class Simulator:
    """
    RoutePulse discrete-event simulator using heapq.
    Simulates vehicle movements, passenger queueing, FIFO boarding,
    dwell calculation, transfers at hub S03, balking, and missed connections.
    """

    def __init__(
        self,
        network: Optional[NetworkResponse] = None,
        travel_time_model: Optional[TravelTimeModel] = None,
        patience_min: float = 20.0,
        min_transfer_min: float = 4.0,
        dwell_base_s: float = 5.0,
        dwell_min_s: float = 6.0,
        dwell_per_board_s: float = 1.4,
        dwell_per_alight_s: float = 0.8,
        min_layover_min: float = 4.0,
    ):
        self.network = network or load_default_network()
        self.topology = NetworkTopology(self.network)
        self.travel_time_model = travel_time_model or TravelTimeModel(network=self.network, deterministic=True)
        self.patience_min = patience_min
        self.min_transfer_min = min_transfer_min
        self.dwell_base_s = dwell_base_s
        self.dwell_min_s = dwell_min_s
        self.dwell_per_board_s = dwell_per_board_s
        self.dwell_per_alight_s = dwell_per_alight_s
        self.min_layover_min = min_layover_min

    def run(
        self,
        plan: Plan,
        demand: Union[list[Passenger], list[DemandObs], None] = None,
        disruptions: Optional[list[Disruption]] = None,
        seed: int = 20261014,
    ) -> SimulationResult:
        """
        Runs the simulation for the given Plan and demand realization.
        """
        # Set disruptions if provided
        if disruptions:
            self.travel_time_model.disruptions = disruptions

        # Prepare passengers
        if demand is None:
            # Default morning peak demand realization
            passengers = generate_peak_demand(self.topology, seed=seed)
        elif len(demand) > 0 and isinstance(demand[0], DemandObs):
            passengers = generate_passengers_from_demand_obs(demand, self.topology, seed=seed)  # type: ignore
        else:
            passengers = demand  # type: ignore

        # Map vehicles and routes
        vehicle_map: dict[str, Vehicle] = {v.vehicle_id: v for v in self.network.vehicles}

        # Check vehicle unavailability disruptions
        unavailable_vehicles: set[str] = set()
        if disruptions:
            for d in disruptions:
                if d.type == "vehicle_out":
                    vid = d.params.get("vehicle_id")
                    if vid:
                        unavailable_vehicles.add(vid)

        # Initialize event queue (min-heap)
        event_queue: list[SimEvent] = []
        event_counter = 0

        def push_event(t: float, priority: int, event_type: str, payload: Any):
            nonlocal event_counter
            event_counter += 1
            heapq.heappush(event_queue, SimEvent(t, priority, event_counter, event_type, payload))

        # 1. Schedule all passenger arrivals and their balk timeouts
        # Queue structure: (stop_id, route_id, direction) -> deque[Passenger]
        stop_queues: dict[Tuple[str, str, int], deque[Passenger]] = defaultdict(deque)

        for p in passengers:
            push_event(p.arrival_time_min, 1, "PASSENGER_ARRIVAL", p)
            push_event(p.arrival_time_min + self.patience_min, 4, "PASSENGER_BALK", p)

        # 2. Schedule trips
        # Trip metrics tracking
        trip_metrics: dict[str, TripMetrics] = {}
        trips_sorted = sorted(plan.trips, key=lambda t: t.departure_min)

        # Onboard passengers: trip_id -> list[Passenger]
        onboard: dict[str, list[Passenger]] = defaultdict(list)

        for trip in trips_sorted:
            v_id = trip.vehicle_id
            veh = vehicle_map.get(v_id)
            cap = veh.capacity if veh else 45
            seated = veh.seated if veh else 30
            acc = veh.accessible if veh else False

            trip_metrics[trip.trip_id] = TripMetrics(
                trip_id=trip.trip_id,
                route_id=trip.route_id,
                vehicle_id=trip.vehicle_id,
                direction=trip.direction,
                departure_min=trip.departure_min,
                capacity=cap,
                seated=seated,
                accessible=acc,
            )

            # If vehicle is out of service, skip scheduling its departure
            if v_id in unavailable_vehicles:
                continue

            # Stop sequence for this trip
            stop_seq = self.topology.get_trip_stop_sequence(trip.route_id, trip.direction)
            if not stop_seq:
                continue

            # Schedule initial arrival at origin stop
            # Scheduled departure is trip.departure_min; arrival at first stop happens at departure_min
            push_event(float(trip.departure_min), 2, "VEHICLE_ARRIVAL", {
                "trip_id": trip.trip_id,
                "stop_index": 0,
                "stop_seq": stop_seq,
            })

        # Scheduled connecting trips departing hub S03 for missed connection tracking
        s03_connecting_trips: dict[str, list[Tuple[float, str]]] = defaultdict(list)
        for trip in plan.trips:
            stop_seq = self.topology.get_trip_stop_sequence(trip.route_id, trip.direction)
            if self.topology.hub_id in stop_seq:
                # Scheduled arrival/departure at S03
                s_time = float(trip.scheduled_stop_times.get(self.topology.hub_id, trip.departure_min))
                s03_connecting_trips[trip.route_id].append((s_time, trip.trip_id))
        for r_id in s03_connecting_trips:
            s03_connecting_trips[r_id].sort()

        # Operational metrics
        apc_records: list[ApcRecord] = []
        missed_connections_records: list[dict[str, Any]] = []
        balked_records: list[dict[str, Any]] = []
        total_vehicle_km = 0.0
        total_seat_km_offered = 0.0
        total_seat_km_used = 0.0

        # Run discrete event simulation loop
        while event_queue:
            ev = heapq.heappop(event_queue)
            sim_time = ev.time
            etype = ev.event_type

            if etype == "PASSENGER_ARRIVAL":
                p: Passenger = ev.payload
                # If passenger has already completed or balked, ignore
                if p.status == "waiting":
                    queue_key = (p.origin, p.route_id, p.direction)
                    stop_queues[queue_key].append(p)

            elif etype == "PASSENGER_BALK":
                p: Passenger = ev.payload
                # If passenger is still waiting in a queue after patience limit has elapsed
                if p.status == "waiting":
                    p.status = "balked"
                    p.balk_time_min = sim_time
                    queue_key = (p.origin, p.route_id, p.direction)
                    q = stop_queues[queue_key]
                    if p in q:
                        q.remove(p)
                    balked_records.append({
                        "pax_id": p.pax_id,
                        "stop_id": p.origin,
                        "time_min": sim_time,
                        "leg": p.leg,
                        "wait_min": p.total_wait_min,
                    })

            elif etype == "VEHICLE_ARRIVAL":
                payload = ev.payload
                t_id = payload["trip_id"]
                s_idx = payload["stop_index"]
                stop_seq = payload["stop_seq"]
                current_stop = stop_seq[s_idx]

                tm = trip_metrics[t_id]
                tm.stop_arrivals[current_stop] = sim_time
                if s_idx == 0:
                    tm.actual_departure = sim_time

                # 1. Alight passengers
                current_onboard = onboard[t_id]
                alighting_pax = [p for p in current_onboard if p.destination == current_stop]
                remaining_onboard = [p for p in current_onboard if p.destination != current_stop]
                onboard[t_id] = remaining_onboard

                num_alightings = len(alighting_pax)
                tm.stop_alightings[current_stop] = num_alightings

                for p in alighting_pax:
                    p.alight_time_min = sim_time
                    if p.needs_transfer and p.leg == 1 and current_stop == self.topology.hub_id:
                        # Transfer leg at S03
                        p.leg = 2
                        p.status = "waiting"
                        p.origin = self.topology.hub_id
                        p.destination = p.final_destination or "S01"
                        p.route_id = p.connecting_route_id or "R1"
                        p.direction = p.connecting_direction or 0
                        p.transfer_arrival_min = sim_time

                        # Add to S03 queue for connecting route
                        c_queue_key = (self.topology.hub_id, p.route_id, p.direction)
                        stop_queues[c_queue_key].append(p)

                        # Schedule balking for leg 2
                        push_event(sim_time + self.patience_min, 4, "PASSENGER_BALK", p)

                        # Check for missed connection
                        # Min transfer buffer is 4 min
                        conns = s03_connecting_trips.get(p.route_id, [])
                        # Find earliest scheduled connecting trip
                        earliest_planned = None
                        for s_dep, c_trip_id in conns:
                            if s_dep >= p.arrival_time_min:  # after passenger started journey
                                earliest_planned = (s_dep, c_trip_id)
                                break

                        if earliest_planned:
                            p.connecting_trip_expected = earliest_planned[1]
                            sched_dep = earliest_planned[0]
                            # If connection departs before arrival + 4 min buffer, connection is missed!
                            if sched_dep < sim_time + self.min_transfer_min:
                                p.missed_connection = True
                                missed_connections_records.append({
                                    "pax_id": p.pax_id,
                                    "feeder_trip_id": t_id,
                                    "connecting_trip_id": earliest_planned[1],
                                    "hub_arrival_min": sim_time,
                                    "connecting_scheduled_dep": sched_dep,
                                    "buffer_min": round(sched_dep - sim_time, 2),
                                })
                    else:
                        p.status = "completed"
                        p.final_alight_min = sim_time

                # 2. Board passengers up to rated capacity (FIFO)
                capacity = tm.capacity
                available_space = capacity - len(onboard[t_id])

                queue_key = (current_stop, tm.route_id, tm.direction)
                queue = stop_queues[queue_key]

                # Filter passengers eligible to board
                # Transferring passengers must have arrived at S03 at least 4 min prior
                eligible_pax: list[Passenger] = []
                ineligible_transfer_pax: list[Passenger] = []

                while queue:
                    candidate = queue.popleft()
                    if candidate.status != "waiting":
                        continue
                    if candidate.leg == 2 and candidate.transfer_arrival_min is not None:
                        if sim_time < candidate.transfer_arrival_min + self.min_transfer_min:
                            ineligible_transfer_pax.append(candidate)
                            continue
                    eligible_pax.append(candidate)

                # Board up to available space
                to_board = eligible_pax[:available_space]
                left_behind = eligible_pax[available_space:]

                num_boardings = len(to_board)
                tm.stop_boardings[current_stop] = num_boardings
                tm.passengers_boarded += num_boardings

                for p in to_board:
                    p.status = "boarded"
                    if p.leg == 1:
                        p.board_time_min = sim_time
                    else:
                        p.connecting_board_min = sim_time
                    onboard[t_id].append(p)

                # Track left-behind passengers
                if len(left_behind) > 0:
                    tm.left_behind_count += len(left_behind)
                    for p in left_behind:
                        p.left_behind_count += 1

                # Re-queue unboarded passengers (both left behind and still-transferring)
                # Maintaining arrival order
                unboarded = left_behind + ineligible_transfer_pax
                unboarded.sort(key=lambda p: (p.transfer_arrival_min or p.arrival_time_min))
                for p in unboarded:
                    queue.append(p)

                # 3. Compute dwell time: max(6, 5 + 1.4*boardings + 0.8*alightings)
                dwell_sec = max(
                    self.dwell_min_s,
                    self.dwell_base_s + self.dwell_per_board_s * num_boardings + self.dwell_per_alight_s * num_alightings
                )
                dwell_min = dwell_sec / 60.0

                dep_time = sim_time + dwell_min
                # If first stop, cannot depart before scheduled departure_min
                if s_idx == 0:
                    dep_time = max(float(tm.departure_min), dep_time)

                # Schedule departure
                push_event(dep_time, 3, "VEHICLE_DEPARTURE", {
                    "trip_id": t_id,
                    "stop_index": s_idx,
                    "stop_seq": stop_seq,
                    "boardings": num_boardings,
                    "alightings": num_alightings,
                })

            elif etype == "VEHICLE_DEPARTURE":
                payload = ev.payload
                t_id = payload["trip_id"]
                s_idx = payload["stop_index"]
                stop_seq = payload["stop_seq"]
                current_stop = stop_seq[s_idx]
                num_boardings = payload["boardings"]
                num_alightings = payload["alightings"]

                tm = trip_metrics[t_id]
                tm.stop_departures[current_stop] = sim_time
                load_after = len(onboard[t_id])
                tm.stop_loads[current_stop] = load_after
                tm.max_load = max(tm.max_load, load_after)

                # Record APC Record
                apc_records.append(ApcRecord(
                    trip_id=t_id,
                    stop_id=current_stop,
                    boardings=num_boardings,
                    alightings=num_alightings,
                    load_after=load_after,
                ))

                # Check if last stop
                if s_idx < len(stop_seq) - 1:
                    next_stop = stop_seq[s_idx + 1]
                    seg_lengths = self.topology.get_trip_segment_lengths(tm.route_id, tm.direction)
                    seg_len = seg_lengths[s_idx] if s_idx < len(seg_lengths) else 350.0

                    # Vehicle-km and seat-km accumulation
                    seg_km = seg_len / 1000.0
                    tm.distance_km += seg_km
                    total_vehicle_km += seg_km
                    offered = seg_km * tm.capacity
                    used = seg_km * load_after
                    tm.seat_km_offered += offered
                    tm.seat_km_used += used
                    total_seat_km_offered += offered
                    total_seat_km_used += used

                    # Travel time to next stop
                    tt_min = self.travel_time_model.get_segment_travel_time_min(
                        route_id=tm.route_id,
                        from_stop=current_stop,
                        to_stop=next_stop,
                        departure_time_min=sim_time,
                        length_m=seg_len,
                    )

                    push_event(sim_time + tt_min, 2, "VEHICLE_ARRIVAL", {
                        "trip_id": t_id,
                        "stop_index": s_idx + 1,
                        "stop_seq": stop_seq,
                    })
                else:
                    # Trip completed!
                    tm.actual_arrival = sim_time

        # -------------------------------------------------------------------
        # KPI calculations (Section 9.2)
        # -------------------------------------------------------------------
        all_waits: list[float] = [p.total_wait_min for p in passengers if p.status in ["boarded", "completed", "balked"]]
        mean_wait = float(np.mean(all_waits)) if all_waits else 0.0
        median_wait = float(np.median(all_waits)) if all_waits else 0.0
        p95_wait = float(np.percentile(all_waits, 95)) if all_waits else 0.0

        # Unique left-behind passengers
        left_behind_pax_count = sum(1 for p in passengers if p.left_behind_count > 0)
        balked_pax_count = sum(1 for p in passengers if p.status == "balked")
        unmet_demand_count = balked_pax_count + sum(1 for p in passengers if p.status == "waiting")

        # Missed connections
        transfer_pax = [p for p in passengers if p.needs_transfer]
        missed_conn_count = sum(1 for p in transfer_pax if p.missed_connection)
        missed_conn_rate = (missed_conn_count / len(transfer_pax)) if transfer_pax else 0.0

        # Overcrowded and capacity-violated trips
        overcrowded_trips = sum(1 for tm in trip_metrics.values() if tm.is_overcrowded)
        capacity_violated_trips = sum(1 for tm in trip_metrics.values() if tm.is_capacity_violated)

        fleet_util = (total_seat_km_used / total_seat_km_offered) if total_seat_km_offered > 0 else 0.0

        kpis = {
            "mean_wait_min": round(mean_wait, 2),
            "median_wait_min": round(median_wait, 2),
            "p95_wait_min": round(p95_wait, 2),
            "left_behind_pax": float(left_behind_pax_count),
            "balked_pax": float(balked_pax_count),
            "unmet_demand_pax": float(unmet_demand_count),
            "missed_connections": float(missed_conn_count),
            "missed_connection_rate": round(missed_conn_rate, 3),
            "overcrowded_trips": float(overcrowded_trips),
            "capacity_violated_trips": float(capacity_violated_trips),
            "vehicle_km": round(total_vehicle_km, 2),
            "seat_km_offered": round(total_seat_km_offered, 1),
            "seat_km_used": round(total_seat_km_used, 1),
            "fleet_utilization": round(fleet_util, 3),
            "violations": 0.0,
        }

        return SimulationResult(
            plan_id=plan.plan_id,
            seed=seed,
            kpis=kpis,
            trip_metrics=trip_metrics,
            apc_records=apc_records,
            passengers=passengers,
            missed_connections=missed_connections_records,
            balked_passengers=balked_records,
            vehicle_km=round(total_vehicle_km, 2),
            seat_km_offered=round(total_seat_km_offered, 1),
            seat_km_used=round(total_seat_km_used, 1),
            fleet_utilization=round(fleet_util, 3),
        )
