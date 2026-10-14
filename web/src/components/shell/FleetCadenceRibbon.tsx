import React, { useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Radio } from 'lucide-react';

interface FleetCadenceRibbonProps {
  width?: number;
  height?: number;
  className?: string;
}

export const FleetCadenceRibbon: React.FC<FleetCadenceRibbonProps> = ({
  width = 130,
  height = 26,
  className
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { networkStress, isPlaying, speed, scenario, networkHealth, theme } = useSimulation();

  // Headway synchronicity score based on networkStress & scenario
  const syncScore = Math.max(
    45,
    Math.round(100 - networkStress * 42 - (scenario === 'S1' ? 14 : scenario === 'S2' ? 26 : scenario === 'S3' ? 18 : 0))
  );

  const statusColor =
    syncScore >= 80
      ? (theme === 'dark' ? '#10B981' : '#059669')
      : syncScore >= 65
      ? (theme === 'dark' ? '#F59E0B' : '#D97706')
      : (theme === 'dark' ? '#EF4444' : '#DC2626');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let tick = 0;

    // 4 route lines colors: R1 (Blue), R2 (Green), R3 (Violet), R4 (Amber)
    const routeColors = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B'];

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw subtle background slot guides (4 horizontal transit channels)
      const channelHeight = height / 4;
      routeColors.forEach((color, i) => {
        const y = i * channelHeight + channelHeight / 2;

        // Baseline track
        ctx.beginPath();
        ctx.strokeStyle = theme === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';
        ctx.lineWidth = 1;
        ctx.moveTo(4, y);
        ctx.lineTo(width - 4, y);
        ctx.stroke();

        // Calculate moving vehicle pulse position
        // When stress is high, bunching introduces phase perturbations
        const speedMultiplier = isPlaying ? (speed === 30 ? 1.5 : speed === 10 ? 0.9 : 0.4) : 0;
        const phaseOffset = (i * 0.28) + (scenario === 'S1' && i === 1 ? Math.sin(tick * 0.05) * 0.15 : 0);
        const progress = ((tick * speedMultiplier * 0.02 + phaseOffset) % 1);

        const x = 6 + progress * (width - 12);

        // Vehicle headway pulse (a bright capsule on the line)
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Trail glow
        const gradient = ctx.createLinearGradient(x - 14, y, x, y);
        gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
        gradient.addColorStop(1, color);
        ctx.fillStyle = gradient;
        ctx.fillRect(Math.max(4, x - 14), y - 1, 14, 2);
      });

      if (isPlaying) {
        tick += 1;
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, speed, scenario, theme, width, height]);

  return (
    <div
      className={`fleet-cadence-container ${className || ''}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '3px 10px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-color)',
        cursor: 'default',
        userSelect: 'none'
      }}
      title={`Fleet Cadence: ${syncScore}% Headway Regularity across R1–R4. Measures headway spacing and bunching risk.`}
    >
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Radio size={11} style={{ color: statusColor }} />
          <span
            style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em'
            }}
          >
            Fleet Cadence
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 1 }}>
          <span
            className="tabular-nums font-mono"
            style={{ fontSize: '0.78rem', fontWeight: 800, color: statusColor }}
          >
            {syncScore}%
          </span>
          <span
            style={{
              fontSize: '0.62rem',
              fontWeight: 600,
              color: 'var(--text-tertiary)'
            }}
          >
            {syncScore >= 80 ? 'Nominal' : syncScore >= 65 ? 'Bunching' : 'Disrupted'}
          </span>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ width: `${width}px`, height: `${height}px`, display: 'block' }}
      />
    </div>
  );
};
