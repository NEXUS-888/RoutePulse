import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import type {
  NetworkResponse,
  Plan,
  Alert,
  Recommendation,
  ScenarioId,
  Vehicle,
  Stop,
  Route,
  NetworkHealthInfo,
  SelectedEntity,
  SelectedEntityType,
  UserRole
} from '../types';
import { api } from '../api/client';
import { interpolatePolyline, projectToSvg } from '../utils/geo';
import { getSchematicPointAtProgress, SCHEMATIC_STOPS } from '../map/schematic';

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
  schematicX: number;
  schematicY: number;
  angle: number;
  status: 'running' | 'idle' | 'breakdown' | 'delayed';
  nextStop: string;
  tripId: string;
}

export interface MapLayersState {
  routes: boolean;
  stops: boolean;
  vehicles: boolean;
  loadRings: boolean;
  demandGlow: boolean;
  alerts: boolean;
  transfers: boolean;
  accessibility: boolean;
  disruptions: boolean;
  planComparison: boolean;
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

  // New spec features
  networkHealth: NetworkHealthInfo;
  networkStress: number;
  avgLoadPct: number;
  mapViewMode: 'schematic' | 'geographic';
  setMapViewMode: (mode: 'schematic' | 'geographic') => void;
  toggleMapViewMode: () => void;
  selectedEntity: SelectedEntity | null;
  setSelectedEntity: (entity: SelectedEntity | null) => void;
  closeInspectorDrawer: () => void;
  mapLayers: MapLayersState;
  toggleLayer: (layer: keyof MapLayersState) => void;

  // Onboarding, Tour & Showcase
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
  isWelcomeOpen: boolean;
  setIsWelcomeOpen: (open: boolean) => void;
  isTourActive: boolean;
  tourStep: number;
  startTour: () => void;
  nextTourStep: () => void;
  prevTourStep: () => void;
  skipTour: () => void;
  isAutoDemoActive: boolean;
  autoDemoCaption: string;
  startAutoDemo: () => void;
  stopAutoDemo: () => void;
  isHelpOpen: boolean;
  setIsHelpOpen: (open: boolean) => void;
  toggleHelp: () => void;
  isCommandPaletteOpen: boolean;
  setIsCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Morning peak: 07:30 (450 min) to 10:30 (630 min)
  const [simTimeMin, setSimTimeMin] = useState<number>(470); // Default 07:50
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

  // Inspector & Map View States
  const [mapViewMode, setMapViewMode] = useState<'schematic' | 'geographic'>('schematic');
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);
  const [mapLayers, setMapLayers] = useState<MapLayersState>({
    routes: true,
    stops: true,
    vehicles: true,
    loadRings: true,
    demandGlow: true,
    alerts: true,
    transfers: true,
    accessibility: false,
    disruptions: true,
    planComparison: false
  });

  // Onboarding & Help
  const [userRole, setUserRole] = useState<UserRole>('operator');
  const [isWelcomeOpen, setIsWelcomeOpen] = useState<boolean>(() => {
    return !localStorage.getItem('rp_onboarded_v1');
  });
  const [isTourActive, setIsTourActive] = useState<boolean>(false);
  const [tourStep, setTourStep] = useState<number>(0);
  const [isAutoDemoActive, setIsAutoDemoActive] = useState<boolean>(false);
  const [autoDemoCaption, setAutoDemoCaption] = useState<string>('');
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);

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

  const toggleMapViewMode = useCallback(() => {
    setMapViewMode(prev => (prev === 'schematic' ? 'geographic' : 'schematic'));
  }, []);

  const closeInspectorDrawer = useCallback(() => {
    setSelectedEntity(null);
  }, []);

  const toggleLayer = useCallback((layer: keyof MapLayersState) => {
    setMapLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  const toggleHelp = useCallback(() => {
    setIsHelpOpen(prev => !prev);
  }, []);

  const toggleCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(prev => !prev);
  }, []);

  // Clock progression
  useEffect(() => {
    if (!isPlaying) return;

    const intervalMs = 100;
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
      { id: 'B3', routeId: 'R3', cycleMin: 12, offsetMin: 1, baseLoad: 42, surgeFactor: 1.4 },
      { id: 'B4', routeId: 'R4', cycleMin: 8, offsetMin: 0, baseLoad: 16, surgeFactor: 0.6 },
      { id: 'M1', routeId: 'R2', cycleMin: 10, offsetMin: 7, baseLoad: 17, surgeFactor: 1.0 },
      { id: 'M2', routeId: 'R1', cycleMin: 14, offsetMin: 7, baseLoad: 18, surgeFactor: 0.9 }
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
      if (appliedRecIds.has('rec-0009') && cfg.id === 'B4') {
        capacity = 22;
      }

      // Check breakdown condition for S2
      const isBreakdown = scenario === 'S2' && cfg.id === 'B3' && simTimeMin >= 485;
      const isTrafficDelayed = scenario === 'S1' && cfg.routeId === 'R3';

      let cycle = cfg.cycleMin;
      if (isTrafficDelayed) cycle += 4;

      const progressRaw = ((simTimeMin - cfg.offsetMin) % cycle) / cycle;
      const progress = progressRaw < 0 ? progressRaw + 1 : progressRaw;

      // Polyline interpolation (geographic)
      let coords = interpolatePolyline(route.polyline, progress);
      // Schematic interpolation
      let schematicPos = getSchematicPointAtProgress(cfg.routeId, progress);

      let status: 'running' | 'idle' | 'breakdown' | 'delayed' = 'running';

      if (isBreakdown) {
        status = 'breakdown';
        coords = { x: 350, y: 150, angle: 45 };
        schematicPos = { x: 360, y: 390 }; // Frozen near Admin Block
      } else if (isTrafficDelayed) {
        status = 'delayed';
      }

      // Dynamic load calculation with peak morning curve
      const peakWeight = Math.sin(((simTimeMin - 450) / 180) * Math.PI);
      let calculatedLoad = Math.round(cfg.baseLoad + peakWeight * 14 * cfg.surgeFactor);

      if (scenario === 'S3' && (cfg.routeId === 'R1' || cfg.routeId === 'R2')) {
        calculatedLoad += 9;
      }

      if (appliedRecIds.has('rec-0007') && cfg.id === 'B3') {
        calculatedLoad = Math.round(calculatedLoad * 0.72);
      }

      calculatedLoad = Math.max(4, Math.min(Math.round(capacity * 1.3), calculatedLoad));
      const loadPct = Math.round((calculatedLoad / capacity) * 100);

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
        speed_mps: isBreakdown ? 0 : isTrafficDelayed ? 4.2 : route.free_flow_speed_mps,
        x: coords.x,
        y: coords.y,
        svgX: svgPos.x,
        svgY: svgPos.y,
        schematicX: schematicPos.x,
        schematicY: schematicPos.y,
        angle: coords.angle,
        status,
        nextStop,
        tripId: `T_${cfg.routeId}_01`
      });
    });

    return list;
  }, [network, simTimeMin, scenario, appliedRecIds]);

  // Network Health Score (Exact UI Spec Section 1.7 Formula)
  const networkHealth = useMemo<NetworkHealthInfo>(() => {
    if (activeVehicles.length === 0) {
      return {
        score: 100,
        band: 'teal',
        overCapacityShare: 0,
        leftBehindShare: 0,
        missedConnectionShare: 0,
        delayedTripsShare: 0
      };
    }

    // 1. Share of trips over capacity (>100%)
    const overCapacityCount = activeVehicles.filter(v => v.loadPct > 100).length;
    const overCapacityShare = overCapacityCount / activeVehicles.length;

    // 2. Share of passengers left behind
    const hasCapacityAlert = alerts.some(a => a.code === 'A2');
    let leftBehindShare = 0;
    if (hasCapacityAlert) {
      leftBehindShare = appliedRecIds.has('rec-0007') ? 0.04 : 0.42;
    }

    // 3. Share of transferring passengers who missed their connection
    const hasMissedConnAlert = alerts.some(a => a.code === 'A4');
    let missedConnectionShare = 0;
    if (hasMissedConnAlert) {
      missedConnectionShare = appliedRecIds.has('rec-0007') ? 0.02 : 0.32;
    }

    // 4. Share of trips delayed by more than 3 minutes
    const delayedCount = activeVehicles.filter(v => v.status === 'delayed' || v.status === 'breakdown').length;
    const delayedTripsShare = delayedCount / activeVehicles.length;

    const penalty =
      40 * overCapacityShare +
      30 * leftBehindShare +
      20 * missedConnectionShare +
      10 * delayedTripsShare;

    const score = Math.max(0, Math.min(100, Math.round(100 - penalty)));

    let band: 'teal' | 'amber' | 'coral' = 'teal';
    if (score < 60) band = 'coral';
    else if (score < 80) band = 'amber';

    return {
      score,
      band,
      overCapacityShare: Math.round(overCapacityShare * 100) / 100,
      leftBehindShare: Math.round(leftBehindShare * 100) / 100,
      missedConnectionShare: Math.round(missedConnectionShare * 100) / 100,
      delayedTripsShare: Math.round(delayedTripsShare * 100) / 100
    };
  }, [activeVehicles, alerts, appliedRecIds]);

  // Average load & network stress for the Pulse Line
  const { avgLoadPct, networkStress } = useMemo(() => {
    if (activeVehicles.length === 0) return { avgLoadPct: 50, networkStress: 0.2 };
    const totalLoad = activeVehicles.reduce((acc, v) => acc + v.loadPct, 0);
    const avg = Math.round(totalLoad / activeVehicles.length);
    const stress = Math.min(1.0, Math.max(0.1, (100 - networkHealth.score) / 100 + avg / 200));
    return { avgLoadPct: avg, networkStress: stress };
  }, [activeVehicles, networkHealth]);

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

  // Tour Controls
  const startTour = useCallback(() => {
    setIsWelcomeOpen(false);
    setIsTourActive(true);
    setTourStep(0);
    setActiveScreen('map');
  }, []);

  const nextTourStep = useCallback(() => {
    setTourStep(prev => {
      const next = prev + 1;
      if (next > 10) {
        setIsTourActive(false);
        localStorage.setItem('rp_onboarded_v1', 'true');
        return 0;
      }
      return next;
    });
  }, []);

  const prevTourStep = useCallback(() => {
    setTourStep(prev => Math.max(0, prev - 1));
  }, []);

  const skipTour = useCallback(() => {
    setIsTourActive(false);
    localStorage.setItem('rp_onboarded_v1', 'true');
  }, []);

  // Showcase Auto-Demo Controls
  const startAutoDemo = useCallback(() => {
    setIsWelcomeOpen(false);
    setIsTourActive(false);
    setIsAutoDemoActive(true);
    setActiveScreen('map');
    setScenario('S0');
    setSimTimeMin(470);
    setSpeed(10);
  }, []);

  const stopAutoDemo = useCallback(() => {
    setIsAutoDemoActive(false);
    setAutoDemoCaption('');
  }, []);

  // Keyboard Navigation: Esc closes modals & drawers, ? opens Help
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (selectedEntity) setSelectedEntity(null);
        if (isHelpOpen) setIsHelpOpen(false);
        if (isTourActive) skipTour();
        if (isWelcomeOpen) setIsWelcomeOpen(false);
        if (isAutoDemoActive) stopAutoDemo();
      } else if (e.key === '?' && !e.ctrlKey && !e.metaKey && document.activeElement?.tagName !== 'INPUT') {
        setIsHelpOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEntity, isHelpOpen, isTourActive, isWelcomeOpen, isAutoDemoActive, skipTour, stopAutoDemo]);

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
      resetToBaseline,

      // New features
      networkHealth,
      networkStress,
      avgLoadPct,
      mapViewMode,
      setMapViewMode,
      toggleMapViewMode,
      selectedEntity,
      setSelectedEntity,
      closeInspectorDrawer,
      mapLayers,
      toggleLayer,

      // Onboarding & Help
      userRole,
      setUserRole,
      isWelcomeOpen,
      setIsWelcomeOpen,
      isTourActive,
      tourStep,
      startTour,
      nextTourStep,
      prevTourStep,
      skipTour,
      isAutoDemoActive,
      autoDemoCaption,
      startAutoDemo,
      stopAutoDemo,
      isHelpOpen,
      setIsHelpOpen,
      toggleHelp,
      isCommandPaletteOpen,
      setIsCommandPaletteOpen,
      toggleCommandPalette
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
      resetToBaseline,
      networkHealth,
      networkStress,
      avgLoadPct,
      mapViewMode,
      selectedEntity,
      closeInspectorDrawer,
      mapLayers,
      toggleLayer,
      userRole,
      isWelcomeOpen,
      isTourActive,
      tourStep,
      startTour,
      nextTourStep,
      prevTourStep,
      skipTour,
      isAutoDemoActive,
      autoDemoCaption,
      startAutoDemo,
      stopAutoDemo,
      isHelpOpen,
      toggleHelp,
      isCommandPaletteOpen,
      toggleCommandPalette
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
