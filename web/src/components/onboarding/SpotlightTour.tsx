import React, { useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { X, ArrowRight, ArrowLeft, Sparkles } from 'lucide-react';
import { SpotlightRing, useCornerPlacement, useTargetBox } from './spotlight';

interface TourStepDef {
  title: string;
  text: string;
  screen: string;
  /** CSS selectors for the on-screen element this step explains (first visible match is outlined). */
  target?: string[];
  actionText?: string;
  onAction?: (sim: any) => void;
}

const TOUR_STEPS: TourStepDef[] = [
  {
    title: '1. Welcome to RoutePulse',
    text: "RoutePulse doesn't just show buses on a map. It re-plans the fleet so the morning peak never overloads a bus. This score sums up the whole network: green is healthy, amber is strained, red is critical.",
    screen: 'map',
    target: ['.health-badge']
  },
  {
    title: '2. The live map',
    text: 'Lines are coloured by route. Each bus wears its route colour, and the ring around it shows how full it is: green has seats, amber is filling up, red is full. This is bus B3.',
    screen: 'map',
    target: ['[data-tour="vehicle-B3"]', '.map-svg'],
    actionText: 'Inspect Bus B3',
    onAction: sim => {
      const b3 = sim.activeVehicles.find((v: any) => v.vehicle_id === 'B3');
      if (b3) sim.setSelectedEntity({ type: 'vehicle', id: 'B3', data: b3 });
    }
  },
  {
    title: '3. Replay time',
    text: 'Scrub between 07:30 and 10:30 along this bar. The coloured strip above the slider shows when crowding peaks.',
    screen: 'map',
    target: ['.scrubber-track-container'],
    actionText: 'Jump to peak (08:15)',
    onAction: sim => sim.setSimTimeMin(495)
  },
  {
    title: '4. Arrivals',
    text: 'Each bar is an 80% likely arrival window, not one fragile number. The tall tick is the best guess; the dashed tick is the timetable.',
    screen: 'eta',
    target: ['[data-tour="eta-window"]', '.solari-departure-board']
  },
  {
    title: '5. Crowding',
    text: 'The grid shows expected passengers per stop and time. Only busy cells are coloured. Problems found are listed here.',
    screen: 'demand',
    target: ['[data-tour="bottlenecks"]', '.screen-card']
  },
  {
    title: '6. Suggestions',
    text: 'Each suggestion shows what it gains and what it costs, and has already passed all 12 hard rules. Accept one to update the plan.',
    screen: 'recommendations',
    target: ['[data-tour="rec-accept"]', '.rec-ticket'],
    actionText: 'Accept rec-0007',
    onAction: sim => sim.acceptRecommendation('rec-0007')
  },
  {
    title: '7. What-if lab',
    text: 'Inject a traffic delay, a bus breakdown or an event surge here, then drag the slider below to compare the fixed timetable with RoutePulse.',
    screen: 'scenarios',
    target: ['[data-tour="scenario-cards"]'],
    actionText: 'Try the S2 breakdown',
    onAction: sim => sim.triggerScenario('S2')
  },
  {
    title: '8. Help is one key away',
    text: 'Press ? anytime for the glossary, guide and shortcuts. Press Ctrl+K to search any screen, stop or bus.',
    screen: 'map',
    target: ['[aria-label="Help Centre"]']
  }
];

export const SpotlightTour: React.FC = () => {
  const sim = useSimulation();
  const { isTourActive, tourStep, nextTourStep, prevTourStep, skipTour, setActiveScreen } = sim;

  const currentStep = TOUR_STEPS[tourStep];
  const cardRef = useRef<HTMLDivElement | null>(null);

  // The inspector drawer would hide the next step's target, so each step starts with it closed
  useEffect(() => {
    if (isTourActive) sim.closeInspectorDrawer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTourActive, tourStep]);

  useEffect(() => {
    if (!isTourActive || !currentStep) return;
    if (currentStep.screen && sim.activeScreen !== currentStep.screen) {
      setActiveScreen(currentStep.screen);
    }
  }, [isTourActive, tourStep, currentStep, sim.activeScreen, setActiveScreen]);

  const active = isTourActive && !!currentStep;
  const targetBox = useTargetBox(currentStep?.target, tourStep, active);
  const placement = useCornerPlacement(targetBox, 400, cardRef, active);

  if (!active) return null;

  const isFirst = tourStep === 0;
  const isLast = tourStep === TOUR_STEPS.length - 1;

  return (
    <>
      {/* The real UI stays fully visible and clickable; only the explained element is outlined */}
      <SpotlightRing box={targetBox} />

      <div
        ref={cardRef}
        className="tour-card"
        role="dialog"
        aria-label="Guided tour"
        style={{
          position: 'fixed',
          zIndex: 300,
          maxWidth: 400,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          padding: '18px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          transition: 'left 260ms var(--ease-standard), top 260ms var(--ease-standard)',
          ...placement
        }}
      >
        {/* Header: Title + Close Button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={16} style={{ color: 'var(--load-amber)', flexShrink: 0 }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentStep.title}
            </h3>
          </div>
          <button className="btn-icon" onClick={skipTour} title="Exit tour (Esc)" aria-label="Close Tour">
            <X size={16} />
          </button>
        </div>

        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {currentStep.text}
        </p>

        {currentStep.actionText && currentStep.onAction && (
          <button
            className="btn"
            onClick={() => currentStep.onAction?.(sim)}
            style={{ padding: '6px 12px', fontSize: '0.8125rem', fontWeight: 600, alignSelf: 'flex-start', gap: 6 }}
          >
            <Sparkles size={13} />
            <span>{currentStep.actionText}</span>
          </button>
        )}

        {/* Footer: Progress Dots + Controls */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: 10,
            borderTop: '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', gap: 4 }}>
            {TOUR_STEPS.map((_, idx) => (
              <span
                key={idx}
                style={{
                  width: idx === tourStep ? 16 : 6,
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: idx === tourStep ? 'var(--accent)' : 'var(--border-strong)',
                  transition: 'all 0.2s ease'
                }}
              />
            ))}
          </div>

          <div style={{ display: 'flex', gap: 6 }}>
            {!isFirst && (
              <button className="btn" onClick={prevTourStep} style={{ padding: '5px 10px', fontSize: '0.8125rem', gap: 4 }}>
                <ArrowLeft size={13} />
                <span>Back</span>
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={nextTourStep}
              style={{ padding: '5px 12px', fontSize: '0.8125rem', gap: 4 }}
            >
              <span>{isLast ? 'Finish Tour' : 'Next'}</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
