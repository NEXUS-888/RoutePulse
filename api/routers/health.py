"""
Health & System Status Router
"""
from __future__ import annotations
import time
from fastapi import APIRouter
from core.schemas import HealthResponse
from core.config import get_master_seed

router = APIRouter(tags=["System"])
_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return system health status, versions, model hash, and master seed."""
    uptime = round(time.time() - _START_TIME, 1)
    seed = get_master_seed()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        data_hash=f"data-seed-{seed}-v1",
        model_hash="models-v1",
        master_seed=seed,
        uptime_s=uptime
    )
