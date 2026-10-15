import React, { useEffect, useRef, useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { RotateCcw, Sparkles } from 'lucide-react';
import { SpotlightRing, useCornerPlacement, useTargetBox } from './spotlight';

interface DemoPhase {
  id: number;
  durationMs: number;
  caption: string;
  /** Selectors for the UI element this phase is about; it is outlined while the caption plays. */
  target: string[];
  setup: (sim: any) => void;
}

const DEMO_PHASES: DemoPhase[] = [
  {
    id: 1,
    target: ['[data-tour="vehicle-B3"]', '.map-svg'],
    durationMs: 14000,
    caption: '1/6: Morning Peak Overload. Regional commuters arrive at Metro S13; Route R3 spikes over 130% capacity under the static baseline schedule.',
    setup: sim => {
      sim.setActiveScreen('map');
      sim.setScenario('S0');
      sim.setSimTimeMin(480);
      sim.setSpeed(10);
    }
  },
  {
    id: 2,
    target: ['[data-tour="eta-window"]', '.solari-departure-board'],
    durationMs: 14000,
    caption: '2/6: ETA Arrival Windows. Operators inspect p10–p90 arrival bounds calibrated on historical dwell times rather than brittle static schedules.',
    setup: sim => {
      sim.setActiveScreen('eta');
    }
  },
  {
    id: 3,
    target: ['[data-tour="rec-accept"]', '.rec-ticket'],
    durationMs: 15000,
    caption: '3/6: Proactive Recommendation. The CP-SAT engine recommends dispatching idle reserve bus B5 at 08:21 to alleviate R3 crowding.',
    setup: sim => {
      sim.setActiveScreen('recommendations');
    }
  },
  {
    id: 4,
    target: ['.health-badge'],
    durationMs: 15000,
    caption: '4/6: Validated Plan Update. Rec-0007 accepted: 0 constraint violations guaranteed. Left-behind passengers immediately decrease by 41.',
    setup: sim => {
      sim.acceptRecommendation('rec-0007');
      sim.setActiveScreen('map');
    }
  },
  {
    id: 5,
    target: ['[data-tour="vehicle-B3"]', '.map-svg'],
    durationMs: 16000,
    caption: '5/6: Disruption Resilience. Injecting S2 breakdown (bus B3 engine failure). The rolling optimizer activates recovery mode.',
    setup: sim => {
      sim.triggerScenario('S2');
      sim.setSimTimeMin(488);
      sim.setActiveScreen('map');
    }
  },
  {
    id: 6,
    target: ['[data-tour="kpi-compare"]', '[data-tour="before-after"]'],
    durationMs: 16000,
    caption: '6/6: Baseline vs RoutePulse Comparison. 25% lower passenger wait time, 66% fewer left behind, and 0 hard constraint violations.',
    setup: sim => {
      sim.setActiveScreen('scenarios');
    }
  }
];

export const ShowcaseDemo: React.FC = () => {
  const sim = useSimulation();
  const { isAutoDemoActive, stopAutoDemo } = sim;

  const [phaseIndex, setPhaseIndex] = useState(0);
  const [phaseProgress, setPhaseProgress] = useState(0); // 0 to 100
  const cardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isAutoDemoActive) return;

    setPhaseIndex(0);
    DEMO_PHASES[0].setup(sim);
  }, [isAutoDemoActive]);

  useEffect(() => {
    if (!isAutoDemoActive) return;

    const currentPhase = DEMO_PHASES[phaseIndex];
    if (!currentPhase) return;

    currentPhase.setup(sim);
    setPhaseProgress(0);

    // Wall-clock progress; no side effects inside state updaters (StrictMode runs those twice)
    const startedAt = Date.now();
    const timer = setInterval(() => {
      const pct = ((Date.now() - startedAt) / currentPhase.durationMs) * 100;
      if (pct < 100) {
        setPhaseProgress(pct);
        return;
      }
      clearInterval(timer);
      if (phaseIndex < DEMO_PHASES.length - 1) {
        setPhaseIndex(phaseIndex + 1);
      } else {
        // Demo finished: hand control to the user in the final state
        stopAutoDemo();
      }
    }, 200);

    return () => clearInterval(timer);
  }, [isAutoDemoActive, phaseIndex]);

  const currentPhase = DEMO_PHASES[phaseIndex] || DEMO_PHASES[0];
  const targetBox = useTargetBox(currentPhase.target, phaseIndex, isAutoDemoActive);
  const placement = useCornerPlacement(targetBox, 440, cardRef, isAutoDemoActive);

  if (!isAutoDemoActive) return null;

  const handleReset = () => {
    setPhaseIndex(0);
    setPhaseProgress(0);
    DEMO_PHASES[0].setup(sim);
  };

  return (
    <>
      {/* Outline the real UI element the caption is describing; the rest of the UI stays visible */}
      <SpotlightRing box={targetBox} />

    <div
      ref={cardRef}
      style={{
        position: 'fixed',
        maxWidth: 440,
        background: 'var(--bg-surface)',
        border: '1.5px solid var(--accent)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-lg)',
        padding: '14px 18px',
        zIndex: 300,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        transition: 'left 260ms var(--ease-standard), top 260ms var(--ease-standard)',
        ...placement
      }}
    >
      {/* Top Row: Tag + Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div
          style={{
            padding: '3px 9px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--accent)',
            color: 'var(--accent-contrast)',
            fontWeight: 700,
            fontSize: '0.75rem'
          }}
        >
          Auto-demo
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            className="btn"
            onClick={handleReset}
            style={{ padding: '5px 9px', fontSize: '0.8125rem' }}
            title="Restart showcase from Step 1"
            aria-label="Restart showcase"
          >
            <RotateCcw size={13} />
          </button>
          <button
            className="btn btn-primary"
            onClick={stopAutoDemo}
            style={{ padding: '5px 12px', fontSize: '0.8125rem', gap: 5 }}
            title="Exit auto-demo and take interactive manual control"
          >
            <Sparkles size={13} />
            <span>Take control</span>
          </button>
        </div>
      </div>

      <span style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.5 }}>
        {currentPhase.caption}
      </span>

      {/* Segmented Progress Bar */}
      <div style={{ display: 'flex', gap: 4, height: 4, width: '100%' }}>
        {DEMO_PHASES.map((p, idx) => {
          let fillWidth = 0;
          if (idx < phaseIndex) fillWidth = 100;
          else if (idx === phaseIndex) fillWidth = phaseProgress;

          return (
            <div
              key={p.id}
              style={{
                flex: 1,
                background: 'var(--bg-hover)',
                borderRadius: 2,
                overflow: 'hidden'
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${fillWidth}%`,
                  background: 'var(--accent)',
                  transition: 'width 0.15s linear'
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
    </>
  );
};
