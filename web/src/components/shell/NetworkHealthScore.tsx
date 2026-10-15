import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Info } from 'lucide-react';

export const NetworkHealthScore: React.FC = () => {
  const { networkHealth } = useSimulation();
  const [showTooltip, setShowTooltip] = useState(false);

  const bandBg =
    networkHealth.band === 'teal'
      ? 'var(--load-teal-bg)'
      : networkHealth.band === 'amber'
      ? 'var(--load-amber-bg)'
      : 'var(--load-coral-bg)';

  const bandBorder =
    networkHealth.band === 'teal'
      ? 'var(--load-teal-border)'
      : networkHealth.band === 'amber'
      ? 'var(--load-amber-border)'
      : 'var(--load-coral-border)';

  const bandColor =
    networkHealth.band === 'teal'
      ? 'var(--load-teal)'
      : networkHealth.band === 'amber'
      ? 'var(--load-amber)'
      : 'var(--load-coral)';

  return (
    <div
      style={{ position: 'relative' }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      <div
        className="health-badge"
        tabIndex={0}
        role="status"
        aria-label={`Network health ${networkHealth.score} out of 100`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 12px',
          borderRadius: 'var(--radius-full)',
          background: bandBg,
          border: `1px solid ${bandBorder}`,
          color: bandColor,
          cursor: 'help',
          userSelect: 'none',
          transition: 'var(--transition-fast)'
        }}
      >
        <span className="health-label" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Network health
        </span>
        <span
          className="tabular-nums font-display"
          style={{ fontSize: '1.05rem', fontWeight: 700, lineHeight: 1 }}
        >
          {networkHealth.score}
        </span>
      </div>

      {showTooltip && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: '320px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 100,
            color: 'var(--text-primary)',
            fontSize: '0.8rem',
            lineHeight: 1.45
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, marginBottom: 6 }}>
            <Info size={14} style={{ color: bandColor }} />
            <span>Network Health Formula</span>
          </div>

          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.7rem',
              background: 'var(--bg-surface-elevated)',
              padding: '6px 8px',
              borderRadius: 'var(--radius-xs)',
              marginBottom: 8,
              border: '1px solid var(--border-subtle)'
            }}
          >
            Health = max(0, 100<br />
            &nbsp; - 40 × (trips over cap)<br />
            &nbsp; - 30 × (left-behind share)<br />
            &nbsp; - 20 × (missed connection share)<br />
            &nbsp; - 10 × (delays &gt; 3 min))
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.74rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Over-capacity trips:</span>
              <span className="tabular-nums font-mono">{Math.round(networkHealth.overCapacityShare * 100)}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Left-behind share:</span>
              <span className="tabular-nums font-mono">{Math.round(networkHealth.leftBehindShare * 100)}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Missed connections:</span>
              <span className="tabular-nums font-mono">{Math.round(networkHealth.missedConnectionShare * 100)}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Delayed trips (&gt;3m):</span>
              <span className="tabular-nums font-mono">{Math.round(networkHealth.delayedTripsShare * 100)}%</span>
            </div>
          </div>

          <div
            style={{
              marginTop: 8,
              paddingTop: 6,
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '0.7rem',
              color: 'var(--text-tertiary)'
            }}
          >
            Bands: 80–100 Teal (Healthy), 60–79 Amber (Strained), &lt;60 Coral (Critical)
          </div>
        </div>
      )}
    </div>
  );
};
