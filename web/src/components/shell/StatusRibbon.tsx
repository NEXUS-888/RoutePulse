import React from 'react';
import {
  Sun,
  Moon,
  HelpCircle,
  RotateCcw,
  Compass,
  Map as MapIcon,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Search
} from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';
import { FleetCadenceRibbon } from './FleetCadenceRibbon';
import { NetworkHealthScore } from './NetworkHealthScore';
import { formatTimeMin } from '../../utils/geo';
import type { ScenarioId } from '../../types';

export const StatusRibbon: React.FC = () => {
  const {
    simTimeMin,
    scenario,
    triggerScenario,
    theme,
    toggleTheme,
    isLiveApi,
    appliedRecIds,
    resetToBaseline,
    mapViewMode,
    toggleMapViewMode,
    startTour,
    toggleHelp,
    setActiveScreen,
    toggleCommandPalette
  } = useSimulation();

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    triggerScenario(e.target.value as ScenarioId);
  };

  return (
    <header className="status-ribbon">
      {/* Zone Left: Logo Lockup + Scenario Chip + Mode */}
      <div className="ribbon-left">
        <div
          className="logo-lockup"
          onClick={() => setActiveScreen('map')}
          title="RoutePulse: Plan the campus. Don't just watch it."
        >
          <div className="logo-header-row">
            <span className="logo-title">RoutePulse</span>
            <div
              style={{
                width: 18,
                height: 18,
                borderRadius: 'var(--radius-xs)',
                background: 'var(--route-r1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.65rem'
              }}
            >
              RP
            </div>
          </div>
          <span className="logo-tagline">Plan the campus. Don't just watch it.</span>
        </div>

        <div style={{ height: 24, width: 1, backgroundColor: 'var(--border-color)', margin: '0 4px' }} />

        {/* Scenario Selector Chip */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select
            value={scenario}
            onChange={handleScenarioChange}
            aria-label="Simulation Scenario"
            style={{
              padding: '4px 10px',
              fontSize: '0.78rem',
              fontWeight: 600,
              fontFamily: 'var(--font-body)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface-elevated)',
              color: 'var(--text-primary)',
              cursor: 'pointer'
            }}
          >
            <option value="S0">S0: Morning Peak (Baseline Overload)</option>
            <option value="S1">S1: Traffic Delay (+8m Corridor)</option>
            <option value="S2">S2: Vehicle Breakdown (Bus B3)</option>
            <option value="S3">S3: Demand Surge (+120pax Event)</option>
          </select>
        </div>

        {/* Live / Offline Status */}
        <div
          className={`status-chip ${isLiveApi ? 'live' : 'offline'}`}
          title={isLiveApi ? "Connected to live FastAPI backend" : "Operating 100% offline with bundled local models & fixtures"}
        >
          <span className="pulse-dot" />
          <span>{isLiveApi ? 'LIVE API' : 'OFFLINE'}</span>
        </div>

        {appliedRecIds.size > 0 && (
          <div
            className="status-chip live"
            style={{ gap: 4 }}
            title="Optimized plan active with 0 hard constraint violations"
          >
            <ShieldCheck size={13} />
            <span>0 Violations (Plan Updated)</span>
          </div>
        )}
      </div>

      {/* Zone Center: Clock + Pulse Line Waveform + Network Health */}
      <div className="ribbon-center">
        {/* Large Tabular Clock */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--bg-surface-elevated)',
            padding: '3px 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)'
          }}
        >
          <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Sim Time
          </span>
          <span
            className="tabular-nums font-mono"
            style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}
          >
            {formatTimeMin(simTimeMin)}
          </span>
        </div>

        {/* Signature Fleet Cadence & Headway Telemetry */}
        <FleetCadenceRibbon width={116} height={24} />

        {/* Live Network Health Score */}
        <NetworkHealthScore />
      </div>

      {/* Zone Right: Schematic Toggle + Tour + Theme + Help */}
      <div className="ribbon-right">
        {/* Command Palette Trigger */}
        <button
          className="btn"
          onClick={toggleCommandPalette}
          title="Open Command Palette (Ctrl+K or /)"
          style={{
            padding: '4px 9px',
            fontSize: '0.74rem',
            gap: 6,
            background: 'var(--bg-surface-elevated)'
          }}
        >
          <Search size={13} style={{ color: 'var(--text-secondary)' }} />
          <span>Search</span>
          <kbd
            style={{
              padding: '1px 5px',
              fontSize: '0.65rem',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-tertiary)',
              fontFamily: 'var(--font-mono)'
            }}
          >
            ⌘K
          </kbd>
        </button>

        {/* View Mode Toggle: Schematic vs Geographic */}
        <button
          className="btn"
          onClick={toggleMapViewMode}
          title={`Switch to ${mapViewMode === 'schematic' ? 'Geographic Real-Metre' : 'Schematic Metro-Style'} view`}
          style={{
            padding: '4px 9px',
            fontSize: '0.74rem',
            gap: 5,
            background: 'var(--bg-surface-elevated)'
          }}
        >
          {mapViewMode === 'schematic' ? <Compass size={14} /> : <MapIcon size={14} />}
          <span>{mapViewMode === 'schematic' ? 'Schematic Map' : 'Geographic Map'}</span>
        </button>

        {/* Replay Tour Button */}
        <button
          className="btn"
          onClick={startTour}
          title="Take the guided 90-second tour"
          style={{
            padding: '4px 9px',
            fontSize: '0.74rem',
            gap: 5,
            background: 'var(--bg-surface-elevated)'
          }}
        >
          <Sparkles size={14} style={{ color: 'var(--load-amber)' }} />
          <span>Tour</span>
        </button>

        {/* Reset Simulation / Plan to Baseline */}
        <button
          className="btn-icon"
          onClick={resetToBaseline}
          title="Reset plan and simulation to Baseline-0"
          aria-label="Reset plan"
        >
          <RotateCcw size={16} />
        </button>

        {/* Theme Toggle (Dark / Light) */}
        <button
          className="btn-icon"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Paper Light' : 'Control Room Dark'} theme`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Help Centre Drawer Trigger */}
        <button
          className="btn-icon"
          onClick={toggleHelp}
          title="Open Help Centre & Glossary (?)"
          aria-label="Help Centre"
        >
          <HelpCircle size={16} />
        </button>
      </div>
    </header>
  );
};
