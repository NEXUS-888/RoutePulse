import React, { useState } from 'react';
import type { EtaPrediction } from '../../types';
import { formatTimeMin } from '../../utils/geo';
import { Clock, Info } from 'lucide-react';

interface EtaCapsuleProps {
  prediction: EtaPrediction;
  simTimeMin: number;
  /** Bar + window only: for rows that already show the route, vehicle and countdown. */
  compact?: boolean;
}

const hhmm = (min: number) => formatTimeMin(min).slice(0, 5);

export const EtaCapsule: React.FC<EtaCapsuleProps> = ({ prediction, simTimeMin, compact = false }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const {
    eta_p10_min,
    eta_p50_min,
    eta_p90_min,
    scheduled_time_min,
    confidence,
    reasons,
    route_id,
    vehicle_id
  } = prediction;

  // Horizontal window coordinate mapping
  // Map range: from simTimeMin to simTimeMin + 25 minutes
  const windowStart = simTimeMin;
  const windowRange = 25; // 25-minute horizon

  const p10Pct = Math.max(0, Math.min(100, ((eta_p10_min - windowStart) / windowRange) * 100));
  const p50Pct = Math.max(0, Math.min(100, ((eta_p50_min - windowStart) / windowRange) * 100));
  const p90Pct = Math.max(0, Math.min(100, ((eta_p90_min - windowStart) / windowRange) * 100));
  const schedPct = Math.max(0, Math.min(100, ((scheduled_time_min - windowStart) / windowRange) * 100));

  const minutesAway = Math.max(0, Math.round(eta_p50_min - simTimeMin));
  const delayDelta = eta_p50_min - scheduled_time_min;

  let delayExplanation = 'Running on schedule with clear road conditions.';
  if (delayDelta > 2) {
    delayExplanation = `Bus is ${delayDelta.toFixed(1)} min late vs timetable. Traffic ahead is easing.`;
  } else if (delayDelta < -1) {
    delayExplanation = `Bus is running ${Math.abs(delayDelta).toFixed(1)} min ahead of schedule.`;
  }

  const confidenceColor =
    confidence === 'high'
      ? 'var(--load-teal)'
      : confidence === 'medium'
      ? 'var(--load-amber)'
      : 'var(--load-coral)';

  return (
    <div
      className="eta-capsule-wrapper"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{ position: 'relative', cursor: 'pointer' }}
    >
      {!compact && (
        <>
      {/* Top Header: Route + Vehicle + Arrival Delta */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
              <span
                style={{
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-xs)',
                  background: `var(--route-${route_id.toLowerCase()}, var(--route-r1))`,
                  color: 'var(--on-route)',
                  fontSize: '0.68rem',
                  fontWeight: 700
                }}
              >
                {route_id}
              </span>
              <span style={{ color: 'var(--text-primary)' }}>{vehicle_id}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span className="tabular-nums font-display" style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {minutesAway} min
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>
                ({formatTimeMin(eta_p50_min)})
              </span>
            </div>
          </div>
        </>
      )}

      {/* Horizontal Confidence Capsule Bar */}
      <div className="eta-capsule-bar" style={{ marginTop: 4 }}>
        {/* Shaded p10–p90 Window */}
        <div
          className="eta-window-fill"
          style={{
            left: `${p10Pct}%`,
            width: `${Math.max(4, p90Pct - p10Pct)}%`
          }}
          title={`80% Arrival Window: ${formatTimeMin(eta_p10_min)} – ${formatTimeMin(eta_p90_min)}`}
        />

        {/* Timetable Scheduled Ghost Tick */}
        <div
          className="eta-timetable-ghost"
          style={{ left: `${schedPct}%` }}
          title={`Published Timetable: ${formatTimeMin(scheduled_time_min)}`}
        />

        {/* p50 Median Bold Tick */}
        <div
          className="eta-p50-tick"
          style={{ left: `${p50Pct}%` }}
          title={`p50 Median Expected: ${formatTimeMin(eta_p50_min)}`}
        />
      </div>

      {/* Bottom Labels: Window (+ timetable when not compact) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
        <span className="font-mono">
          {compact ? '' : 'Win: '}{hhmm(eta_p10_min)}–{hhmm(eta_p90_min)}
        </span>
        {!compact && (
          <span className="font-mono">
            Sched: {formatTimeMin(scheduled_time_min)}
          </span>
        )}
      </div>

      {/* Hover Diagnostic Tooltip */}
      {showTooltip && (
        <div
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: 0,
            width: '280px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 100,
            fontSize: '0.75rem',
            color: 'var(--text-primary)',
            lineHeight: 1.4
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontWeight: 700 }}>Arrival Window Diagnosis</span>
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: confidenceColor,
                textTransform: 'uppercase'
              }}
            >
              {confidence} confidence
            </span>
          </div>

          <p style={{ color: 'var(--text-secondary)', marginBottom: 6 }}>
            {delayExplanation}
          </p>

          {reasons && reasons.length > 0 && (
            <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', borderTop: '1px solid var(--border-subtle)', paddingTop: 4 }}>
              <strong>Factors:</strong> {reasons.join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
