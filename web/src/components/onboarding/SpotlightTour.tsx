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
    text: "RoutePulse doesn't just show buses on a map. It re-plans the fleet so the morning peak never overloads a bus.",
    screen: 'map'
  },
  {
    title: '2. The live map',
    text: 'Lines are coloured by route. Each bus wears its route colour, and the ring around it shows how full it is: green has seats, amber is filling up, red is full. The header chip shows overall network health.',
    screen: 'map',
    actionText: 'Inspect Bus B3',
    onAction: sim => {
      const b3 = sim.activeVehicles.find((v: any) => v.vehicle_id === 'B3');
      if (b3) sim.setSelectedEntity({ type: 'vehicle', id: 'B3', data: b3 });
    }
  },
  {
    title: '3. Replay time',
    text: 'Scrub between 07:30 and 10:30 along the bottom bar. The coloured strip above the slider shows when crowding peaks.',
    screen: 'map',
    actionText: 'Jump to peak (08:15)',
    onAction: sim => sim.setSimTimeMin(495)
  },
  {
    title: '4. Arrivals and Crowding',
    text: 'Arrivals shows an 80% likely arrival window for each bus, not one fragile number. Crowding highlights the stops and times where platforms will overflow.',
    screen: 'eta'
  },
  {
    title: '5. Suggestions',
    text: 'Each suggestion shows what it gains and what it costs, and has already passed all 12 hard rules. Accept one to update the plan.',
    screen: 'recommendations',
    actionText: 'Accept rec-0007',
    onAction: sim => sim.acceptRecommendation('rec-0007')
  },
  {
    title: '6. What-if lab',
    text: 'Inject a traffic delay, a bus breakdown or an event surge, then drag the slider to compare the fixed timetable with RoutePulse.',
    screen: 'scenarios',
    actionText: 'Try the S2 breakdown',
    onAction: sim => sim.triggerScenario('S2')
  },
  {
    title: '7. Help is one key away',
    text: 'Press ? anytime for the glossary, guide and shortcuts. Press Ctrl+K to search any screen, stop or bus.',
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
        backgroundColor: 'rgba(8, 7, 6, 0.65)',
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
            <Sparkles size={13} style={{ color: 'var(--accent)' }} />
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
                  backgroundColor: idx === tourStep ? 'var(--accent)' : 'var(--border-color)',
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
