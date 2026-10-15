import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { useEvalHeadline } from '../../utils/evalStats';
import { PulseLine } from '../shell/PulseLine';
import { Play, Sparkles, ArrowRight } from 'lucide-react';
import type { UserRole } from '../../types';

const whole = (n: number) => Math.round(n);

/**
 * First impression. One promise, four measured proof points, one obvious next step.
 * Every number comes from the evaluation results (never typed in), and the live map stays
 * visible behind it so the product is the backdrop.
 */
export const WelcomeModal: React.FC = () => {
  const {
    isWelcomeOpen,
    setIsWelcomeOpen,
    startTour,
    startAutoDemo,
    setUserRole,
    setActiveScreen
  } = useSimulation();
  const h = useEvalHeadline();

  if (!isWelcomeOpen) return null;

  const dismiss = () => {
    setIsWelcomeOpen(false);
    localStorage.setItem('rp_onboarded_v1', 'true');
  };

  const jumpTo = (role: UserRole, screen: string) => {
    setUserRole(role);
    setActiveScreen(screen);
    dismiss();
  };

  const proof = [
    {
      value: `−${whole(h.s0.left_behind_reduction_pct)}%`,
      label: 'students left at the stop',
      note: `${h.s0.left_behind_b0} → ${h.s0.left_behind_rp} per peak`
    },
    {
      value: `−${whole(h.s0.wait_reduction_pct)}%`,
      label: 'average wait',
      note: `${h.s0.wait_b0} → ${h.s0.wait_rp} min`
    },
    {
      value: `−${whole(h.eta.reduction_pct)}%`,
      label: 'arrival-time error',
      note: `${h.eta.coverage_80}% of arrivals land in the shown window`
    },
    {
      value: `${h.hard_violations}`,
      label: 'rule violations',
      note: `across ${h.runs} simulated runs`
    }
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(8, 7, 6, 0.6)',
        backdropFilter: 'blur(3px)',
        WebkitBackdropFilter: 'blur(3px)',
        zIndex: 200,
        display: 'flex',
        padding: 20,
        overflowY: 'auto'
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 760,
          margin: 'auto', // centres when it fits, scrolls from the top when it doesn't
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-lg)',
          padding: 'clamp(24px, 5vw, 40px)',
          display: 'flex',
          flexDirection: 'column',
          gap: 24
        }}
      >
        {/* Brand + context */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true">
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
            <span className="font-display" style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              RoutePulse
            </span>
            <PulseLine width={72} height={22} />
          </div>
          <span
            style={{
              fontSize: '0.8125rem',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-full)',
              padding: '4px 12px'
            }}
          >
            Problem PS 02 · Campus transit under real constraints
          </span>
        </div>

        {/* Promise */}
        <div>
          <h1
            id="welcome-title"
            className="font-display"
            style={{ fontSize: 'clamp(1.9rem, 5vw, 2.75rem)', fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1.08 }}
          >
            Fewer students left at the stop.
          </h1>
          <p style={{ fontSize: '1.0625rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginTop: 12, maxWidth: 600 }}>
            RoutePulse predicts when campus buses arrive and where crowds will form, then suggests timetable changes. Every
            suggestion is checked against 12 hard safety rules before an operator can accept it.
          </p>
        </div>

        {/* Proof: measured, not claimed */}
        <div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: 1,
              background: 'var(--border-color)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden'
            }}
          >
            {proof.map(p => (
              <div key={p.label} style={{ background: 'var(--bg-surface-elevated)', padding: '16px 16px 14px' }}>
                <div
                  className="font-display tabular-nums"
                  style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--load-teal)', lineHeight: 1 }}
                >
                  {p.value}
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: 6 }}>{p.label}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: 2 }}>{p.note}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-tertiary)', marginTop: 8 }}>
            Versus the fixed timetable, normal morning peak. Simulated campus data, {h.replications} seeded runs per scenario.
            Method and all scenarios: results/summary.md.
          </p>
        </div>

        {/* Next step */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              autoFocus
              onClick={startAutoDemo}
              style={{ padding: '13px 22px', fontSize: '1rem', gap: 10, flex: '1 1 260px' }}
            >
              <Play size={18} />
              <span>Watch the 90-second demo</span>
              <ArrowRight size={16} />
            </button>
            <button className="btn" onClick={startTour} style={{ padding: '13px 20px', fontSize: '0.9375rem', gap: 8 }}>
              <Sparkles size={16} />
              <span>Take the guided tour</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            <span>Or jump straight to</span>
            <button className="link-btn" style={{ fontSize: '0.875rem' }} onClick={() => jumpTo('operator', 'map')}>
              the live map
            </button>
            <span aria-hidden="true">·</span>
            <button className="link-btn" style={{ fontSize: '0.875rem' }} onClick={() => jumpTo('student', 'student')}>
              the student app
            </button>
            <span aria-hidden="true">·</span>
            <button className="link-btn" style={{ fontSize: '0.875rem' }} onClick={() => jumpTo('reviewer', 'scenarios')}>
              the results lab
            </button>
            <span style={{ marginLeft: 'auto', color: 'var(--text-tertiary)' }}>
              Press <kbd style={{ padding: '1px 6px', borderRadius: 4, background: 'var(--bg-hover)', border: '1px solid var(--border-color)' }}>?</kbd> for help
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
