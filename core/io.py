"""
IO utilities: Parquet reading/writing, JSON serialisation, DuckDB query helper.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd
import duckdb


def save_json(data: Any, path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path | str) -> Any:
    p = Path(path)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_parquet(df: pd.DataFrame, path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False, engine="pyarrow")


def load_parquet(path: Path | str) -> pd.DataFrame:
    p = Path(path)
    return pd.read_parquet(p, engine="pyarrow")


def get_duckdb_connection(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    return duckdb.connect(db_path)
