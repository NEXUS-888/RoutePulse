"""
Synthetic World Generator for RoutePulse.
Implements Section 7 of docs/ARCHITECTURE.md:
  - Master seed: 20261014
  - 14 stops (S01-S14) with metric and WGS84 coordinates centered at (12.9716, 77.5946)
  - 4 routes (R1, R2, R3, R4)
  - 10 vehicles (B1-B6 buses, M1-M4 minibuses)
  - Baseline timetable in config/baseline_plan.json
  - 30 simulated service days (06:30 to 22:00)
  - Splits: train (days 1-20), validation (days 21-25), test (days 26-30)
  - Travel-time and demand ground truth with disruptions S0-S3
  - Generates network.json, events.csv, baseline_plan.json, scenarios.json,
    demand_obs.parquet, apc_records.parquet, gps_pings.parquet, data_hash.txt
"""
from __future__ import annotations
import argparse
import hashlib
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Any
import pandas as pd

from core.config import get_master_seed

from core.io import save_parquet, save_json
from sim.topology import get_network, save_network_fixture
from sim.baseline import generate_baseline_plan, save_baseline_plan
from sim.events import save_events_csv
from sim.scenarios import save_scenarios_json
from sim.demand_gen import DemandGenerator
from sim.gps import TraceGenerator


def compute_file_hash(path: Path | str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_dataset_hash(data_dir: Path | str = "data") -> tuple[str, dict[str, str]]:
    """
    Computes SHA-256 for all generated data artifacts and returns (combined_hash, per_file_hashes).
    """
    dpath = Path(data_dir)
    target_files = [
        "network.json",
        "baseline_plan.json",
        "events.csv",
        "scenarios.json",
        "demand_obs.parquet",
        "apc_records.parquet",
        "gps_pings.parquet",
    ]

    per_file: dict[str, str] = {}
    master_hasher = hashlib.sha256()

    for fname in target_files:
        fpath = dpath / fname
        if fpath.exists():
            h = compute_file_hash(fpath)
            per_file[fname] = h
            master_hasher.update(f"{fname}:{h}".encode("utf-8"))

    combined_hash = master_hasher.hexdigest()
    return combined_hash, per_file


def get_split(day: int) -> str:
    if 1 <= day <= 20:
        return "train"
    elif 21 <= day <= 25:
        return "validation"
    elif 26 <= day <= 30:
        return "test"
    else:
        return "unknown"


def generate_world(
    num_days: int = 30,
    seed: int = 20261014,
    data_dir: Path | str = "data",
    config_dir: Path | str = "config",
    verbose: bool = True
) -> dict[str, Any]:
    """
    Generates complete synthetic dataset for RoutePulse.
    """
    dpath = Path(data_dir)
    cpath = Path(config_dir)
    dpath.mkdir(parents=True, exist_ok=True)
    cpath.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"=== RoutePulse Synthetic World Generator ===")
        print(f"Master Seed: {seed} | Days: {num_days} | Target Dir: {dpath}")

    # 1. Network Topology
    if verbose:
        print("\n[1/6] Generating network topology...")
    net = get_network()
    net_path = dpath / "network.json"
    save_network_fixture(net_path)
    # Also keep api/fixtures/network.json synchronized
    save_network_fixture(Path("api/fixtures/network.json"))

    # 2. Baseline Plan
    if verbose:
        print("[2/6] Generating baseline timetable...")
    plan_path = cpath / "baseline_plan.json"
    save_baseline_plan(
        output_path=plan_path,
        fixtures_path=Path("api/fixtures/baseline_plan.json")
    )
    # Copy to data/baseline_plan.json as well
    save_baseline_plan(
        output_path=dpath / "baseline_plan.json",
        fixtures_path=Path("api/fixtures/baseline_plan.json")
    )
    baseline_plan = generate_baseline_plan()

    # 3. Events Schedule
    if verbose:
        print("[3/6] Generating events schedule...")
    events_path = dpath / "events.csv"
    save_events_csv(events_path)

    # 4. Scenarios
    if verbose:
        print("[4/6] Generating evaluation scenarios (S0-S3)...")
    scenarios_path = dpath / "scenarios.json"
    save_scenarios_json(scenarios_path)

    # 5. Multi-day Demand and Vehicle Traces
    if verbose:
        print(f"[5/6] Simulating {num_days} service days (Demand, Traffic, APC, GPS)...")

    all_demand_dfs: list[pd.DataFrame] = []
    all_apc_dfs: list[pd.DataFrame] = []
    all_gps_dfs: list[pd.DataFrame] = []

    total_r3_peak_trips = 0
    total_r3_peak_overloaded = 0

    for day in range(1, num_days + 1):
        day_seed = seed + (day * 1000)
        split = get_split(day)

        # Check for day-specific disruption flags
        is_s1 = (day == 27)  # Traffic delay
        is_s2 = (day == 28)  # Vehicle B2 unavailable

        # Demand generation for this day
        demand_gen = DemandGenerator(seed=day_seed)
        df_demand_day, minute_arrivals = demand_gen.generate_day_demand(day=day)
        df_demand_day["split"] = split
        all_demand_dfs.append(df_demand_day)

        # Trace and APC generation
        trace_gen = TraceGenerator(seed=day_seed + 1)
        df_apc_day, df_gps_day, day_stats = trace_gen.simulate_day(
            day=day,
            plan=baseline_plan,
            routes=net.routes,
            stops=net.stops,
            vehicles=net.vehicles,
            minute_arrivals=minute_arrivals,
            is_s1=is_s1,
            is_s2=is_s2,
        )
        df_apc_day["day"] = day
        df_apc_day["split"] = split
        df_gps_day["day"] = day
        df_gps_day["split"] = split

        all_apc_dfs.append(df_apc_day)
        all_gps_dfs.append(df_gps_day)

        total_r3_peak_trips += day_stats["r3_peak_trips"]
        total_r3_peak_overloaded += day_stats["r3_peak_overloaded"]

        if verbose and (day % 5 == 0 or day == num_days):
            print(f"  -> Completed Day {day:02d}/{num_days:02d} ({split:10s}): "
                  f"Boardings={day_stats['total_boardings']}, GPS Pings={len(df_gps_day):,}")

    # Combine and save Parquet datasets
    df_demand = pd.concat(all_demand_dfs, ignore_index=True)
    df_apc = pd.concat(all_apc_dfs, ignore_index=True)
    df_gps = pd.concat(all_gps_dfs, ignore_index=True)

    save_parquet(df_demand, dpath / "demand_obs.parquet")
    save_parquet(df_apc, dpath / "apc_records.parquet")
    save_parquet(df_gps, dpath / "gps_pings.parquet")

    # 6. Compute Data Hashes
    if verbose:
        print("[6/6] Computing SHA-256 data hash...")
    combined_hash, per_file_hashes = compute_dataset_hash(dpath)

    hash_file_content = [
        f"# RoutePulse Frozen Dataset SHA-256 Hashes",
        f"# Master Seed: {seed}",
        f"# Total Days: {num_days}",
        f"combined_data_hash: {combined_hash}",
        "",
        "# Per-file SHA-256 digests:",
    ]
    for fn, h in per_file_hashes.items():
        hash_file_content.append(f"{fn}: {h}")

    hash_path = dpath / "data_hash.txt"
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write("\n".join(hash_file_content) + "\n")

    r3_overload_pct = (total_r3_peak_overloaded / max(1, total_r3_peak_trips)) * 100.0

    if verbose:
        print(f"\nGeneration Complete!")
        print(f"  Combined Data Hash: {combined_hash}")
        print(f"  Hash written to:    {hash_path}")
        print(f"  R3 Peak Overload:   {total_r3_peak_overloaded}/{total_r3_peak_trips} ({r3_overload_pct:.1f}%)")
        print(f"  Total GPS Pings:    {len(df_gps):,}")
        print(f"  Total APC Records:  {len(df_apc):,}")
        print(f"  Total Demand Slots: {len(df_demand):,}")

    return {
        "combined_hash": combined_hash,
        "per_file_hashes": per_file_hashes,
        "total_gps_pings": len(df_gps),
        "total_apc_records": len(df_apc),
        "total_demand_slots": len(df_demand),
        "r3_overload_pct": r3_overload_pct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RoutePulse Synthetic World Data")
    parser.add_argument("--days", type=int, default=30, help="Number of days to simulate (default 30)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (defaults to master seed)")
    parser.add_argument("--data-dir", type=str, default="data", help="Output data directory")
    args = parser.parse_args()

    master_seed = args.seed if args.seed is not None else get_master_seed()
    generate_world(num_days=args.days, seed=master_seed, data_dir=args.data_dir)


if __name__ == "__main__":
    main()
