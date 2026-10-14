"""
Configuration Loader
"""
from pathlib import Path
from typing import Any
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_master_seed(config_path: Path | str = DEFAULT_CONFIG_PATH) -> int:
    cfg = load_config(config_path)
    return int(cfg.get("master_seed", 20261014))
