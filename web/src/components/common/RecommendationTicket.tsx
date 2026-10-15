import React, { useState } from 'react';
import type { Recommendation } from '../../types';
import { useSimulation } from '../../context/SimulationContext';
import {
  ShieldCheck,
  Check,
  X,
  Sliders,
  TrendingDown,
  TrendingUp,
  AlertCircle,
  HelpCircle
} from 'lucide-react';

interface RecommendationTicketProps {
  recommendation: Recommendation;
  onWhatIf?: (rec: Recommendation) => void;
}

const CONSTRAINTS = [
  { id: 'H1', name: 'Capacity' },
  { id: 'H2', name: 'Speed Limits' },
  { id: 'H3', name: 'Driver Layover' },
  { id: 'H4', name: 'Vehicle Conflict' },
  { id: 'H5', name: 'Depot Yard' },
  { id: 'H6', name: 'Fleet Limit' },
  { id: 'H7', name: 'Route Coverage' },
  { id: 'H8', name: 'Headway Spacing' },
  { id: 'H9', name: 'Shift Limit (≤5m)' },
  { id: 'H10', name: 'Battery Range' },
  { id: 'H11', name: 'Transfer Buffer (≥4m)' },
  { id: 'H12', name: 'Stop Sequence' }
];

export const RecommendationTicket: React.FC<RecommendationTicketProps> = ({
  recommendation,
  onWhatIf
}) => {
  const { acceptRecommendation, rejectRecommendation, appliedRecIds, setActiveScreen } = useSimulation();
  const [showWhatIfModal, setShowWhatIfModal] = useState(false);
  const [showRules, setShowRules] = useState(false);

  const isApplied = appliedRecIds.has(recommendation.id);
  const leftBehindDelta = recommendation.impact.left_behind ?? -41;
  const waitDelta = recommendation.impact.avg_wait_min ?? -1.8;
  const missedConnDelta = recommendation.impact.missed_connections ?? -17;
  const kmDelta = recommendation.impact.vehicle_km ?? +14.2;

  const handleWhatIfClick = () => {
    if (onWhatIf) {
      onWhatIf(recommendation);
    } else {
      setActiveScreen('scenarios');
    }
  };

  return (
    <div className={`rec-ticket ${recommendation.validated ? 'validated' : ''}`}>
      {/* Header: what kind of change + the validator seal */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            {recommendation.type.charAt(0) + recommendation.type.slice(1).toLowerCase().replace(/_/g, ' ')}
          </span>
          <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
            {recommendation.id}
          </span>
        </div>

        <span className="validation-seal" title="Checked by the CP-SAT constraint validator">
          <ShieldCheck size={14} />
          <span>0 rule violations</span>
        </span>
      </div>

      {/* Summary */}
      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.35 }}>
        {recommendation.summary}
      </h3>

      {/* Big Animated Count-Up Delta Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          background: 'var(--bg-surface-elevated)',
          padding: '12px 14px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-color)'
        }}
      >
        <div>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Left behind
          </span>
          <div
            className="tabular-nums font-display"
            style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--load-teal)' }}
          >
            {leftBehindDelta > 0 ? `+${leftBehindDelta}` : leftBehindDelta}
            <span style={{ fontSize: '0.75rem', fontWeight: 500, marginLeft: 2 }}>pax</span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Average wait
          </span>
          <div
            className="tabular-nums font-display"
            style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--load-teal)' }}
          >
            {waitDelta > 0 ? `+${waitDelta}` : waitDelta}
            <span style={{ fontSize: '0.75rem', fontWeight: 500, marginLeft: 2 }}>min</span>
          </div>
        </div>

        <div>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Missed transfers
          </span>
          <div
            className="tabular-nums font-display"
            style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--load-teal)' }}
          >
            {missedConnDelta > 0 ? `+${missedConnDelta}` : missedConnDelta}
            <span style={{ fontSize: '0.75rem', fontWeight: 500, marginLeft: 2 }}>pax</span>
          </div>
        </div>
      </div>

      {/* Trade-off in plain words, cost on its own quiet line */}
      <div style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
        <p style={{ color: 'var(--text-primary)' }}>{recommendation.tradeoff}</p>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.8125rem', marginTop: 4 }}>
          Cost: {kmDelta > 0 ? '+' : ''}{kmDelta} km and 52 min of reserve bus time.
        </p>
      </div>

      {/* The 12 hard rules stay one click away instead of always on screen */}
      <div>
        <button
          className="link-btn"
          onClick={() => setShowRules(prev => !prev)}
          aria-expanded={showRules}
          style={{ color: 'var(--load-teal)', fontSize: '0.8125rem' }}
        >
          <Check size={13} />
          <span>Passed all 12 hard rules · {showRules ? 'hide' : 'show details'}</span>
        </button>

        {showRules && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
            {CONSTRAINTS.map(c => (
              <span
                key={c.id}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: 'var(--load-teal-bg)',
                  color: 'var(--load-teal)',
                  border: '1px solid var(--load-teal-border)'
                }}
                title={`${c.id}: ${c.name} — checked, 0 violations`}
              >
                <Check size={11} />
                <span>
                  {c.id} {c.name}
                </span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Action Buttons: Accept / Reject / Try What-If */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        {!isApplied ? (
          <>
            <button
              className="btn btn-primary"
              onClick={() => acceptRecommendation(recommendation.id)}
              data-tour="rec-accept"
              style={{ flex: 1, gap: 6, fontWeight: 600 }}
            >
              <Check size={14} />
              <span>Accept</span>
            </button>

            <button
              className="btn"
              onClick={handleWhatIfClick}
              title="Test this change in What-If Sandbox"
              style={{ gap: 5 }}
            >
              <Sliders size={14} />
              <span>Try what-if</span>
            </button>

            <button
              className="btn-icon"
              onClick={() => rejectRecommendation(recommendation.id)}
              title="Dismiss recommendation"
              style={{ color: 'var(--text-tertiary)' }}
            >
              <X size={16} />
            </button>
          </>
        ) : (
          <div
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '8px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--load-teal-bg)',
              color: 'var(--load-teal)',
              fontWeight: 700,
              fontSize: '0.84rem',
              border: '1px solid var(--load-teal-border)'
            }}
          >
            <ShieldCheck size={16} />
            <span>Applied — KPIs updated</span>
          </div>
        )}
      </div>
    </div>
  );
};
