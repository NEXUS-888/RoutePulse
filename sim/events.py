"""
Events schedule generator for RoutePulse.
Defines and exports recurring campus events according to Section 7.6 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from core.schemas import Event


EVENTS_DATA = [
    {
        "event_id": "EVT_01",
        "day": 5,
        "name": "Research Symposium",
        "venue_stop_id": "S07",
        "start_min": 840,   # 14:00
        "end_min": 960,     # 16:00
        "attendance": 400,
        "outflow_profile": [0.05, 0.15, 0.35, 0.25, 0.15, 0.05],
    },
    {
        "event_id": "EVT_02",
        "day": 12,
        "name": "Industry Keynote & Career Fair",
        "venue_stop_id": "S07",
        "start_min": 600,   # 10:00
        "end_min": 900,     # 15:00
        "attendance": 750,
        "outflow_profile": [0.10, 0.20, 0.30, 0.25, 0.10, 0.05],
    },
    {
        "event_id": "EVT_03",
        "day": 18,
        "name": "Annual Sports Fest",
        "venue_stop_id": "S11",
        "start_min": 540,   # 09:00
        "end_min": 1080,    # 18:00
        "attendance": 600,
        "outflow_profile": [0.05, 0.10, 0.20, 0.30, 0.20, 0.15],
    },
    {
        "event_id": "EVT_04",
        "day": 22,
        "name": "Campus Cultural Showcase",
        "venue_stop_id": "S07",
        "start_min": 930,   # 15:30
        "end_min": 1050,    # 17:30
        "attendance": 650,
        "outflow_profile": [0.10, 0.25, 0.35, 0.20, 0.10],
    },
    {
        "event_id": "EVT_05",
        "day": 29,
        "name": "Mega Cultural Fest Valedictory",
        "venue_stop_id": "S07",
        "start_min": 900,   # 15:00
        "end_min": 1050,    # 17:30
        "attendance": 1000,
        # Major surge 17:30-17:55 (+1000 passengers)
        "outflow_profile": [0.05, 0.10, 0.20, 0.25, 0.20, 0.12, 0.08],
    },
]


def get_events() -> list[Event]:
    return [
        Event(
            event_id=e["event_id"],
            venue_stop_id=e["venue_stop_id"],
            start_min=e["start_min"],
            end_min=e["end_min"],
            attendance=e["attendance"],
            outflow_profile=e["outflow_profile"],
        )
        for e in EVENTS_DATA
    ]


def save_events_csv(output_path: Path | str = "data/events.csv") -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "day", "name", "venue_stop_id", "start_min", "end_min", "attendance", "outflow_profile"])
        for e in EVENTS_DATA:
            writer.writerow([
                e["event_id"],
                e["day"],
                e["name"],
                e["venue_stop_id"],
                e["start_min"],
                e["end_min"],
                e["attendance"],
                json.dumps(e["outflow_profile"]),
            ])
