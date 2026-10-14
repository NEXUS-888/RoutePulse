"""
Scenario definitions for RoutePulse evaluation.
Implements Section 7.8 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations
from pathlib import Path
from core.schemas import Scenario, Disruption
from core.io import save_json


def get_scenarios(replications: int = 20) -> list[Scenario]:
    """
    Builds the scenarios S0, S1, S2, S3 across 20 stochastic replications.
    """
    scenarios: list[Scenario] = []

    # S0: Normal operation (Days 26-30)
    for rep in range(1, replications + 1):
        scenarios.append(Scenario(
            scenario_id="S0",
            day=26,
            window=["07:30", "10:30"],
            disruptions=[],
            seed=rep,
            description="Normal daily campus operation without external shocks.",
        ))

    # S1: Traffic delay (Day 27)
    for rep in range(1, replications + 1):
        scenarios.append(Scenario(
            scenario_id="S1",
            day=27,
            window=["07:30", "10:30"],
            disruptions=[
                Disruption(
                    type="traffic",
                    params={
                        "multiplier": 1.35,
                        "corridors": ["Metro", "Main Gate"],
                        "stops": ["S13", "S01", "S02", "S03"],
                    },
                    start_min=480,  # 08:00
                    end_min=570,    # 09:30
                )
            ],
            seed=rep,
            description="1.35x travel-time congestion on Metro corridor and Main Gate, 08:00-09:30.",
        ))

    # S2: Vehicle breakdown (Day 28)
    for rep in range(1, replications + 1):
        scenarios.append(Scenario(
            scenario_id="S2",
            day=28,
            window=["07:30", "10:30"],
            disruptions=[
                Disruption(
                    type="vehicle_out",
                    params={
                        "vehicle_id": "B2",
                        "reserve_available": True,
                    },
                    start_min=495,  # 08:15
                    end_min=630,    # 10:30 (end of W1)
                )
            ],
            seed=rep,
            description="Bus B2 mechanical failure from 08:15 to end of morning peak W1.",
        ))

    # S3: Demand spike (Day 29)
    for rep in range(1, replications + 1):
        scenarios.append(Scenario(
            scenario_id="S3",
            day=29,
            window=["16:30", "19:30"],
            disruptions=[
                Disruption(
                    type="demand_spike",
                    params={
                        "stop_id": "S07",
                        "surge_passengers": 1000,
                        "multiplier": 3.0,
                    },
                    start_min=1050,  # 17:30
                    end_min=1075,   # 17:55 (25-min surge)
                )
            ],
            seed=rep,
            description="Mega cultural auditorium event at S07 ends at 17:30, +1,000 passenger surge.",
        ))

    return scenarios


def save_scenarios_json(output_path: Path | str = "data/scenarios.json") -> None:
    scens = get_scenarios()
    save_json([s.model_dump() for s in scens], output_path)
