import React, { useState, useRef, useCallback } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { ShieldCheck, ArrowLeftRight, TrendingDown } from 'lucide-react';

export const BeforeAfterSlider: React.FC = () => {
  const [sliderPos, setSliderPos] = useState<number>(50); // percentage 0 to 100
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const handlePointerDown = () => {
    setIsDragging(true);
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
      setSliderPos(Math.round((x / rect.width) * 100));
    },
    [isDragging]
  );

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Slider Hero Container */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        style={{
          position: 'relative',
          width: '100%',
          height: '380px',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          border: '1px solid var(--border-color)',
          userSelect: 'none',
          cursor: 'ew-resize',
          background: 'var(--bg-surface)'
        }}
      >
        {/* Left Half: Baseline-0 (Coral Overcrowded) */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(ellipse at 30% 60%, rgba(239, 68, 68, 0.18), transparent 70%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: 20
          }}
        >
          {/* Label Badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--load-coral-bg)',
                border: '1px solid var(--load-coral-border)',
                color: 'var(--load-coral)',
                fontWeight: 700,
                fontSize: '0.78rem',
                textTransform: 'uppercase'
              }}
            >
              Baseline-0 Plan (Static Timetable)
            </span>
          </div>

          {/* Schematic Preview Representation */}
          <svg viewBox="0 0 500 240" style={{ width: '80%', height: 'auto', alignSelf: 'center' }}>
            {/* Route R3 Overloaded */}
            <path
              d="M 60 180 L 160 120 L 260 120 L 380 60"
              fill="none"
              stroke="var(--load-coral)"
              strokeWidth="7"
              strokeLinecap="round"
            />
            {/* Passenger Overcrowding Clusters */}
            <circle cx="160" cy="120" r="14" fill="var(--load-coral)" opacity="0.8" />
            <text x="160" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="10" fontWeight="700">62</text>
            <text x="160" y="146" textAnchor="middle" fill="var(--load-coral)" fontSize="10" fontWeight="700">Left Behind</text>

            <circle cx="260" cy="120" r="10" fill="var(--load-coral)" opacity="0.6" />
            <text x="260" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="700">134%</text>
            <text x="260" y="144" textAnchor="middle" fill="var(--load-coral)" fontSize="9" fontWeight="600">Overload</text>
          </svg>

          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--load-coral)', fontWeight: 600 }}>
              ⚠ Severe passenger bunching on R3 • 62 riders left behind • Health: 58 (Coral)
            </span>
          </div>
        </div>

        {/* Right Half: RoutePulse Optimized (Clipped by slider position) */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            clipPath: `polygon(${sliderPos}% 0, 100% 0, 100% 100%, ${sliderPos}% 100%)`,
            background: 'radial-gradient(ellipse at 70% 60%, rgba(16, 185, 129, 0.16), transparent 70%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: 20,
            borderLeft: '1px solid var(--border-color)'
          }}
        >
          {/* Label Badge */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--load-teal-bg)',
                border: '1px solid var(--load-teal-border)',
                color: 'var(--load-teal)',
                fontWeight: 700,
                fontSize: '0.78rem',
                textTransform: 'uppercase'
              }}
            >
              RoutePulse Optimized (+B5 Reserve Inserted)
            </span>
          </div>

          {/* Schematic Preview Representation */}
          <svg viewBox="0 0 500 240" style={{ width: '80%', height: 'auto', alignSelf: 'center' }}>
            {/* Route R3 Balanced */}
            <path
              d="M 60 180 L 160 120 L 260 120 L 380 60"
              fill="none"
              stroke="var(--load-teal)"
              strokeWidth="5"
              strokeLinecap="round"
            />
            {/* Smooth flow */}
            <circle cx="160" cy="120" r="10" fill="var(--load-teal)" opacity="0.8" />
            <text x="160" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="700">21</text>
            <text x="160" y="144" textAnchor="middle" fill="var(--load-teal)" fontSize="9" fontWeight="700">-41 Pax</text>

            <circle cx="260" cy="120" r="10" fill="var(--load-teal)" opacity="0.8" />
            <text x="260" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="700">82%</text>
            <text x="260" y="144" textAnchor="middle" fill="var(--load-teal)" fontSize="9" fontWeight="600">Optimal</text>
          </svg>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--load-teal)', fontWeight: 600 }}>
              ✓ Smooth headway • 0 hard violations • Health: 94 (Teal)
            </span>
          </div>
        </div>

        {/* Draggable Divider Handle */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${sliderPos}%`,
            width: '2px',
            background: 'var(--text-primary)',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
            zIndex: 10,
            boxShadow: '0 0 10px rgba(0,0,0,0.5)'
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'var(--bg-surface)',
              border: '2px solid var(--text-primary)',
              boxShadow: 'var(--shadow-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-primary)'
            }}
          >
            <ArrowLeftRight size={14} />
          </div>
        </div>
      </div>

      {/* KPI Comparison Matrix */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 12
        }}
      >
        <div className="card" style={{ padding: '12px 14px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Mean Passenger Wait
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
            <span className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              5.4 min
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textDecoration: 'line-through' }}>
              7.2m
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--load-teal)', fontWeight: 600 }}>
            -1.8 min (-25%)
          </span>
        </div>

        <div className="card" style={{ padding: '12px 14px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Left-Behind Riders
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
            <span className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              21 pax
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textDecoration: 'line-through' }}>
              62p
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--load-teal)', fontWeight: 600 }}>
            -41 pax (-66%)
          </span>
        </div>

        <div className="card" style={{ padding: '12px 14px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Missed Connections
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
            <span className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              11 pax
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textDecoration: 'line-through' }}>
              28p
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--load-teal)', fontWeight: 600 }}>
            -17 pax (-61%)
          </span>
        </div>

        <div className="card" style={{ padding: '12px 14px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Hard Violations (Gate)
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
            <span className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              0
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              (H1–H12 Passed)
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--load-teal)', fontWeight: 600 }}>
            ✓ Verified by Solver
          </span>
        </div>
      </div>
    </div>
  );
};
