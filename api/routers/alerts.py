"""
Alerts Router
Provides typed alerts A1-A8 with severity scores and passenger impact.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

from core.schemas import Alert
from api.replayer import get_replayer

router = APIRouter(tags=["Alerts"])
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@router.get("/alerts", response_model=list[Alert])
def get_alerts(
    plan_id: Optional[str] = Query(default=None, description="Filter by plan ID"),
    scenario_id: Optional[str] = Query(default=None, description="Filter by scenario ID (S0, S1, S2, S3)"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (hard-risk or soft)")
) -> list[Alert]:
    """Return active typed alerts A1-A8 (overcrowding, tight connections, delays, fleet risks)."""
    replayer = get_replayer()
    if scenario_id:
        replayer.scenario_id = scenario_id

    alerts = replayer._detect_alerts()

    # If dynamic alerts are empty, fallback to frozen alerts fixture
    if not alerts:
        p = FIXTURES_DIR / "alerts.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            alerts = [Alert(**item) for item in data]

    # Apply filters
    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    return alerts
