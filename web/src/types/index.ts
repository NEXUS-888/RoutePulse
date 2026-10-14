// Domain Models & API Types for RoutePulse

export interface Stop {
  stop_id: string;
  name: string;
  x: number;
  y: number;
  lat: number;
  lon: number;
  is_hub: boolean;
  accessible: boolean;
  capacity_waiting?: number;
}

export interface Route {
  route_id: string;
  name: string;
  type: 'loop' | 'linear';
  stop_sequence: string[];
  polyline: [number, number][];
  segment_lengths_m: number[];
  free_flow_speed_mps: number;
}

export interface Vehicle {
  vehicle_id: string;
  type: 'bus' | 'minibus';
  capacity: number;
  seated: number;
  accessible: boolean;
  depot_stop: string;
  available_from: number;
  available_to: number;
}

export interface Transfer {
  from_route: string;
  to_route: string;
  hub_stop_id: string;
  min_transfer_min: number;
}

export interface NetworkResponse {
  stops: Stop[];
  routes: Route[];
  vehicles: Vehicle[];
  transfers: Transfer[];
}

export interface Trip {
  trip_id: string;
  route_id: string;
  direction: number;
  vehicle_id: string;
  departure_min: number;
  scheduled_stop_times: Record<string, number>;
}

export interface Plan {
  plan_id: string;
  name: string;
  window: [string, string];
  trips: Trip[];
  vehicle_blocks?: Record<string, string[]>;
  metadata?: Record<string, unknown>;
}

export interface Violation {
  code: string;
  severity: 'hard' | 'soft';
  entity: string;
  time?: number;
  detail: string;
}

export interface PlanValidationResponse {
  is_valid: boolean;
  hard_violations_count: number;
  soft_violations_count: number;
  violations: Violation[];
}

export interface EtaPrediction {
  stop_id: string;
  route_id: string;
  vehicle_id: string;
  trip_id: string;
  scheduled_time_min: number;
  eta_p10_min: number;
  eta_p50_min: number;
  eta_p90_min: number;
  confidence: 'high' | 'medium' | 'low';
  reasons: string[];
  stale_gps?: boolean;
}

export interface EtaResponse {
  stop_id: string;
  query_time_min: number;
  arrivals: EtaPrediction[];
}

export interface VehicleEtaResponse {
  vehicle_id: string;
  trip_id?: string;
  current_progress_m: number;
  speed_mps: number;
  downstream_stops: EtaPrediction[];
}

export interface DemandSlot {
  slot_start_min: number;
  slot_end_min: number;
  p50_arrivals: number;
  p80_arrivals: number;
  p90_arrivals: number;
  actual_arrivals?: number;
}

export interface DemandResponse {
  stop_id: string;
  date: string;
  slots: DemandSlot[];
}

export interface Alert {
  alert_id: string;
  code: 'A1' | 'A2' | 'A3' | 'A4' | 'A5' | 'A6' | 'A7' | 'A8';
  severity: 'hard-risk' | 'soft';
  title: string;
  detail: string;
  entity_type: 'route' | 'vehicle' | 'trip' | 'stop';
  entity_id: string;
  time_min: number;
  pax_affected: number;
}

export type RecommendationType =
  | 'ADD_TRIP'
  | 'RETIME_TRIP'
  | 'SWAP_VEHICLE'
  | 'REALLOCATE_VEHICLE'
  | 'SHORT_TURN'
  | 'HOLD_FOR_CONNECTION';

export interface AlternativeRejected {
  option: string;
  why: string;
}

export interface Recommendation {
  id: string;
  type: RecommendationType;
  summary: string;
  reason_codes: string[];
  evidence: {
    p80_load_before?: number;
    p80_load_after?: number;
    pax_affected?: number;
    [key: string]: unknown;
  };
  impact: {
    avg_wait_min?: number;
    left_behind?: number;
    missed_connections?: number;
    vehicle_km?: number;
    [key: string]: unknown;
  };
  tradeoff: string;
  binding_constraints: string[];
  alternatives_rejected: AlternativeRejected[];
  validated: boolean;
  violations: Violation[];
  confidence: 'high' | 'medium' | 'low';
}

export interface ApplyRecommendationResponse {
  applied_recommendation_id: string;
  new_plan_id: string;
  new_plan: Plan;
  kpi_deltas: Record<string, number>;
  validated: boolean;
  violations: Violation[];
}

export interface WhatIfRequest {
  base_plan_id: string;
  scenario_id: string;
  added_trips?: Trip[];
  retimed_trips?: Record<string, number>;
  vehicle_swaps?: Record<string, string>;
}

export interface WhatIfResponse {
  validated: boolean;
  violations: Violation[];
  simulated_kpis: {
    avg_wait_min: number;
    left_behind_pax: number;
    missed_connections: number;
    vehicle_km: number;
  };
  delta_vs_base: {
    avg_wait_min: number;
    left_behind_pax: number;
    missed_connections: number;
    vehicle_km: number;
  };
}

export interface ScenarioRunResponse {
  scenario_id: string;
  plan_id: string;
  seed: number;
  kpis: {
    mean_wait_min: number;
    left_behind_pax: number;
    missed_connections: number;
    fleet_utilization: number;
    violations: number;
  };
}

export interface EvalSummaryItem {
  system: string;
  scenario: string;
  wait_min: string;
  left_behind: string;
  missed_conn: string;
  hard_violations: number;
}

export interface EvalResultsResponse {
  summary_table: EvalSummaryItem[];
  scenarios: Record<string, unknown>;
  chart_paths: string[];
  timestamp: string;
}

export interface StudentRouteOption {
  itinerary_id: string;
  route_id: string;
  from_stop: string;
  to_stop: string;
  departure_min: number;
  eta_p10_min: number;
  eta_p50_min: number;
  eta_p90_min: number;
  is_transfer: boolean;
  transfer_stop?: string;
  transfer_safe_prob: number;
  accessible: boolean;
  crowding_level: 'low' | 'moderate' | 'crowded';
  recommendation_note?: string;
}

export interface StudentRouteResponse {
  from_stop: string;
  to_stop: string;
  query_time_min: number;
  options: StudentRouteOption[];
}

export interface LiveVehiclePing {
  vehicle_id: string;
  lat: number;
  lon: number;
  speed_mps: number;
  load: number;
  route_id?: string;
  trip_id?: string;
  capacity?: number;
  progress_pct?: number;
  x?: number;
  y?: number;
}

export interface LiveStreamTick {
  t_sec: number;
  time_str: string;
  active_vehicles: number;
  pings: LiveVehiclePing[];
  alerts_count: number;
}

export type ScenarioId = 'S0' | 'S1' | 'S2' | 'S3';

export interface HealthResponse {
  status: string;
  version: string;
  data_hash?: string;
  model_hash?: string;
  master_seed: number;
  uptime_s: number;
}

export interface NetworkHealthInfo {
  score: number;
  band: 'teal' | 'amber' | 'coral';
  overCapacityShare: number;
  leftBehindShare: number;
  missedConnectionShare: number;
  delayedTripsShare: number;
}

export type SelectedEntityType = 'stop' | 'vehicle' | 'alert' | 'recommendation';

export interface SelectedEntity {
  type: SelectedEntityType;
  id: string;
  data: any;
}

export type UserRole = 'operator' | 'student' | 'reviewer';

