import React from 'react';
import { Play, Pause, AlertCircle, Zap } from 'lucide-react';
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
      <div className="time-deck-left">
        <button
          className="play-btn"
          onClick={togglePlay}
          title={isPlaying ? 'Pause replay (Space)' : 'Play replay (Space)'}
          aria-label={isPlaying ? 'Pause replay' : 'Play replay'}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <div className="time-deck-clock-wrap">
          <div className="time-deck-clock tabular-nums">{formatTimeMin(simTimeMin)}</div>
          <button
            className="link-btn"
            onClick={jumpToMorningPeak}
            title="Jump the playhead to the 08:15 morning peak"
          >
            <Zap size={12} />
            <span>Jump to peak</span>
          </button>
        </div>
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
          style={{ ['--pct' as string]: `${((simTimeMin - 450) / 180) * 100}%` }}
          aria-label="Simulation Time Scrubber"
        />

        <div className="scrubber-ticks">
          <span>07:30</span>
          <span>08:30</span>
          <span>09:30</span>
          <span>10:30</span>
        </div>
      </div>

      {/* Deck Right: Speed Controls */}
      <div className="segmented" role="group" aria-label="Replay speed">
        {([1, 10, 30] as const).map(s => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={speed === s ? 'active' : ''}
            aria-pressed={speed === s}
          >
            {s}×
          </button>
        ))}
      </div>
    </footer>
  );
};
