import React, { useEffect, useRef, useState } from 'react';
import { Sun, Moon, HelpCircle, RotateCcw, Sparkles, ShieldCheck, Search, MoreHorizontal, Info } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';
import { NetworkHealthScore } from './NetworkHealthScore';
import type { ScenarioId } from '../../types';

const SCENARIOS: { id: ScenarioId; label: string }[] = [
  { id: 'S0', label: 'S0 · Morning peak' },
  { id: 'S1', label: 'S1 · Traffic delay' },
  { id: 'S2', label: 'S2 · Bus breakdown' },
  { id: 'S3', label: 'S3 · Event surge' }
];

/** Small overflow menu so rarely used actions don't compete with the primary header controls. */
const MoreMenu: React.FC = () => {
  const { startTour, resetToBaseline, setIsWelcomeOpen } = useSimulation();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const run = (fn: () => void) => () => {
    setOpen(false);
    fn();
  };

  return (
    <div className="menu-wrap" ref={wrapRef}>
      <button
        className="btn-icon"
        onClick={() => setOpen(prev => !prev)}
        aria-label="More actions"
        aria-haspopup="menu"
        aria-expanded={open}
        title="More"
      >
        <MoreHorizontal size={18} />
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          <button className="menu-item" role="menuitem" onClick={run(() => setIsWelcomeOpen(true))}>
            <Info size={15} />
            <span>About RoutePulse</span>
          </button>
          <button className="menu-item" role="menuitem" onClick={run(startTour)}>
            <Sparkles size={15} />
            <span>Take the guided tour</span>
          </button>
          <button className="menu-item" role="menuitem" onClick={run(resetToBaseline)}>
            <RotateCcw size={15} />
            <span>Reset to baseline plan</span>
          </button>
        </div>
      )}
    </div>
  );
};

export const StatusRibbon: React.FC = () => {
  const {
    scenario,
    triggerScenario,
    theme,
    toggleTheme,
    isLiveApi,
    appliedRecIds,
    toggleHelp,
    setActiveScreen,
    toggleCommandPalette
  } = useSimulation();

  return (
    <header className="status-ribbon">
      {/* Left: brand + the one control that changes the whole story (scenario) */}
      <div className="ribbon-left">
        <button
          className="logo-lockup"
          onClick={() => setActiveScreen('map')}
          title="RoutePulse: plan the campus, don't just watch it."
          aria-label="RoutePulse home"
        >
          <svg className="logo-mark" viewBox="0 0 24 24" aria-hidden="true">
            <rect width="24" height="24" rx="6" fill="var(--accent)" />
            <path
              d="M3.5 12.5h4l2.2-5.5 3.6 11 2.4-5.5h4.8"
              fill="none"
              stroke="var(--accent-contrast)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="logo-title">RoutePulse</span>
        </button>

        <label className="scenario-picker">
          <span className="scenario-picker-label">Scenario</span>
          <select
            value={scenario}
            onChange={e => triggerScenario(e.target.value as ScenarioId)}
            aria-label="Simulation Scenario"
          >
            {SCENARIOS.map(s => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Right: one health signal, then utilities */}
      <div className="ribbon-right">
        {appliedRecIds.size > 0 && (
          <div
            className="status-chip live"
            title="Optimized plan active with 0 hard constraint violations"
          >
            <ShieldCheck size={13} />
            <span>Plan updated</span>
          </div>
        )}

        <NetworkHealthScore />

        <div
          className={`status-chip ${isLiveApi ? 'live' : 'offline'}`}
          title={
            isLiveApi
              ? 'Connected to the live FastAPI backend'
              : 'No backend connected: showing the bundled demo data (measured evaluation results + replayed scenario). Start the API for live models.'
          }
        >
          <span className="pulse-dot" />
          <span>{isLiveApi ? 'Live' : 'Demo data'}</span>
        </div>

        <span className="ribbon-divider" aria-hidden="true" />

        <button
          className="btn search-btn"
          onClick={toggleCommandPalette}
          title="Search screens, stops and vehicles (Ctrl+K or /)"
        >
          <Search size={15} />
          <span className="search-btn-label">Search</span>
          <kbd>Ctrl K</kbd>
        </button>

        <button
          className="btn-icon"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Timetable (light)' : 'Signage (dark)'} theme (T)`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <button
          className="btn-icon"
          onClick={toggleHelp}
          title="Help, glossary & shortcuts (?)"
          aria-label="Help Centre"
        >
          <HelpCircle size={17} />
        </button>

        <MoreMenu />
      </div>
    </header>
  );
};
