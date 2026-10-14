import React, { useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { X, ArrowRight, ArrowLeft, Check, Sparkles } from 'lucide-react';

interface TourStepDef {
  title: string;
  text: string;
  screen: string;
  actionText?: string;
  onAction?: (sim: any) => void;
}

const TOUR_STEPS: TourStepDef[] = [
  {
    title: '1. Welcome to RoutePulse',
    text: "RoutePulse doesn't just show buses on a map—it dynamically optimizes fleet schedules to prevent peak overcrowding.",
    screen: 'map'
  },
  {
    title: '2. Status Ribbon & Health',
    text: 'The top ribbon shows the live Pulse Line and Network Health score. Teal is healthy, amber is strained, coral is critical.',
    screen: 'map'
  },
  {
    title: '3. Schematic Campus Map',
    text: 'View hand-authored 45°/90° metro lines. Vehicle capsules feature circular load rings that pulse when exceeding 85% capacity.',
    screen: 'map',
    actionText: 'Inspect Bus B3',
    onAction: sim => {
      const b3 = sim.activeVehicles.find((v: any) => v.vehicle_id === 'B3');
      if (b3) sim.setSelectedEntity({ type: 'vehicle', id: 'B3', data: b3 });
    }
  },
  {
    title: '4. Replay Time Deck',
    text: 'Scrub replay time between 07:30 and 10:30. Observe the heat-strip showing passenger demand surge during morning peak.',
    screen: 'map',
    actionText: 'Jump to Peak (08:15)',
    onAction: sim => sim.setSimTimeMin(495)
  },
  {
    title: '5. ETA Arrival Windows',
    text: 'Inspect arrival windows (p10–p90) rather than fragile single ETAs. Hover capsules to see plain-language delay diagnosis.',
    screen: 'eta'
  },
  {
    title: '6. Demand & Alerts',
    text: 'Detect A1–A8 operational bottlenecks: corridor overcrowding, missed connections at Hub S03, and student queues.',
    screen: 'demand'
  },
  {
    title: '7. Recommendation Tickets',
    text: 'Operator decision cards provide clear evidence, trade-offs, and delta metrics for passengers and vehicle kilometers.',
    screen: 'recommendations'
  },
  {
    title: '8. 0 Violations Guarantee',
    text: 'Apply optimization recommendations with confidence. Hard rules H1–H12 are verified by solver to ensure 0 violations.',
    screen: 'recommendations',
    actionText: 'Accept Rec-0007',
    onAction: sim => sim.acceptRecommendation('rec-0007')
  },
  {
    title: '9. Scenario Lab',
    text: 'Test resilience against real-world disruptions: inject S1 traffic delay, S2 vehicle breakdown, or S3 demand surge.',
    screen: 'scenarios',
    actionText: 'Test S2 Breakdown',
    onAction: sim => sim.triggerScenario('S2')
  },
  {
    title: '10. Results & Plan Comparison',
    text: 'Compare Baseline-0 vs RoutePulse. RoutePulse eliminates hard-rule violations and reduces left-behind passengers by up to 50%.',
    screen: 'scenarios'
  },
  {
    title: '11. Help Centre & Guide',
    text: 'Press ? anytime to open the Help Centre, glossary, written guide, keyboard shortcuts, or replay this tour.',
    screen: 'map'
  }
];

export const SpotlightTour: React.FC = () => {
  const sim = useSimulation();
  const { isTourActive, tourStep, nextTourStep, prevTourStep, skipTour, setActiveScreen } = sim;

  const currentStep = TOUR_STEPS[tourStep];

  useEffect(() => {
    if (!isTourActive || !currentStep) return;
    if (currentStep.screen && sim.activeScreen !== currentStep.screen) {
      setActiveScreen(currentStep.screen);
    }
  }, [isTourActive, tourStep, currentStep, sim.activeScreen, setActiveScreen]);

  if (!isTourActive || !currentStep) return null;

  const isFirst = tourStep === 0;
  const isLast = tourStep === TOUR_STEPS.length - 1;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(11, 16, 32, 0.65)',
        zIndex: 300,
        pointerEvents: 'auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20
      }}
    >
      <div
        className="tour-card"
        style={{
          width: '100%',
          maxWidth: '460px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          padding: '24px 26px',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          position: 'relative'
        }}
      >
        {/* Header: Title + Close Button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Sparkles size={16} style={{ color: 'var(--load-amber)' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentStep.title}
            </h3>
          </div>
          <button
            className="btn-icon"
            onClick={skipTour}
            title="Exit Tour (Esc)"
            aria-label="Close Tour"
          >
            <X size={16} />
          </button>
        </div>

        {/* Step Body (<25 words) */}
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {currentStep.text}
        </p>

        {/* Optional Action Button ("Try it") */}
        {currentStep.actionText && currentStep.onAction && (
          <button
            className="btn btn-outline"
            onClick={() => currentStep.onAction?.(sim)}
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              fontWeight: 600,
              alignSelf: 'flex-start',
              gap: 6
            }}
          >
            <Sparkles size={13} style={{ color: 'var(--route-r1)' }} />
            <span>{currentStep.actionText}</span>
          </button>
        )}

        {/* Footer: Progress Dots + Controls */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6, paddingTop: 10, borderTop: '1px solid var(--border-subtle)' }}>
          {/* Progress Dots */}
          <div style={{ display: 'flex', gap: 4 }}>
            {TOUR_STEPS.map((_, idx) => (
              <span
                key={idx}
                style={{
                  width: idx === tourStep ? 16 : 6,
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: idx === tourStep ? 'var(--route-r1)' : 'var(--border-color)',
                  transition: 'all 0.2s ease'
                }}
              />
            ))}
          </div>

          {/* Navigation Buttons */}
          <div style={{ display: 'flex', gap: 6 }}>
            {!isFirst && (
              <button
                className="btn btn-outline"
                onClick={prevTourStep}
                style={{ padding: '5px 10px', fontSize: '0.75rem', gap: 4 }}
              >
                <ArrowLeft size={13} />
                <span>Back</span>
              </button>
            )}

            <button
              className="btn btn-primary"
              onClick={nextTourStep}
              style={{ padding: '5px 12px', fontSize: '0.75rem', gap: 4 }}
            >
              <span>{isLast ? 'Finish Tour' : 'Next'}</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
