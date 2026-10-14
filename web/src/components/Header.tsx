import React from 'react';
import {
  Play,
  Pause,
  Sun,
  Moon,
  Clock,
  Radio,
  RotateCcw,
  ShieldCheck,
  Activity
} from 'lucide-react';
import { useSimulation } from '../context/SimulationContext';
import { formatTimeMin } from '../utils/geo';
import type { ScenarioId } from '../types';

export const Header: React.FC = () => {
  const {
    simTimeMin,
    setSimTimeMin,
    isPlaying,
    togglePlay,
    speed,
    setSpeed,
    scenario,
    triggerScenario,
    theme,
    toggleTheme,
    isLiveApi,
    appliedRecIds,
    resetToBaseline,
    alerts
  } = useSimulation();

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSimTimeMin(parseFloat(e.target.value));
  };

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    triggerScenario(e.target.value as ScenarioId);
  };

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo-badge">
          <div className="logo-icon">
            <Activity size={20} />
          </div>
          <div>
            <span>RoutePulse</span>
            <div style={{ fontSize: '0.65rem', fontWeight: 500, color: 'var(--text-tertiary)', lineHeight: 1 }}>
              Operator & Student Platform
            </div>
          </div>
        </div>

        <div className="badge-live" title={isLiveApi ? "Connected to FastAPI Backend" : "Running 100% Offline with Local Contracts & Fixtures"}>
          <span className="badge-dot" />
          <span>{isLiveApi ? 'LIVE API' : 'OFFLINE MODE'}</span>
        </div>

        {appliedRecIds.size > 0 && (
          <span className="badge badge-success" style={{ gap: 4 }}>
            <ShieldCheck size={14} />
            <span>0 Violations (Plan Updated)</span>
          </span>
        )}
      </div>

      <div className="header-center">
        <div className="clock-display tabular-nums">
          <Clock size={16} className="clock-icon" />
          <span>{formatTimeMin(simTimeMin)}</span>
        </div>

        <div className="scrubber-controls">
          <button
            className="btn-icon"
            onClick={togglePlay}
            title={isPlaying ? "Pause simulation replay" : "Play simulation replay"}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>

          <input
            type="range"
            min={450}
            max={630}
            step={0.5}
            value={simTimeMin}
            onChange={handleTimeChange}
            className="time-slider"
            title={`Scrub simulation time: ${formatTimeMin(simTimeMin)}`}
          />

          <div className="speed-selector" title="Replay speed multiplier">
            <button
              className={`speed-btn ${speed === 1 ? 'active' : ''}`}
              onClick={() => setSpeed(1)}
            >
              1x
            </button>
            <button
              className={`speed-btn ${speed === 10 ? 'active' : ''}`}
              onClick={() => setSpeed(10)}
            >
              10x
            </button>
            <button
              className={`speed-btn ${speed === 30 ? 'active' : ''}`}
              onClick={() => setSpeed(30)}
            >
              30x
            </button>
          </div>
        </div>
      </div>

      <div className="header-right">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Scenario:
          </span>
          <select
            value={scenario}
            onChange={handleScenarioChange}
            style={{
              padding: '4px 8px',
              fontSize: '0.8rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface-elevated)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            <option value="S0">S0 Normal Peak</option>
            <option value="S1">S1 Traffic Delay (+8m)</option>
            <option value="S2">S2 Vehicle Breakdown (B3)</option>
            <option value="S3">S3 Demand Surge (+120pax)</option>
          </select>
        </div>

        <button
          className="btn-icon"
          onClick={resetToBaseline}
          title="Reset plan and simulation to Baseline-0"
        >
          <RotateCcw size={16} />
        </button>

        <button
          className="btn-icon"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>
    </header>
  );
};
