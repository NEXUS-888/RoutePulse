"""
Network topology and infrastructure definition for RoutePulse.
Defines stops, routes, vehicles, and transfers as specified in Section 7.1 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
import math
from pathlib import Path
from core.schemas import Stop, Route, Vehicle, Transfer, NetworkResponse
from core.geometry import xy_to_latlon, euclidean_dist
from core.io import save_json

# 14 Campus Stops (S01 - S14)
# (stop_id, name, x_m, y_m, is_hub, accessible, capacity_waiting)
STOPS_SPEC = [
    ("S01", "Main Gate", 0.0, 0.0, False, True, 40),
    ("S02", "Admin Block", 350.0, 150.0, False, True, 40),
    ("S03", "Central Hub", 600.0, 400.0, True, True, 100),
    ("S04", "Library", 850.0, 450.0, False, True, 40),
    ("S05", "Engineering", 1100.0, 600.0, False, True, 40),
    ("S06", "Science", 1000.0, 900.0, False, True, 40),
    ("S07", "Auditorium", 550.0, 850.0, False, True, 40),
    ("S08", "Hostel A", 400.0, 1200.0, False, True, 40),
    ("S09", "Hostel B", 650.0, 1300.0, False, True, 40),
    ("S10", "Food Court", 500.0, 700.0, False, True, 40),
    ("S11", "Sports Complex", 1400.0, 300.0, False, True, 40),
    ("S12", "Research Park", 1200.0, 200.0, False, True, 40),
    ("S13", "Metro Station", -1500.0, -600.0, False, True, 40),
    ("S14", "Medical Centre", 800.0, 250.0, False, True, 40),
]


def build_stops() -> list[Stop]:
    stops: list[Stop] = []
    for sid, name, x, y, is_hub, accessible, cap_wait in STOPS_SPEC:
        lat, lon = xy_to_latlon(x, y)
        stops.append(Stop(
            stop_id=sid,
            name=name,
            x=x,
            y=y,
            lat=lat,
            lon=lon,
            is_hub=is_hub,
            accessible=accessible,
            capacity_waiting=cap_wait,
        ))
    return stops


def build_routes(stops: list[Stop]) -> list[Route]:
    stop_map = {s.stop_id: s for s in stops}

    def _make_route(rid: str, name: str, rtype: str, seq: list[str], speed: float = 8.0) -> Route:
        polyline = [[stop_map[sid].x, stop_map[sid].y] for sid in seq]
        segment_lengths: list[float] = []
        for i in range(len(polyline) - 1):
            d = euclidean_dist(polyline[i], polyline[i + 1])
            segment_lengths.append(round(d, 1))
        return Route(
            route_id=rid,
            name=name,
            type=rtype,  # type: ignore[arg-type]
            stop_sequence=seq,
            polyline=polyline,
            segment_lengths_m=segment_lengths,
            free_flow_speed_mps=speed,
        )

    return [
        _make_route("R1", "Main Loop", "loop", ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S01"]),
        _make_route("R2", "Hostel Express", "loop", ["S03", "S10", "S08", "S09", "S03"]),
        _make_route("R3", "Metro Connector", "linear", ["S13", "S01", "S02", "S03"]),
        _make_route("R4", "Research/Sports Shuttle", "linear", ["S03", "S14", "S12", "S11"]),
    ]


def build_vehicles() -> list[Vehicle]:
    vehicles: list[Vehicle] = []
    # B1-B6 buses (capacity 45, B1 and B2 accessible)
    for i in range(1, 7):
        vid = f"B{i}"
        vehicles.append(Vehicle(
            vehicle_id=vid,
            type="bus",
            capacity=45,
            seated=30,
            accessible=(vid in ("B1", "B2")),
            depot_stop="S01",
            available_from=390,
            available_to=1320,
        ))
    # M1-M4 minibuses (capacity 22, M1 accessible)
    for j in range(1, 5):
        vid = f"M{j}"
        vehicles.append(Vehicle(
            vehicle_id=vid,
            type="minibus",
            capacity=22,
            seated=16,
            accessible=(vid == "M1"),
            depot_stop="S01",
            available_from=390,
            available_to=1320,
        ))
    return vehicles


def build_transfers() -> list[Transfer]:
    # Hub transfers at S03 between intersecting routes
    routes = ["R1", "R2", "R3", "R4"]
    transfers: list[Transfer] = []
    for r1 in routes:
        for r2 in routes:
            if r1 != r2:
                transfers.append(Transfer(
                    from_route=r1,
                    to_route=r2,
                    hub_stop_id="S03",
                    min_transfer_min=4,
                ))
    return transfers


def get_network() -> NetworkResponse:
    stops = build_stops()
    routes = build_routes(stops)
    vehicles = build_vehicles()
    transfers = build_transfers()
    return NetworkResponse(
        stops=stops,
        routes=routes,
        vehicles=vehicles,
        transfers=transfers,
    )


def save_network_fixture(output_path: Path | str = "data/network.json") -> None:
    net = get_network()
    save_json(net.model_dump(), output_path)
