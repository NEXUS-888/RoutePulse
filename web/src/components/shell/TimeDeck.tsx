import React from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  AlertCircle,
  Zap
} from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';
import { formatTimeMin } from '../../utils/geo';

export const TimeDeck: React.FC = () => {
  const {
    simTimeMin,
    setSimTimeMin,
    isPlaying,
    togglePlay,
    speed,
    setSpeed,
    scenario
  } = useSimulation();

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSimTimeMin(parseFloat(e.target.value));
  };

  const jumpToMorningPeak = () => {
    setSimTimeMin(495); // 08:15 Morning peak
  };

  return (
    <footer className="time-deck" aria-label="Simulation Time Deck">
      {/* Deck Left: Play/Pause + Clock */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button
          className="btn-icon"
          onClick={togglePlay}
          title={isPlaying ? "Pause replay" : "Play replay"}
          style={{
            width: 38,
            height: 38,
            borderRadius: 'var(--radius-sm)',
            background: isPlaying ? 'var(--bg-surface-elevated)' : 'var(--route-r1)',
            color: isPlaying ? 'var(--text-primary)' : '#FFFFFF',
            border: '1px solid var(--border-color)'
          }}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Simulated Time
          </div>
          <div className="time-deck-clock tabular-nums">
            {formatTimeMin(simTimeMin)}
          </div>
        </div>

        <button
          className="btn"
          onClick={jumpToMorningPeak}
          title="Jump playhead directly to 08:15 Morning Peak"
          style={{ padding: '3px 8px', fontSize: '0.72rem', gap: 4 }}
        >
          <Zap size={13} style={{ color: 'var(--load-amber)' }} />
          <span>Peak (08:15)</span>
        </button>
      </div>

      {/* Deck Center: Scrubber Track with Demand Heat-Strip & Event Pins */}
      <div className="scrubber-track-container">
        {/* Heat-Strip & Disruption Event Pins */}
        <div style={{ position: 'relative', width: '100%', marginBottom: 2 }}>
          <div className="heat-strip-bar">
            {/* 07:30 to 08:00: Light (<85%) */}
            <div style={{ flex: 30, background: 'var(--load-teal)', opacity: 0.7 }} title="07:30-08:00 Low Demand" />
            {/* 08:00 to 08:45: Peak Overload (>100%) */}
            <div style={{ flex: 45, background: 'var(--load-coral)', opacity: 0.85 }} title="08:00-08:45 Critical Morning Peak" />
            {/* 08:45 to 09:30: High/Moderate (85-100%) */}
            <div style={{ flex: 45, background: 'var(--load-amber)', opacity: 0.75 }} title="08:45-09:30 Moderate Demand" />
            {/* 09:30 to 10:30: Low (<85%) */}
            <div style={{ flex: 60, background: 'var(--load-teal)', opacity: 0.7 }} title="09:30-10:30 Post-Peak Low Demand" />
          </div>

          {/* S1 Event Pin */}
          {scenario === 'S1' && (
            <div
              style={{
                position: 'absolute',
                left: `${((490 - 450) / 180) * 100}%`,
                top: -14,
                transform: 'translateX(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                fontSize: '0.65rem',
                color: 'var(--load-amber)',
                fontWeight: 700
              }}
              title="08:10 S1 Traffic Delay Injected"
            >
              <AlertCircle size={11} />
              <span>S1 (08:10)</span>
            </div>
          )}

          {/* S2 Event Pin */}
          {scenario === 'S2' && (
            <div
              style={{
                position: 'absolute',
                left: `${((485 - 450) / 180) * 100}%`,
                top: -14,
                transform: 'translateX(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                fontSize: '0.65rem',
                color: 'var(--load-coral)',
                fontWeight: 700
              }}
              title="08:05 S2 Bus B3 Engine Failure Injected"
            >
              <AlertCircle size={11} />
              <span>S2 Breakdown (08:05)</span>
            </div>
          )}

          {/* S3 Event Pin */}
          {scenario === 'S3' && (
            <div
              style={{
                position: 'absolute',
                left: `${((510 - 450) / 180) * 100}%`,
                top: -14,
                transform: 'translateX(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                fontSize: '0.65rem',
                color: 'var(--route-r3)',
                fontWeight: 700
              }}
              title="08:30 S3 Event Demand Spike at Auditorium Injected"
            >
              <AlertCircle size={11} />
              <span>S3 Spike (08:30)</span>
            </div>
          )}
        </div>

        {/* Scrubber Range Slider */}
        <input
          type="range"
          min={450}
          max={630}
          step={0.25}
          value={simTimeMin}
          onChange={handleSliderChange}
          className="time-range-slider"
          aria-label="Simulation Time Scrubber"
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
          <span>07:30</span>
          <span>08:00</span>
          <span style={{ color: 'var(--load-coral)', fontWeight: 600 }}>08:30 (Peak)</span>
          <span>09:00</span>
          <span>09:30</span>
          <span>10:00</span>
          <span>10:30</span>
        </div>
      </div>

      {/* Deck Right: Speed Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Speed:
        </span>
        <div
          style={{
            display: 'flex',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
            padding: 2
          }}
        >
          {([1, 10, 30] as const).map(s => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className="btn"
              style={{
                padding: '3px 9px',
                fontSize: '0.75rem',
                fontWeight: 600,
                border: 'none',
                background: speed === s ? 'var(--route-r1)' : 'transparent',
                color: speed === s ? '#FFFFFF' : 'var(--text-secondary)',
                borderRadius: 'var(--radius-xs)'
              }}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </footer>
  );
};
