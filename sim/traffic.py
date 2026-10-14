"""
Travel-Time and Traffic Ground Truth Model for RoutePulse.
Implements Section 7.3 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
import math
from typing import Optional
import numpy as np


class TrafficModel:
    """
    Ground truth travel-time and dwell-time simulator.
    """

    def __init__(self, seed: int = 20261014):
        self.rng = np.random.default_rng(seed)

    def is_metro_gate_corridor(self, from_stop: str, to_stop: str) -> bool:
        corridor_stops = {"S13", "S01", "S02", "S03"}
        return (from_stop in corridor_stops and to_stop in corridor_stops) or (
            (from_stop == "S07" and to_stop == "S01") or (from_stop == "S01" and to_stop == "S02")
        )

    def get_congestion_multiplier(
        self,
        t_min: float,
        from_stop: str,
        to_stop: str,
        day: int = 1,
        is_s1_disruption: bool = False
    ) -> float:
        """
        Calculates congestion factor based on time of day, corridor, weekday, and disruptions.
        """
        is_metro_gate = self.is_metro_gate_corridor(from_stop, to_stop)

        # Base multiplier
        mult = 1.0

        # Morning bump: 07:45 - 09:15 (min 465 to 555)
        if 465 <= t_min <= 555:
            # Smooth peak centered at 08:30 (min 510)
            peak_fraction = 1.0 - abs(t_min - 510) / 45.0
            peak_fraction = max(0.0, peak_fraction)
            if is_metro_gate:
                mult += (0.25 + 0.15 * peak_fraction)
            else:
                mult += (0.05 + 0.10 * peak_fraction)

        # Evening bump: 16:45 - 18:30 (min 1005 to 1110)
        elif 1005 <= t_min <= 1110:
            peak_fraction = 1.0 - abs(t_min - 1057.5) / 52.5
            peak_fraction = max(0.0, peak_fraction)
            mult += (0.20 + 0.15 * peak_fraction)

        # Weekday variation (Day 1..30; Friday is day % 7 == 5)
        if day % 7 == 5:
            mult *= 0.95

        # Disruption S1: Day 27, 08:00 - 09:30 (min 480 to 570)
        # travel-time x1.35 on Metro corridor + Main Gate
        if is_s1_disruption and is_metro_gate and 480 <= t_min <= 570:
            mult *= 1.35

        return mult

    def sample_segment_traversal_time_s(
        self,
        length_m: float,
        free_flow_speed_mps: float,
        t_min: float,
        from_stop: str,
        to_stop: str,
        day: int = 1,
        day_noise: float = 1.0,
        is_s1_disruption: bool = False,
    ) -> float:
        """
        Samples realistic segment traversal time in seconds:
        T = (length / free_flow_speed) * congestion(t) * LogNormal(0, 0.12) + intersection_delays
        """
        base_time_s = length_m / max(free_flow_speed_mps, 1.0)
        cong = self.get_congestion_multiplier(t_min, from_stop, to_stop, day, is_s1_disruption)

        # LogNormal noise (mu=0, sigma=0.12)
        ln_noise = float(self.rng.lognormal(mean=0.0, sigma=0.12))

        # Intersection delay event: Poisson process (approx 0.35 chance per segment), delay 2-25 s
        intersection_delay_s = 0.0
        if self.rng.random() < 0.35:
            intersection_delay_s = float(self.rng.uniform(2.0, 25.0))

        traversal_time_s = (base_time_s * cong * ln_noise * day_noise) + intersection_delay_s
        return max(5.0, traversal_time_s)

    @staticmethod
    def calculate_dwell_time_s(boardings: int, alightings: int) -> float:
        """
        Coupled dwell time model:
        dwell = max(6.0, 5.0 + 1.4 * boardings + 0.8 * alightings)
        """
        return max(6.0, 5.0 + 1.4 * boardings + 0.8 * alightings)
