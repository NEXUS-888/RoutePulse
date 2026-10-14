import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import type {
  NetworkResponse,
  Plan,
  Alert,
  Recommendation,
  ScenarioId,
  Vehicle,
  Stop,
  Route
} from '../types';
import { api } from '../api/client';
import { interpolatePolyline, projectToSvg } from '../utils/geo';

export interface ActiveVehicleState {
  vehicle_id: string;
  type: 'bus' | 'minibus';
  route_id: string;
  capacity: number;
  seated: number;
  load: number;
  loadPct: number;
  speed_mps: number;
  x: number;
  y: number;
  svgX: number;
  svgY: number;
  angle: number;
  status: 'running' | 'idle' | 'breakdown' | 'delayed';
  nextStop: string;
  tripId: string;
}

interface SimulationContextValue {
  simTimeMin: number;
  setSimTimeMin: (t: number) => void;
  isPlaying: boolean;
  togglePlay: () => void;
  speed: 1 | 10 | 30;
  setSpeed: (s: 1 | 10 | 30) => void;
  scenario: ScenarioId;
  setScenario: (s: ScenarioId) => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  activeScreen: string;
  setActiveScreen: (s: string) => void;
  highlightedEntity: { type: 'trip' | 'route' | 'stop' | 'vehicle'; id: string } | null;
  setHighlightedEntity: (e: { type: 'trip' | 'route' | 'stop' | 'vehicle'; id: string } | null) => void;
  network: NetworkResponse | null;
  workingPlan: Plan | null;
  alerts: Alert[];
  recommendations: Recommendation[];
  appliedRecIds: Set<string>;
  acceptRecommendation: (id: string) => Promise<void>;
  rejectRecommendation: (id: string) => void;
  activeVehicles: ActiveVehicleState[];
  isLiveApi: boolean;
  activeDisruptionAlert: string | null;
  triggerScenario: (s: ScenarioId) => Promise<void>;
  resetToBaseline: () => void;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Morning peak: 07:30 (450 min) to 10:30 (630 min)
  const [simTimeMin, setSimTimeMin] = useState<number>(470); // Default around 07:50
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [speed, setSpeed] = useState<1 | 10 | 30>(10);
  const [scenario, setScenario] = useState<ScenarioId>('S0');
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('routepulse_theme') as 'dark' | 'light') || 'dark';
  });
  const [activeScreen, setActiveScreen] = useState<string>('map');
  const [highlightedEntity, setHighlightedEntity] = useState<{
    type: 'trip' | 'route' | 'stop' | 'vehicle';
    id: string;
  } | null>(null);

  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [workingPlan, setWorkingPlan] = useState<Plan | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [appliedRecIds, setAppliedRecIds] = useState<Set<string>>(new Set());
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [activeDisruptionAlert, setActiveDisruptionAlert] = useState<string | null>(null);

  // Load initial dataset
  useEffect(() => {
    async function loadData() {
      const netRes = await api.getNetwork();
      setNetwork(netRes.data);
      if (netRes.isLive) setIsLiveApi(true);

      const planRes = await api.getPlan();
      setWorkingPlan(planRes.data);

      const alertRes = await api.getAlerts(scenario);
      setAlerts(alertRes.data);

      const recRes = await api.getRecommendations();
      setRecommendations(recRes.data);
    }
    loadData();
  }, [scenario]);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('routepulse_theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const togglePlay = useCallback(() => {
    setIsPlaying(prev => !prev);
  }, []);

  // Clock progression
  useEffect(() => {
    if (!isPlaying) return;

    const intervalMs = 100;
    // Advance time: 1 min per 60000ms / speed. At 100ms tick:
    // advance = (intervalMs / 1000) * (speed / 60)
    const stepMin = (0.1 * speed) / 6;

    const timer = setInterval(() => {
      setSimTimeMin(prev => {
        const next = prev + stepMin;
        if (next > 630) return 450; // loop back to 07:30
        return next;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isPlaying, speed]);

  // Calculate dynamic vehicle positions along routes
  const activeVehicles = useMemo<ActiveVehicleState[]>(() => {
    if (!network) return [];

    const routesMap = new Map<string, Route>();
    network.routes.forEach(r => routesMap.set(r.route_id, r));

    const list: ActiveVehicleState[] = [];

    // Base assignments
    // B1 on R1 (cycle 14 min)
    // B2 on R2 (cycle 10 min)
    // B3 on R3 (cycle 12 min)
    // B4 on R4 (cycle 8 min)
    // M1 on R2 (cycle 10 min, offset 5 min)
    // M2 on R1 (cycle 14 min, offset 7 min)

    interface VehConfig {
      id: string;
      routeId: string;
      cycleMin: number;
      offsetMin: number;
      baseLoad: number;
      surgeFactor: number;
    }

    const configs: VehConfig[] = [
      { id: 'B1', routeId: 'R1', cycleMin: 14, offsetMin: 0, baseLoad: 32, surgeFactor: 0.8 },
      { id: 'B2', routeId: 'R2', cycleMin: 10, offsetMin: 2, baseLoad: 24, surgeFactor: 1.1 },
      { id: 'B3', routeId: 'R3', cycleMin: 12, offsetMin: 1, baseLoad: 41, surgeFactor: 1.4 },
      { id: 'B4', routeId: 'R4', cycleMin: 8, offsetMin: 0, baseLoad: 16, surgeFactor: 0.6 },
      { id: 'M1', routeId: 'R2', cycleMin: 10, offsetMin: 7, baseLoad: 17, surgeFactor: 1.0 },
      { id: 'M2', routeId: 'R1', cycleMin: 14, offsetMin: 7, baseLoad: 18, surgeFactor: 0.9 },
    ];

    // If rec-0007 (ADD_TRIP with B5) is accepted, add B5 on R3
    if (appliedRecIds.has('rec-0007')) {
      configs.push({
        id: 'B5',
        routeId: 'R3',
        cycleMin: 12,
        offsetMin: 6,
        baseLoad: 28,
        surgeFactor: 0.85
      });
    }

    // If rec-0010 is accepted, add M3 on R4
    if (appliedRecIds.has('rec-0010')) {
      configs.push({
        id: 'M3',
        routeId: 'R4',
        cycleMin: 8,
        offsetMin: 4,
        baseLoad: 14,
        surgeFactor: 0.7
      });
    }

    const vehiclesMap = new Map<string, Vehicle>();
    network.vehicles.forEach(v => vehiclesMap.set(v.vehicle_id, v));

    configs.forEach(cfg => {
      const route = routesMap.get(cfg.routeId);
      const vehicle = vehiclesMap.get(cfg.id);
      if (!route || !vehicle) return;

      let capacity = vehicle.capacity;
      // If rec-0009 swapped B4 with M3
      if (appliedRecIds.has('rec-0009') && cfg.id === 'B4') {
        capacity = 22;
      }

      // Check breakdown condition for S2
      const isBreakdown = scenario === 'S2' && cfg.id === 'B3' && simTimeMin >= 485;
      const isTrafficDelayed = scenario === 'S1' && cfg.routeId === 'R3';

      // Cycle calculation
      let cycle = cfg.cycleMin;
      if (isTrafficDelayed) cycle += 4; // slower in traffic

      const progressRaw = ((simTimeMin - cfg.offsetMin) % cycle) / cycle;
      const progress = progressRaw < 0 ? progressRaw + 1 : progressRaw;

      // Polyline interpolation
      let coords = interpolatePolyline(route.polyline, progress);
      let status: 'running' | 'idle' | 'breakdown' | 'delayed' = 'running';

      if (isBreakdown) {
        status = 'breakdown';
        // Freeze position around S02
        coords = { x: 350, y: 150, angle: 45 };
      } else if (isTrafficDelayed) {
        status = 'delayed';
      }

      // Dynamic load calculation with peak morning curve
      const peakWeight = Math.sin(((simTimeMin - 450) / 180) * Math.PI);
      let calculatedLoad = Math.round(cfg.baseLoad + peakWeight * 14 * cfg.surgeFactor);

      // In S3 (auditorium surge), routes connecting to S07 get extra load
      if (scenario === 'S3' && (cfg.routeId === 'R1' || cfg.routeId === 'R2')) {
        calculatedLoad += 9;
      }

      // If rec-0007 applied, B3 load is reduced due to B5 sharing load!
      if (appliedRecIds.has('rec-0007') && cfg.id === 'B3') {
        calculatedLoad = Math.round(calculatedLoad * 0.72);
      }

      calculatedLoad = Math.max(4, Math.min(Math.round(capacity * 1.3), calculatedLoad));
      const loadPct = Math.round((calculatedLoad / capacity) * 100);

      // Determine approximate next stop
      const stopIndex = Math.min(
        route.stop_sequence.length - 1,
        Math.floor(progress * route.stop_sequence.length)
      );
      const nextStop = route.stop_sequence[stopIndex] || route.stop_sequence[0];

      const svgPos = projectToSvg(coords.x, coords.y);

      list.push({
        vehicle_id: cfg.id,
        type: vehicle.type,
        route_id: cfg.routeId,
        capacity,
        seated: vehicle.seated,
        load: calculatedLoad,
        loadPct,
        speed_mps: isBreakdown ? 0 : (isTrafficDelayed ? 4.2 : route.free_flow_speed_mps),
        x: coords.x,
        y: coords.y,
        svgX: svgPos.x,
        svgY: svgPos.y,
        angle: coords.angle,
        status,
        nextStop,
        tripId: `T_${cfg.routeId}_01`
      });
    });

    return list;
  }, [network, simTimeMin, scenario, appliedRecIds]);

  const acceptRecommendation = useCallback(async (id: string) => {
    const res = await api.applyRecommendation(id);
    setAppliedRecIds(prev => new Set([...prev, id]));
    if (res.data?.new_plan) {
      setWorkingPlan(res.data.new_plan);
    }
  }, []);

  const rejectRecommendation = useCallback((id: string) => {
    setRecommendations(prev => prev.filter(r => r.id !== id));
  }, []);

  const triggerScenario = useCallback(async (s: ScenarioId) => {
    setScenario(s);
    if (s === 'S1') {
      setActiveDisruptionAlert('S1 Traffic Delay active (+8 min corridor slowdown on Metro R3).');
    } else if (s === 'S2') {
      setActiveDisruptionAlert('S2 Vehicle Breakdown active: Bus B3 reported engine failure at 08:05.');
    } else if (s === 'S3') {
      setActiveDisruptionAlert('S3 Demand Surge active: +120 attendee surge at Auditorium S07.');
    } else {
      setActiveDisruptionAlert(null);
    }
    await api.runScenario(s);
  }, []);

  const resetToBaseline = useCallback(() => {
    api.resetPlan();
    setAppliedRecIds(new Set());
    setScenario('S0');
    setActiveDisruptionAlert(null);
    setSimTimeMin(470);
  }, []);

  const value = useMemo(
    () => ({
      simTimeMin,
      setSimTimeMin,
      isPlaying,
      togglePlay,
      speed,
      setSpeed,
      scenario,
      setScenario,
      theme,
      toggleTheme,
      activeScreen,
      setActiveScreen,
      highlightedEntity,
      setHighlightedEntity,
      network,
      workingPlan,
      alerts,
      recommendations,
      appliedRecIds,
      acceptRecommendation,
      rejectRecommendation,
      activeVehicles,
      isLiveApi,
      activeDisruptionAlert,
      triggerScenario,
      resetToBaseline
    }),
    [
      simTimeMin,
      isPlaying,
      togglePlay,
      speed,
      scenario,
      theme,
      toggleTheme,
      activeScreen,
      highlightedEntity,
      network,
      workingPlan,
      alerts,
      recommendations,
      appliedRecIds,
      acceptRecommendation,
      rejectRecommendation,
      activeVehicles,
      isLiveApi,
      activeDisruptionAlert,
      triggerScenario,
      resetToBaseline
    ]
  );

  return <SimulationContext.Provider value={value}>{children}</SimulationContext.Provider>;
};

export const useSimulation = () => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};
