"""
GPS and APC Synthetic Trace Generator for RoutePulse.
Implements Sections 7.3, 7.4, 7.5 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from core.schemas import GpsPing, ApcRecord, Plan, Route, Stop, Vehicle
from core.geometry import xy_to_latlon, euclidean_dist
from sim.traffic import TrafficModel


class TraceGenerator:
    """
    Simulates actual vehicle journeys, passenger loads (APC), and realistic GPS pings.
    """

    def __init__(self, seed: int = 20261014):
        self.rng = np.random.default_rng(seed)
        self.traffic = TrafficModel(seed=seed)

    def simulate_day(
        self,
        day: int,
        plan: Plan,
        routes: list[Route],
        stops: list[Stop],
        vehicles: list[Vehicle],
        minute_arrivals: list[dict[str, Any]],
        is_s1: bool = False,
        is_s2: bool = False,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
        """
        Simulates all trips for one day.
        Returns:
          - df_apc: DataFrame of ApcRecord
          - df_gps: DataFrame of GpsPing
          - stats: Simulation summary stats (overloaded trips count, total boardings, etc.)
        """
        stop_map = {s.stop_id: s for s in stops}
        route_map = {r.route_id: r for r in routes}
        vehicle_map = {v.vehicle_id: v for v in vehicles}

        # Day-level traffic noise
        day_traffic_noise = float(self.rng.lognormal(0.0, 0.04))

        # Build passenger queues at stops: stop_id -> list of arrival records
        # Queue item: {"arrival_min": int, "origin": str, "dest": str}
        stop_queues: dict[str, list[dict[str, Any]]] = {s.stop_id: [] for s in stops}
        for arr in minute_arrivals:
            stop_queues[arr["origin_stop"]].append(arr)
        # Sort each queue by arrival time
        for s in stop_queues:
            stop_queues[s].sort(key=lambda x: x["arrival_min"])

        apc_records: list[dict[str, Any]] = []
        gps_pings: list[dict[str, Any]] = []

        # Track per-vehicle last event time and position to ensure depot start
        vehicle_pings: dict[str, list[dict[str, Any]]] = {v.vehicle_id: [] for v in vehicles}

        # Outage bursts: 2 per vehicle-day, 30-90 s duration
        outage_windows: dict[str, list[tuple[int, int]]] = {}
        for v in vehicles:
            outage_windows[v.vehicle_id] = []
            for _ in range(2):
                b_start = int(self.rng.uniform(400 * 60, 1300 * 60))
                b_dur = int(self.rng.uniform(30, 90))
                outage_windows[v.vehicle_id].append((b_start, b_start + b_dur))

        # Stats tracking
        r3_peak_trips = 0
        r3_peak_overloaded = 0
        total_boardings = 0

        # Sort trips chronologically
        sorted_trips = sorted(plan.trips, key=lambda t: t.departure_min)

        for trip in sorted_trips:
            # S2 Disruption: Bus B2 out of service from 08:15 (495 min) to 10:30 (630 min) on Day 28
            if is_s2 and trip.vehicle_id == "B2" and (495 <= trip.departure_min <= 630):
                continue

            r_info = route_map[trip.route_id]
            veh_info = vehicle_map[trip.vehicle_id]
            cap = veh_info.capacity

            # Determine stop sequence for this trip direction
            if r_info.type == "linear" and trip.direction == 1:
                trip_stops = list(reversed(r_info.stop_sequence))
            else:
                trip_stops = list(r_info.stop_sequence)

            current_load = 0
            onboard_passengers: list[str] = []  # list of destination stops
            curr_time_sec = trip.departure_min * 60.0

            # Is this trip in the morning peak on R3? (07:30 to 09:30, min 450 to 570)
            is_r3_peak = (trip.route_id == "R3" and 450 <= trip.departure_min <= 570)
            if is_r3_peak:
                r3_peak_trips += 1

            trip_exceeded_cap = False

            for idx, stop_id in enumerate(trip_stops):
                stop_obj = stop_map[stop_id]
                t_curr_min = curr_time_sec / 60.0

                # 1. Alightings
                alighting_count = sum(1 for d in onboard_passengers if d == stop_id)
                # At the terminal stop, everyone remaining alights
                if idx == len(trip_stops) - 1:
                    alighting_count = len(onboard_passengers)
                    onboard_passengers.clear()
                else:
                    onboard_passengers = [d for d in onboard_passengers if d != stop_id]

                # 2. Boardings (FIFO from queue up to remaining capacity)
                space = max(0, cap - len(onboard_passengers))
                waiting_queue = stop_queues[stop_id]
                eligible: list[dict[str, Any]] = []
                remaining_queue: list[dict[str, Any]] = []

                # Remaining stops on this trip
                downstream_stops = set(trip_stops[idx + 1:])

                for pax in waiting_queue:
                    # Passenger must have arrived by now, and must not have balked (> 20 min wait)
                    if pax["arrival_min"] <= t_curr_min:
                        if (t_curr_min - pax["arrival_min"]) <= 20.0:
                            # Does this route serve pax destination or transfer hub S03?
                            if pax["destination_stop"] in downstream_stops or (
                                "S03" in downstream_stops and stop_id != "S03"
                            ):
                                eligible.append(pax)
                            else:
                                remaining_queue.append(pax)
                        else:
                            # Balked / unmet demand, drops from queue
                            pass
                    else:
                        remaining_queue.append(pax)

                # If queue exceeded capacity, mark exceeded
                if len(eligible) > space:
                    trip_exceeded_cap = True

                boarded = eligible[:space]
                unboarded = eligible[space:]
                remaining_queue.extend(unboarded)
                stop_queues[stop_id] = remaining_queue

                boarding_count = len(boarded)
                for b in boarded:
                    dest = b["destination_stop"]
                    if dest not in downstream_stops and "S03" in downstream_stops:
                        onboard_passengers.append("S03")  # Transfer at S03
                    else:
                        onboard_passengers.append(dest)

                load_after = len(onboard_passengers)
                total_boardings += boarding_count

                # Record APC record
                apc_records.append({
                    "trip_id": trip.trip_id,
                    "stop_id": stop_id,
                    "boardings": boarding_count,
                    "alightings": alighting_count,
                    "load_after": load_after,
                })

                # Calculate dwell time
                dwell_s = self.traffic.calculate_dwell_time_s(boarding_count, alighting_count)

                # Generate GPS pings during dwell at stop (every 10 seconds)
                dwell_end_sec = curr_time_sec + dwell_s
                ping_t = math.ceil(curr_time_sec / 10.0) * 10
                while ping_t <= dwell_end_sec:
                    self._add_gps_ping(
                        vehicle_pings=vehicle_pings,
                        veh_id=trip.vehicle_id,
                        t_sec=ping_t,
                        x=stop_obj.x,
                        y=stop_obj.y,
                        speed=0.0,
                        heading=0.0,
                        outages=outage_windows[trip.vehicle_id],
                    )
                    ping_t += 10

                curr_time_sec = dwell_end_sec

                # 3. Traverse to next stop if not at end
                if idx < len(trip_stops) - 1:
                    next_stop_id = trip_stops[idx + 1]
                    next_stop_obj = stop_map[next_stop_id]
                    seg_dist = euclidean_dist([stop_obj.x, stop_obj.y], [next_stop_obj.x, next_stop_obj.y])

                    # Sample travel time
                    seg_time_s = self.traffic.sample_segment_traversal_time_s(
                        length_m=seg_dist,
                        free_flow_speed_mps=r_info.free_flow_speed_mps,
                        t_min=curr_time_sec / 60.0,
                        from_stop=stop_id,
                        to_stop=next_stop_id,
                        day=day,
                        day_noise=day_traffic_noise,
                        is_s1_disruption=is_s1,
                    )

                    dx = next_stop_obj.x - stop_obj.x
                    dy = next_stop_obj.y - stop_obj.y
                    heading_deg = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
                    avg_speed = seg_dist / max(seg_time_s, 1.0)

                    seg_end_sec = curr_time_sec + seg_time_s
                    ping_t = math.ceil(curr_time_sec / 10.0) * 10

                    while ping_t <= seg_end_sec:
                        fraction = (ping_t - curr_time_sec) / seg_time_s
                        fraction = max(0.0, min(1.0, fraction))
                        px = stop_obj.x + fraction * dx
                        py = stop_obj.y + fraction * dy
                        self._add_gps_ping(
                            vehicle_pings=vehicle_pings,
                            veh_id=trip.vehicle_id,
                            t_sec=ping_t,
                            x=px,
                            y=py,
                            speed=avg_speed,
                            heading=heading_deg,
                            outages=outage_windows[trip.vehicle_id],
                        )
                        ping_t += 10

                    curr_time_sec = seg_end_sec

            if is_r3_peak and trip_exceeded_cap:
                r3_peak_overloaded += 1

        # Flatten and sort all GPS pings
        all_pings: list[dict[str, Any]] = []
        for vid in vehicle_pings:
            # Sort each vehicle strictly by t_sec
            vehicle_pings[vid].sort(key=lambda p: p["t_sec"])
            # Remove any duplicate timestamps per vehicle
            deduped = []
            last_t = -1
            for p in vehicle_pings[vid]:
                if p["t_sec"] > last_t:
                    deduped.append(p)
                    last_t = p["t_sec"]
            all_pings.extend(deduped)

        df_apc = pd.DataFrame(apc_records)
        df_gps = pd.DataFrame(all_pings)

        stats = {
            "day": day,
            "total_boardings": total_boardings,
            "r3_peak_trips": r3_peak_trips,
            "r3_peak_overloaded": r3_peak_overloaded,
            "r3_overload_ratio": (r3_peak_overloaded / max(1, r3_peak_trips)),
        }
        return df_apc, df_gps, stats

    def _add_gps_ping(
        self,
        vehicle_pings: dict[str, list[dict[str, Any]]],
        veh_id: str,
        t_sec: int,
        x: float,
        y: float,
        speed: float,
        heading: float,
        outages: list[tuple[int, int]],
    ) -> None:
        """
        Applies GPS noise model:
          - Check outage bursts (omit ping if in outage)
          - Random 3% dropout (omit ping)
          - Gaussian position noise sigma = 8m
          - 2% outliers (40-80m offset)
          - Gaussian speed noise sigma = 0.7 m/s
        """
        # 1. Outage bursts
        for start_s, end_s in outages:
            if start_s <= t_sec <= end_s:
                return

        # 2. Random 3% dropout
        if self.rng.random() < 0.03:
            return

        # 3. Position noise
        pos_noise_x = float(self.rng.normal(0.0, 8.0))
        pos_noise_y = float(self.rng.normal(0.0, 8.0))

        # 4. Outliers (2% rate, 40-80m displacement)
        if self.rng.random() < 0.02:
            outlier_angle = float(self.rng.uniform(0.0, 2 * math.pi))
            outlier_dist = float(self.rng.uniform(40.0, 80.0))
            pos_noise_x += outlier_dist * math.cos(outlier_angle)
            pos_noise_y += outlier_dist * math.sin(outlier_angle)

        noisy_x = x + pos_noise_x
        noisy_y = y + pos_noise_y

        # Convert to lat/lon
        lat, lon = xy_to_latlon(noisy_x, noisy_y)

        # 5. Speed noise sigma = 0.7 m/s
        noisy_speed = max(0.0, speed + float(self.rng.normal(0.0, 0.7)))

        vehicle_pings[veh_id].append({
            "vehicle_id": veh_id,
            "t_sec": t_sec,
            "lat": lat,
            "lon": lon,
            "speed_mps": round(noisy_speed, 2),
            "heading": round(heading, 1),
        })
