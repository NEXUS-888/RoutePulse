"""
Demand Ground Truth Generator for RoutePulse.
Implements Section 7.4 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
import json
import math
from typing import Any
import numpy as np
import pandas as pd
from core.schemas import DemandObs


STOPS_ALL = [f"S{i:02d}" for i in range(1, 15)]

# Base relative arrival weights across stops
BASE_STOP_WEIGHTS: dict[str, float] = {
    "S01": 1.2,   # Main Gate
    "S02": 0.6,   # Admin
    "S03": 1.5,   # Central Hub
    "S04": 0.8,   # Library
    "S05": 1.0,   # Engineering
    "S06": 0.9,   # Science
    "S07": 0.7,   # Auditorium
    "S08": 1.1,   # Hostel A
    "S09": 1.1,   # Hostel B
    "S10": 1.0,   # Food Court
    "S11": 0.5,   # Sports Complex
    "S12": 0.6,   # Research Park
    "S13": 1.8,   # Metro Station
    "S14": 0.4,   # Medical Centre
}


class DemandGenerator:
    """
    Generates minute-level passenger arrivals and OD flows across 30 days.
    """

    def __init__(self, seed: int = 20261014):
        self.rng = np.random.default_rng(seed)

    def get_time_multiplier(self, stop_id: str, t_min: int, is_class_change: bool) -> float:
        """
        Calculates time-of-day arrival rate multiplier for a given stop.
        """
        mult = 1.0

        # Class change surges at :50 to :05
        minute_of_hour = t_min % 60
        if (48 <= minute_of_hour <= 59 or 0 <= minute_of_hour <= 4) and 480 <= t_min <= 1080:
            mult *= 1.45

        # Morning arrival wave: 07:45 - 09:30 (465 to 570 min)
        # Strongly elevated at S13 (Metro) and S01 (Main Gate)
        if 465 <= t_min <= 570:
            peak_fraction = 1.0 - abs(t_min - 510) / 55.0
            peak_fraction = max(0.0, peak_fraction)
            if stop_id == "S13":
                mult *= (2.7 + 1.35 * peak_fraction)
            elif stop_id == "S01":
                mult *= (2.0 + 0.9 * peak_fraction)
            elif stop_id in ("S08", "S09"):  # Hostels outbound to classes
                mult *= (1.7 + 0.6 * peak_fraction)
            else:
                mult *= 0.7



        # Lunch peak at Food Court (S10): 12:00 - 13:45 (720 to 825 min)
        elif 720 <= t_min <= 825:
            peak_fraction = 1.0 - abs(t_min - 765) / 50.0
            peak_fraction = max(0.0, peak_fraction)
            if stop_id == "S10":
                mult *= (2.5 + 1.2 * peak_fraction)
            elif stop_id in ("S04", "S05", "S06", "S02"):
                mult *= (1.3 + 0.4 * peak_fraction)

        # Evening dinner peak at Food Court (S10): 19:00 - 20:30 (1140 to 1230 min)
        elif 1140 <= t_min <= 1230:
            if stop_id == "S10":
                mult *= 2.0

        # Evening outbound wave: 16:30 - 18:30 (990 to 1110 min)
        # Elevated from campus (S04, S05, S06, S12) towards S01 and S13
        elif 990 <= t_min <= 1110:
            peak_fraction = 1.0 - abs(t_min - 1050) / 60.0
            peak_fraction = max(0.0, peak_fraction)
            if stop_id in ("S04", "S05", "S06", "S12", "S07"):
                mult *= (1.8 + 0.8 * peak_fraction)
            elif stop_id in ("S01", "S13"):
                mult *= 0.6

        return mult

    def get_event_multiplier(self, stop_id: str, t_min: int, day: int) -> float:
        """
        Event multipliers, including Day 29 auditorium valedictory surge.
        """
        # Day 29: Mega Cultural Fest valedictory at S07 ends at 17:30 (1050 min)
        # Surge 17:30 - 17:55 (1050 to 1075 min)
        if day == 29 and stop_id == "S07" and 1050 <= t_min <= 1075:
            return 8.5  # Surge of ~1000 passengers over 25 min

        # Day 12: Career fair at S07 ends ~15:00 (900 min)
        if day == 12 and stop_id == "S07" and 885 <= t_min <= 920:
            return 3.0

        # Day 18: Sports fest at S11
        if day == 18 and stop_id == "S11" and 1050 <= t_min <= 1100:
            return 3.5

        return 1.0

    def sample_od_destination(self, origin_stop: str, t_min: int) -> str:
        """
        Samples passenger destination based on origin and time of day.
        Ensures realistic directional patterns and transfer flows.
        """
        candidates = [s for s in STOPS_ALL if s != origin_stop]
        probs = np.ones(len(candidates), dtype=float)

        for idx, dest in enumerate(candidates):
            # Morning inbound: S13 / S01 -> academic blocks (S04, S05, S06) and Hub (S03)
            if 465 <= t_min <= 570:
                if origin_stop in ("S13", "S01"):
                    if dest in ("S03", "S04", "S05", "S06"):
                        probs[idx] *= 3.0
                    elif dest in ("S08", "S09"):
                        probs[idx] *= 1.5

            # Lunch time: all -> S10
            elif 720 <= t_min <= 825:
                if dest == "S10":
                    probs[idx] *= 4.0

            # Evening outbound: all -> S01, S13
            elif 990 <= t_min <= 1110:
                if dest in ("S01", "S13"):
                    probs[idx] *= 4.0
                elif dest in ("S08", "S09"):
                    probs[idx] *= 2.0

            # Hub S03 is a frequent destination for transfers
            if dest == "S03":
                probs[idx] *= 1.8

        probs /= probs.sum()
        return str(self.rng.choice(candidates, p=probs))

    def generate_day_demand(self, day: int) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """
        Generates demand for one 06:30-22:00 day (minutes 390 to 1320).
        Returns:
          - DataFrame of DemandObs (aggregated by 15-min slots)
          - Raw minute-by-minute passenger arrival records for simulator
        """
        day_noise = float(self.rng.lognormal(0.0, 0.05))
        weekday_mult = 0.95 if day % 7 == 5 else 1.0  # Friday slightly lighter

        # Normalization factor calibrated to yield ~6,000 boardings/day
        target_daily = 6000.0
        # Average base rate per stop-min
        base_rate = (target_daily / (930.0 * sum(BASE_STOP_WEIGHTS.values()))) * 0.92

        minute_arrivals: list[dict[str, Any]] = []

        # 15-minute slot buckets: (stop_id, slot_start) -> {arrivals: int, od: dict}
        slot_map: dict[tuple[str, int], dict[str, Any]] = {}
        for s in STOPS_ALL:
            for slot_start in range(390, 1320, 15):
                slot_map[(s, slot_start)] = {"arrivals": 0, "od": {}}

        for t_min in range(390, 1320):
            slot_start = (t_min // 15) * 15
            for stop_id, w in BASE_STOP_WEIGHTS.items():
                t_mult = self.get_time_multiplier(stop_id, t_min, is_class_change=True)
                evt_mult = self.get_event_multiplier(stop_id, t_min, day)
                lam = base_rate * w * t_mult * evt_mult * weekday_mult * day_noise

                pax_count = int(self.rng.poisson(lam))
                if pax_count > 0:
                    slot_entry = slot_map[(stop_id, slot_start)]
                    slot_entry["arrivals"] += pax_count
                    for _ in range(pax_count):
                        dest = self.sample_od_destination(stop_id, t_min)
                        slot_entry["od"][dest] = slot_entry["od"].get(dest, 0) + 1
                        minute_arrivals.append({
                            "day": day,
                            "arrival_min": t_min,
                            "origin_stop": stop_id,
                            "destination_stop": dest,
                        })

        obs_rows: list[dict[str, Any]] = []
        for (stop_id, slot_start), data in slot_map.items():
            obs_rows.append({
                "day": day,
                "stop_id": stop_id,
                "slot_start": slot_start,
                "arrivals": data["arrivals"],
                "od_destination": json.dumps(data["od"]),
            })

        df_obs = pd.DataFrame(obs_rows)
        return df_obs, minute_arrivals
