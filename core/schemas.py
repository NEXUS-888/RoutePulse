"""
RoutePulse Core Schemas (Pydantic v2)
Single source of truth for all entities, data contracts, and API payloads.
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Section 6: Domain Data Model
# ---------------------------------------------------------------------------

class Stop(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stop_id: str = Field(..., description="Unique stop identifier, e.g. S01")
    name: str = Field(..., description="Human-readable stop name")
    x: float = Field(..., description="Local metric X coordinate in meters")
    y: float = Field(..., description="Local metric Y coordinate in meters")
    lat: float = Field(..., description="WGS84 latitude")
    lon: float = Field(..., description="WGS84 longitude")
    is_hub: bool = Field(default=False, description="Whether this stop is a central transfer hub")
    accessible: bool = Field(default=True, description="Wheelchair accessibility of the stop")
    capacity_waiting: Optional[int] = Field(default=None, description="Waiting area capacity")


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route_id: str = Field(..., description="Unique route identifier, e.g. R1")
    name: str = Field(..., description="Route name, e.g. Main Loop")
    type: Literal["loop", "linear"] = Field(..., description="Route topology")
    stop_sequence: list[str] = Field(..., description="Ordered list of stop IDs")
    polyline: list[list[float]] = Field(..., description="Piecewise coordinates [[x,y], ...]")
    segment_lengths_m: list[float] = Field(..., description="Length of each segment between consecutive stops")
    free_flow_speed_mps: float = Field(..., gt=0, description="Base free-flow vehicle speed in m/s")


class Vehicle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str = Field(..., description="Unique vehicle ID, e.g. B1, M1")
    type: Literal["bus", "minibus"] = Field(..., description="Vehicle class")
    capacity: int = Field(..., gt=0, description="Rated total capacity (seated + standing)")
    seated: int = Field(..., gt=0, description="Number of seated places")
    accessible: bool = Field(default=False, description="Equipped with wheelchair ramp / accessible")
    depot_stop: str = Field(default="S01", description="Depot stop ID")
    available_from: int = Field(default=390, description="Minutes from midnight available (06:30 = 390)")
    available_to: int = Field(default=1320, description="Minutes from midnight available (22:00 = 1320)")


class Trip(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trip_id: str = Field(..., description="Unique trip ID")
    route_id: str = Field(..., description="Route ID served by trip")
    direction: int = Field(default=0, description="Direction (0=forward/loop, 1=return)")
    vehicle_id: str = Field(..., description="Assigned vehicle ID")
    departure_min: int = Field(..., description="Trip departure time in minutes from midnight")
    scheduled_stop_times: dict[str, int] = Field(..., description="Mapping of stop_id -> scheduled arrival minute")

    @field_validator("route_id")
    @classmethod
    def validate_route_id(cls, v: str) -> str:
        valid_routes = {"R1", "R2", "R3", "R4"}
        if v not in valid_routes:
            raise ValueError(f"Invalid route_id '{v}'. Allowed routes are: {sorted(valid_routes)}")
        return v


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(..., description="Unique plan ID, e.g. baseline or opt-s0")
    name: str = Field(..., description="Descriptive name")
    window: list[str] = Field(..., description="Operating window, e.g. ['07:30', '10:30']")
    trips: list[Trip] = Field(default_factory=list, description="All scheduled trips")
    vehicle_blocks: dict[str, list[str]] = Field(
        default_factory=dict, description="Mapping of vehicle_id -> list of trip_ids in chronological order"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional properties, solver runtime, seed, etc.")


class GpsPing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str
    t_sec: int = Field(..., description="Timestamp in seconds from midnight")
    lat: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    speed_mps: float = Field(..., ge=0.0, description="Speed in m/s")
    heading: float = Field(default=0.0, ge=0.0, le=360.0, description="Vehicle heading in degrees")


class ApcRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trip_id: str
    stop_id: str
    boardings: int
    alightings: int
    load_after: int


class DemandObs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stop_id: str
    slot_start: int = Field(..., description="Minutes from midnight for the 15-min slot")
    arrivals: int
    od_destination: dict[str, int] = Field(default_factory=dict, description="Destination stop_id -> passenger count")


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    venue_stop_id: str
    start_min: int
    end_min: int
    attendance: int
    outflow_profile: list[float] = Field(default_factory=list, description="Minute-by-minute surge probability")


class Transfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_route: str
    to_route: str
    hub_stop_id: str = "S03"
    min_transfer_min: int = 4


class ServiceRules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_headway: int = 3
    max_headway_peak: int = 12
    max_headway_offpeak: int = 20
    min_layover: int = 4
    max_departure_shift: int = 5
    max_continuous_drive_min: int = 210
    min_break_min: int = 20
    min_transfer_min: int = 4
    accessible_min_per_route_hour: int = 1


class Disruption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["traffic", "vehicle_out", "demand_spike"]
    params: dict[str, Any] = Field(default_factory=dict)
    start_min: int
    end_min: int


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(..., description="Scenario ID: S0, S1, S2, S3")
    day: int = Field(..., description="Day index in evaluation split [26..30]")
    window: list[str] = Field(..., description="Active window ['07:30','10:30']")
    disruptions: list[Disruption] = Field(default_factory=list)
    seed: int
    description: str


class Violation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., description="Constraint code, e.g. H1..H12 or A1..A8")
    severity: Literal["hard", "soft"]
    entity: str = Field(..., description="Identifier of offending trip/vehicle/stop")
    time: Optional[int] = Field(default=None, description="Time in minutes from midnight")
    detail: str = Field(..., description="Detailed explanation of the violation")


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., description="Unique recommendation identifier, e.g. rec-0001")
    type: Literal[
        "ADD_TRIP",
        "RETIME_TRIP",
        "SWAP_VEHICLE",
        "REALLOCATE_VEHICLE",
        "SHORT_TURN",
        "HOLD_FOR_CONNECTION"
    ]
    summary: str
    reason_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    impact: dict[str, Any] = Field(default_factory=dict)
    tradeoff: str
    binding_constraints: list[str] = Field(default_factory=list)
    alternatives_rejected: list[dict[str, Any]] = Field(default_factory=list)
    validated: bool = True
    violations: list[Violation] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "high"


# ---------------------------------------------------------------------------
# Section 10: API Contracts & Payloads
# ---------------------------------------------------------------------------

class NetworkResponse(BaseModel):
    stops: list[Stop]
    routes: list[Route]
    vehicles: list[Vehicle]
    transfers: list[Transfer]


class EtaPrediction(BaseModel):
    stop_id: str
    route_id: str
    vehicle_id: str
    trip_id: str
    scheduled_time_min: int
    eta_p10_min: float
    eta_p50_min: float
    eta_p90_min: float
    confidence: Literal["high", "medium", "low"]
    reasons: list[str] = Field(default_factory=list)
    stale_gps: bool = False


class EtaResponse(BaseModel):
    stop_id: str
    query_time_min: int
    arrivals: list[EtaPrediction]


class VehicleEtaResponse(BaseModel):
    vehicle_id: str
    trip_id: Optional[str] = None
    current_progress_m: float
    speed_mps: float
    downstream_stops: list[EtaPrediction]


class DemandSlot(BaseModel):
    slot_start_min: int
    slot_end_min: int
    p50_arrivals: float
    p80_arrivals: float
    p90_arrivals: float
    actual_arrivals: Optional[float] = None


class DemandResponse(BaseModel):
    stop_id: str
    date: str
    slots: list[DemandSlot]


class Alert(BaseModel):
    alert_id: str
    code: Literal["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]
    severity: Literal["hard-risk", "soft"]
    title: str
    detail: str
    entity_type: Literal["route", "vehicle", "trip", "stop"]
    entity_id: str
    time_min: int
    pax_affected: int


class PlanValidationResponse(BaseModel):
    is_valid: bool
    hard_violations_count: int
    soft_violations_count: int
    violations: list[Violation]


class RecommendationRequest(BaseModel):
    scenario_id: str
    plan_id: str
    current_time_min: int


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]


class ApplyRecommendationRequest(BaseModel):
    working_plan_id: Optional[str] = None


class ApplyRecommendationResponse(BaseModel):
    applied_recommendation_id: str
    new_plan_id: str
    new_plan: Plan
    kpi_deltas: dict[str, float]
    validated: bool
    violations: list[Violation]


class WhatIfRequest(BaseModel):
    base_plan_id: str
    scenario_id: str
    added_trips: list[Trip] = Field(default_factory=list)
    retimed_trips: dict[str, int] = Field(default_factory=dict, description="trip_id -> departure_shift_min")
    vehicle_swaps: dict[str, str] = Field(default_factory=dict, description="trip_id -> new_vehicle_id")


class WhatIfResponse(BaseModel):
    validated: bool
    violations: list[Violation]
    simulated_kpis: dict[str, float]
    delta_vs_base: dict[str, float]


class ScenarioRunRequest(BaseModel):
    plan_id: Optional[str] = None
    seed: Optional[int] = None


class ScenarioRunResponse(BaseModel):
    scenario_id: str
    plan_id: str
    seed: int
    kpis: dict[str, float]


class EvalResultsResponse(BaseModel):
    summary_table: list[dict[str, Any]]
    scenarios: dict[str, Any]
    chart_paths: list[str]
    timestamp: str
    headline: dict[str, Any] | None = None  # derived from measured results (eval.report.compute_headline)


class IngestGpsRequest(BaseModel):
    pings: list[GpsPing]


class IngestApcRequest(BaseModel):
    records: list[ApcRecord]


class IngestResponse(BaseModel):
    status: str
    count: int


class StudentRouteOption(BaseModel):
    itinerary_id: str
    route_id: str
    from_stop: str
    to_stop: str
    departure_min: int
    eta_p10_min: float
    eta_p50_min: float
    eta_p90_min: float
    is_transfer: bool
    transfer_stop: Optional[str] = None
    transfer_safe_prob: float = 1.0
    accessible: bool = True
    crowding_level: Literal["low", "moderate", "crowded"] = "low"
    recommendation_note: Optional[str] = None


class StudentRouteResponse(BaseModel):
    from_stop: str
    to_stop: str
    query_time_min: int
    options: list[StudentRouteOption]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    data_hash: Optional[str] = None
    model_hash: Optional[str] = None
    master_seed: int = 20261014
    uptime_s: float = 0.0
