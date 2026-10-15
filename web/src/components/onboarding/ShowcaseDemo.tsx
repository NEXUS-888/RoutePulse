import React, { useEffect, useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Play, Pause, RotateCcw, X, Sparkles, CheckCircle2 } from 'lucide-react';

interface DemoPhase {
  id: number;
  durationMs: number;
  caption: string;
  setup: (sim: any) => void;
}

const DEMO_PHASES: DemoPhase[] = [
  {
    id: 1,
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
    durationMs: 14000,
    caption: '2/6: ETA Arrival Windows. Operators inspect p10–p90 arrival bounds calibrated on historical dwell times rather than brittle static schedules.',
    setup: sim => {
      sim.setActiveScreen('eta');
    }
  },
  {
    id: 3,
    durationMs: 15000,
    caption: '3/6: Proactive Recommendation. The CP-SAT engine recommends dispatching idle reserve bus B5 at 08:21 to alleviate R3 crowding.',
    setup: sim => {
      sim.setActiveScreen('recommendations');
    }
  },
  {
    id: 4,
    durationMs: 15000,
    caption: '4/6: Validated Plan Update. Rec-0007 accepted: 0 constraint violations guaranteed. Left-behind passengers immediately decrease by 41.',
    setup: sim => {
      sim.acceptRecommendation('rec-0007');
      sim.setActiveScreen('map');
    }
  },
  {
    id: 5,
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

    const stepMs = 200;
    const progressInc = (stepMs / currentPhase.durationMs) * 100;

    const timer = setInterval(() => {
      setPhaseProgress(prev => {
        const next = prev + progressInc;
        if (next >= 100) {
          if (phaseIndex < DEMO_PHASES.length - 1) {
            setPhaseIndex(p => p + 1);
          } else {
            // Demo finished, stay in final state or take control
            stopAutoDemo();
          }
          return 0;
        }
        return next;
      });
    }, stepMs);

    return () => clearInterval(timer);
  }, [isAutoDemoActive, phaseIndex]);

  if (!isAutoDemoActive) return null;

  const currentPhase = DEMO_PHASES[phaseIndex] || DEMO_PHASES[0];

  const handleReset = () => {
    setPhaseIndex(0);
    setPhaseProgress(0);
    DEMO_PHASES[0].setup(sim);
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 84,
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
        maxWidth: '820px',
        background: 'var(--bg-surface)',
        border: '1.5px solid var(--accent)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-lg)',
        padding: '14px 20px',
        zIndex: 150,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)'
      }}
    >
      {/* Top Row: Caption + Phase Tracker + Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          <div
            style={{
              padding: '4px 8px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--accent)',
              color: 'var(--accent-contrast)',
              fontWeight: 700,
              fontSize: '0.72rem',
              letterSpacing: '0.04em',
              textTransform: 'uppercase'
            }}
          >
            Showcase
          </div>
          <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>
            {currentPhase.caption}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            className="btn btn-primary"
            onClick={stopAutoDemo}
            style={{ padding: '6px 12px', fontSize: '0.78rem', gap: 5 }}
            title="Exit auto-demo and take interactive manual control"
          >
            <Sparkles size={13} style={{ color: 'var(--load-amber)' }} />
            <span>Take Control</span>
          </button>

          <button
            className="btn btn-outline"
            onClick={handleReset}
            style={{ padding: '6px 10px', fontSize: '0.78rem' }}
            title="Restart showcase from Step 1"
          >
            <RotateCcw size={13} />
          </button>
        </div>
      </div>

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
  );
};
