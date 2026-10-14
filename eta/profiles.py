"""
Historical Travel-Time Profiles (eta/profiles.py)
Implements Section 8.3 of docs/ARCHITECTURE.md:
- Segment travel time profiles: median and spread by (segment, 15-min bucket, day_type).
- Hierarchical empirical Bayes shrinkage to segment-level and route-level means for sparse buckets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd


def day_to_day_type(day: int) -> str:
    """
    Maps day index (1..30) to day_type category:
    - Friday: day % 7 == 5 (matches sim/traffic.py 0.95 multiplier)
    - Weekend: day % 7 in (0, 6)
    - Weekday: day % 7 in (1, 2, 3, 4)
    """
    mod = day % 7
    if mod == 5:
        return "friday"
    elif mod in (0, 6):
        return "weekend"
    else:
        return "weekday"


class HistoricalProfiles:
    """
    Computes and stores smoothed historical travel-time profiles for network segments.
    Applies shrinkage from (segment, bucket, day_type) -> segment -> route.
    """

    def __init__(
        self,
        slot_size_min: int = 15,
        shrinkage_lambda_seg: float = 5.0,
        shrinkage_lambda_route: float = 10.0,
    ):
        self.slot_size_min = slot_size_min
        self.lambda_seg = shrinkage_lambda_seg
        self.lambda_route = shrinkage_lambda_route

        # Lookup structures
        self.route_stats: dict[str, tuple[float, float]] = {}  # route_id -> (median_s, spread_s)
        self.seg_stats: dict[str, tuple[float, float]] = {}    # seg_id -> (median_s, spread_s)
        self.profiles: dict[str, tuple[float, float]] = {}     # key -> (median_s, spread_s)
        self.global_median = 120.0
        self.global_spread = 20.0

    @staticmethod
    def _make_key(segment_id: str, slot: int, day_type: str) -> str:
        return f"{segment_id}::{slot}::{day_type}"

    def fit(self, df_segments: pd.DataFrame) -> HistoricalProfiles:
        """
        Fits historical segment profiles from segment_times table.
        Asserts that data contains only Train split (Days 1-20).
        """
        if "day" in df_segments.columns:
            days = df_segments["day"].dropna().unique()
            invalid_days = [d for d in days if d not in range(1, 21)]
            assert not invalid_days, (
                f"Data leakage detected! Training profiles on days outside Train split (1-20): {invalid_days}"
            )

        df = df_segments.copy()
        if "duration_sec" not in df.columns and "duration_s" in df.columns:
            df["duration_sec"] = df["duration_s"]

        # Drop any invalid or negative durations
        df = df[df["duration_sec"] > 0].copy()
        if len(df) == 0:
            return self

        # Global fallback
        self.global_median = float(df["duration_sec"].median())
        self.global_spread = float(np.percentile(df["duration_sec"], 75) - np.percentile(df["duration_sec"], 25)) / 2.0
        self.global_spread = max(5.0, self.global_spread)

        # 1. Route-level stats
        if "route_id" in df.columns:
            for rid, grp in df.groupby("route_id"):
                med = float(grp["duration_sec"].median())
                q75, q25 = np.percentile(grp["duration_sec"], [75, 25])
                spd = max(5.0, float(q75 - q25) / 2.0)
                self.route_stats[str(rid)] = (med, spd)

        # 2. Segment-level stats (shrunk towards route stats)
        for seg_id, grp in df.groupby("segment_id"):
            n = len(grp)
            seg_med = float(grp["duration_sec"].median())
            q75, q25 = np.percentile(grp["duration_sec"], [75, 25])
            seg_spd = max(5.0, float(q75 - q25) / 2.0)

            # Determine parent route
            r_id = str(grp["route_id"].iloc[0]) if "route_id" in grp.columns else None
            r_med, r_spd = self.route_stats.get(r_id, (self.global_median, self.global_spread))

            # Shrink segment stats towards route stats
            w = n / (n + self.lambda_route)
            shrunk_med = w * seg_med + (1.0 - w) * r_med
            shrunk_spd = w * seg_spd + (1.0 - w) * r_spd
            self.seg_stats[str(seg_id)] = (round(shrunk_med, 1), round(shrunk_spd, 1))

        # 3. Bucket-level stats: (segment_id, slot, day_type)
        if "entry_time_min" not in df.columns:
            df["entry_time_min"] = df["entry_time_sec"] / 60.0
        df["slot"] = (df["entry_time_min"] // self.slot_size_min).astype(int)

        if "day_type" not in df.columns:
            if "day" in df.columns:
                df["day_type"] = df["day"].apply(day_to_day_type)
            else:
                df["day_type"] = "weekday"

        grouped = df.groupby(["segment_id", "slot", "day_type"])
        for (seg_id, slot, d_type), grp in grouped:
            n = len(grp)
            b_med = float(grp["duration_sec"].median())
            q75, q25 = np.percentile(grp["duration_sec"], [75, 25])
            b_spd = max(5.0, float(q75 - q25) / 2.0)

            # Shrink towards segment stats
            p_med, p_spd = self.seg_stats.get(str(seg_id), (self.global_median, self.global_spread))
            w = n / (n + self.lambda_seg)
            shrunk_med = w * b_med + (1.0 - w) * p_med
            shrunk_spd = w * b_spd + (1.0 - w) * p_spd

            key = self._make_key(str(seg_id), int(slot), str(d_type))
            self.profiles[key] = (round(shrunk_med, 1), round(shrunk_spd, 1))

        return self

    def get_segment_time(
        self,
        segment_id: str,
        t_min: float,
        day: int = 1,
        day_type: Optional[str] = None,
        route_id: Optional[str] = None,
    ) -> tuple[float, float]:
        """
        Returns (median_duration_sec, spread_sec) for a given segment and time.
        Falls back smoothly through shrinkage hierarchy: bucket -> segment -> route -> global.
        """
        d_type = day_type or day_to_day_type(day)
        slot = int(t_min // self.slot_size_min)
        key = self._make_key(segment_id, slot, d_type)

        if key in self.profiles:
            return self.profiles[key]

        # Try adjacent slots (+/- 1) for same day type
        for alt_slot in (slot - 1, slot + 1):
            alt_key = self._make_key(segment_id, alt_slot, d_type)
            if alt_key in self.profiles:
                return self.profiles[alt_key]

        # Fallback to segment-level stats
        if segment_id in self.seg_stats:
            return self.seg_stats[segment_id]

        # Fallback to route-level stats
        if route_id and route_id in self.route_stats:
            return self.route_stats[route_id]

        # Global fallback
        return self.global_median, self.global_spread

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_size_min": self.slot_size_min,
            "lambda_seg": self.lambda_seg,
            "lambda_route": self.lambda_route,
            "global_median": self.global_median,
            "global_spread": self.global_spread,
            "route_stats": {k: list(v) for k, v in self.route_stats.items()},
            "seg_stats": {k: list(v) for k, v in self.seg_stats.items()},
            "profiles": {k: list(v) for k, v in self.profiles.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoricalProfiles:
        obj = cls(
            slot_size_min=data.get("slot_size_min", 15),
            shrinkage_lambda_seg=data.get("lambda_seg", 5.0),
            shrinkage_lambda_route=data.get("lambda_route", 10.0),
        )
        obj.global_median = float(data.get("global_median", 120.0))
        obj.global_spread = float(data.get("global_spread", 20.0))
        obj.route_stats = {k: (v[0], v[1]) for k, v in data.get("route_stats", {}).items()}
        obj.seg_stats = {k: (v[0], v[1]) for k, v in data.get("seg_stats", {}).items()}
        obj.profiles = {k: (v[0], v[1]) for k, v in data.get("profiles", {}).items()}
        return obj

    def save(self, path: Union[Path, str]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Union[Path, str]) -> HistoricalProfiles:
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
