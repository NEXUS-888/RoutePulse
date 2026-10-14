import type {
  NetworkResponse,
  Plan,
  PlanValidationResponse,
  EtaResponse,
  VehicleEtaResponse,
  DemandResponse,
  Alert,
  Recommendation,
  ApplyRecommendationResponse,
  WhatIfRequest,
  WhatIfResponse,
  ScenarioRunResponse,
  EvalResultsResponse,
  StudentRouteResponse,
  HealthResponse,
  ScenarioId
} from '../types';

import rawNetwork from '../fixtures/network.json';
import rawPlan from '../fixtures/baseline_plan.json';
import rawEtaStop from '../fixtures/eta_stop.json';
import rawEtaVehicle from '../fixtures/eta_vehicle.json';
import rawStudentRoute from '../fixtures/student_route.json';
import rawValidation from '../fixtures/plan_validation.json';
import rawHealth from '../fixtures/health.json';

import {
  ALL_ALERTS,
  ALL_RECOMMENDATIONS,
  MOCK_EVAL_RESULTS,
  generateStopDemandHeatmap
} from '../fixtures/richData';

const API_BASE = '/api';
const TIMEOUT_MS = 1500;

export interface ApiResponse<T> {
  data: T;
  isLive: boolean;
  error?: string;
}

// In-memory working state for offline interactivity
let currentWorkingPlan: Plan = JSON.parse(JSON.stringify(rawPlan));
const appliedRecommendationIds = new Set<string>();
const allDemandData = generateStopDemandHeatmap(rawNetwork.stops);

async function fetchWithFallback<T>(endpoint: string, fallbackData: T): Promise<ApiResponse<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    clearTimeout(timer);

    if (res.ok) {
      const data = await res.json();
      return { data, isLive: true };
    }
  } catch (_err) {
    // Silent fallback to offline fixture
  } finally {
    clearTimeout(timer);
  }

  return { data: fallbackData, isLive: false };
}

export const api = {
  async getHealth(): Promise<ApiResponse<HealthResponse>> {
    return fetchWithFallback<HealthResponse>('/health', rawHealth as HealthResponse);
  },

  async getNetwork(): Promise<ApiResponse<NetworkResponse>> {
    return fetchWithFallback<NetworkResponse>('/network', rawNetwork as NetworkResponse);
  },

  async getPlan(planId: string = 'baseline'): Promise<ApiResponse<Plan>> {
    return fetchWithFallback<Plan>(`/plans/${planId}`, currentWorkingPlan);
  },

  async validatePlan(plan: Plan): Promise<ApiResponse<PlanValidationResponse>> {
    // If the plan has 0 hard violations
    const fallback: PlanValidationResponse = {
      is_valid: true,
      hard_violations_count: 0,
      soft_violations_count: 0,
      violations: []
    };

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const res = await fetch(`${API_BASE}/plans/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(plan),
        signal: controller.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        return { data: await res.json(), isLive: true };
      }
    } catch (_e) {
      // offline fallback
    }

    return { data: fallback, isLive: false };
  },

  async getStopEta(stopId: string, tMin: number = 455): Promise<ApiResponse<EtaResponse>> {
    const fallback: EtaResponse = {
      stop_id: stopId,
      query_time_min: tMin,
      arrivals: (rawEtaStop.arrivals as any[]).map(arr => ({
        ...arr,
        stop_id: stopId,
        scheduled_time_min: tMin + 3,
        eta_p10_min: tMin + 2.5,
        eta_p50_min: tMin + 4.0,
        eta_p90_min: tMin + 6.2,
      }))
    };

    return fetchWithFallback<EtaResponse>(`/eta?stop_id=${stopId}&t=${tMin}`, fallback);
  },

  async getVehicleEta(vehicleId: string): Promise<ApiResponse<VehicleEtaResponse>> {
    const fallback: VehicleEtaResponse = {
      ...(rawEtaVehicle as any),
      vehicle_id: vehicleId
    };
    return fetchWithFallback<VehicleEtaResponse>(`/eta/vehicle/${vehicleId}`, fallback);
  },

  async getDemand(stopId: string, _date: string = '2026-10-14'): Promise<ApiResponse<DemandResponse>> {
    const fallback = allDemandData[stopId] || {
      stop_id: stopId,
      date: "2026-10-14",
      slots: []
    };
    return fetchWithFallback<DemandResponse>(`/demand?stop_id=${stopId}`, fallback);
  },

  getAllDemandData(): Record<string, DemandResponse> {
    return allDemandData;
  },

  async getAlerts(scenarioId?: ScenarioId): Promise<ApiResponse<Alert[]>> {
    // If S1 (Traffic delay), add/emphasize delay alerts
    let alerts = [...ALL_ALERTS];
    if (scenarioId === 'S1') {
      alerts = alerts.filter(a => ['A2', 'A4', 'A6'].includes(a.code));
    } else if (scenarioId === 'S2') {
      alerts = alerts.filter(a => ['A8', 'A5', 'A3'].includes(a.code));
    } else if (scenarioId === 'S3') {
      alerts = alerts.filter(a => ['A1', 'A2', 'A3'].includes(a.code));
    }

    // Sort by severity (hard-risk first) and pax_affected descending
    alerts.sort((a, b) => {
      if (a.severity === 'hard-risk' && b.severity !== 'hard-risk') return -1;
      if (a.severity !== 'hard-risk' && b.severity === 'hard-risk') return 1;
      return b.pax_affected - a.pax_affected;
    });

    return fetchWithFallback<Alert[]>(`/alerts${scenarioId ? `?scenario_id=${scenarioId}` : ''}`, alerts);
  },

  async getRecommendations(): Promise<ApiResponse<Recommendation[]>> {
    return fetchWithFallback<Recommendation[]>('/recommendations', ALL_RECOMMENDATIONS);
  },

  async applyRecommendation(recId: string): Promise<ApiResponse<ApplyRecommendationResponse>> {
    appliedRecommendationIds.add(recId);
    const rec = ALL_RECOMMENDATIONS.find(r => r.id === recId);

    const fallback: ApplyRecommendationResponse = {
      applied_recommendation_id: recId,
      new_plan_id: `plan_opt_${recId}`,
      new_plan: {
        ...currentWorkingPlan,
        plan_id: `plan_opt_${recId}`,
        name: `Optimized Plan (${rec?.type || 'Update'})`
      },
      kpi_deltas: {
        avg_wait_min: rec?.impact.avg_wait_min || -1.5,
        left_behind: rec?.impact.left_behind || -35,
        missed_connections: rec?.impact.missed_connections || -14,
        vehicle_km: rec?.impact.vehicle_km || 12.0
      },
      validated: true,
      violations: []
    };

    currentWorkingPlan = fallback.new_plan;

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const res = await fetch(`${API_BASE}/recommendations/${recId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ working_plan_id: currentWorkingPlan.plan_id }),
        signal: controller.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        return { data: await res.json(), isLive: true };
      }
    } catch (_e) {
      // offline fallback
    }

    return { data: fallback, isLive: false };
  },

  async runWhatIf(req: WhatIfRequest): Promise<ApiResponse<WhatIfResponse>> {
    const fallback: WhatIfResponse = {
      validated: true,
      violations: [],
      simulated_kpis: {
        avg_wait_min: 5.2,
        left_behind_pax: 10.0,
        missed_connections: 2.0,
        vehicle_km: 115.0
      },
      delta_vs_base: {
        avg_wait_min: -1.7,
        left_behind_pax: -37.0,
        missed_connections: -13.0,
        vehicle_km: 14.2
      }
    };

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const res = await fetch(`${API_BASE}/whatif`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        return { data: await res.json(), isLive: true };
      }
    } catch (_e) {
      // offline fallback
    }

    return { data: fallback, isLive: false };
  },

  async runScenario(scenarioId: ScenarioId, seed: number = 20261014): Promise<ApiResponse<ScenarioRunResponse>> {
    const kpiMap: Record<ScenarioId, { wait: number; left: number; conn: number; util: number }> = {
      S0: { wait: 4.7, left: 6, conn: 2, util: 0.88 },
      S1: { wait: 5.6, left: 14, conn: 5, util: 0.92 },
      S2: { wait: 5.9, left: 18, conn: 6, util: 0.94 },
      S3: { wait: 5.8, left: 22, conn: 5, util: 0.95 },
    };

    const target = kpiMap[scenarioId];
    const fallback: ScenarioRunResponse = {
      scenario_id: scenarioId,
      plan_id: currentWorkingPlan.plan_id,
      seed,
      kpis: {
        mean_wait_min: target.wait,
        left_behind_pax: target.left,
        missed_connections: target.conn,
        fleet_utilization: target.util,
        violations: 0
      }
    };

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed, plan_id: currentWorkingPlan.plan_id }),
        signal: controller.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        return { data: await res.json(), isLive: true };
      }
    } catch (_e) {
      // offline fallback
    }

    return { data: fallback, isLive: false };
  },

  async getEvalResults(): Promise<ApiResponse<EvalResultsResponse>> {
    return fetchWithFallback<EvalResultsResponse>('/eval/results', MOCK_EVAL_RESULTS);
  },

  async getStudentRoute(
    fromStop: string,
    toStop: string,
    queryTimeMin: number = 460,
    accessibleOnly: boolean = false
  ): Promise<ApiResponse<StudentRouteResponse>> {
    const fallback: StudentRouteResponse = {
      from_stop: fromStop,
      to_stop: toStop,
      query_time_min: queryTimeMin,
      options: [
        {
          itinerary_id: "ITIN-01",
          route_id: "R3",
          from_stop: fromStop,
          to_stop: toStop,
          departure_min: queryTimeMin + 3,
          eta_p10_min: queryTimeMin + 14.0,
          eta_p50_min: queryTimeMin + 17.0,
          eta_p90_min: queryTimeMin + 20.0,
          is_transfer: true,
          transfer_stop: "S03",
          transfer_safe_prob: 0.94,
          accessible: true,
          crowding_level: "crowded",
          recommendation_note: "Next R3 departure is crowded (88% full). Conformal transfer probability at Hub S03 is 94%."
        },
        {
          itinerary_id: "ITIN-02",
          route_id: "R3",
          from_stop: fromStop,
          to_stop: toStop,
          departure_min: queryTimeMin + 11,
          eta_p10_min: queryTimeMin + 22.0,
          eta_p50_min: queryTimeMin + 25.0,
          eta_p90_min: queryTimeMin + 28.0,
          is_transfer: true,
          transfer_stop: "S03",
          transfer_safe_prob: 0.99,
          accessible: true,
          crowding_level: "low",
          recommendation_note: "Recommended: 8 min later R3 is predicted only 55% full with 99% transfer safety!"
        }
      ]
    };

    if (accessibleOnly) {
      fallback.options = fallback.options.filter(o => o.accessible);
    }

    return fetchWithFallback<StudentRouteResponse>(
      `/student/route?from=${fromStop}&to=${toStop}&t=${queryTimeMin}&accessible=${accessibleOnly}`,
      fallback
    );
  },

  getAppliedRecommendationIds(): Set<string> {
    return appliedRecommendationIds;
  },

  resetPlan(): void {
    currentWorkingPlan = JSON.parse(JSON.stringify(rawPlan));
    appliedRecommendationIds.clear();
  }
};
