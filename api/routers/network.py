"""
Network Topology Router
"""
from __future__ import annotations
from fastapi import APIRouter
from core.schemas import NetworkResponse
from api.replayer import get_replayer

router = APIRouter(tags=["Network"])


@router.get("/network", response_model=NetworkResponse)
def get_network() -> NetworkResponse:
    """Return all stops, routes, vehicles, and hub transfers across the network."""
    replayer = get_replayer()
    if replayer.network:
        return replayer.network
    # Fallback directly to fixture if replayer network is unset
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "fixtures" / "network.json"
    with open(p, "r", encoding="utf-8") as f:
        return NetworkResponse(**json.load(f))
