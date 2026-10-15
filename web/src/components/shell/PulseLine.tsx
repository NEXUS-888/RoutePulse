import React, { useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';

interface PulseLineProps {
  width?: number;
  height?: number;
  className?: string;
}

export const PulseLine: React.FC<PulseLineProps> = ({ width = 120, height = 28, className }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { networkStress, isPlaying, speed, networkHealth, theme } = useSimulation();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Base line styling
      const strokeColor =
        networkHealth.band === 'teal'
          ? (theme === 'dark' ? '#3DD68C' : '#12713F')
          : networkHealth.band === 'amber'
          ? (theme === 'dark' ? '#FFB02E' : '#A85A00')
          : (theme === 'dark' ? '#FF5F52' : '#C4301F');

      ctx.lineWidth = 1.75;
      ctx.strokeStyle = strokeColor;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Soft glow in dark mode
      if (theme === 'dark') {
        ctx.shadowColor = strokeColor;
        ctx.shadowBlur = networkHealth.band === 'coral' ? 6 : 4;
      } else {
        ctx.shadowBlur = 0;
      }

      ctx.beginPath();
      const midY = height / 2;

      // Draw ECG-style waveform
      // Flat baseline -> P-wave -> Q-dip -> R-spike -> S-drop -> T-wave -> Flat
      const step = 2;
      for (let x = 0; x <= width; x += step) {
        // Position relative to moving cycle
        const cycleProgress = ((x + phase) % width) / width;
        let dy = 0;

        // Amplitude scales with network stress (0.1 to 1.0)
        const amp = (height * 0.42) * Math.max(0.2, networkStress);

        if (cycleProgress >= 0.35 && cycleProgress < 0.40) {
          // Small P-wave
          dy = -Math.sin(((cycleProgress - 0.35) / 0.05) * Math.PI) * (amp * 0.25);
        } else if (cycleProgress >= 0.40 && cycleProgress < 0.43) {
          // Q dip
          dy = Math.sin(((cycleProgress - 0.40) / 0.03) * Math.PI) * (amp * 0.18);
        } else if (cycleProgress >= 0.43 && cycleProgress < 0.48) {
          // Sharp R spike upwards
          dy = -Math.sin(((cycleProgress - 0.43) / 0.05) * Math.PI) * amp;
        } else if (cycleProgress >= 0.48 && cycleProgress < 0.52) {
          // S drop downwards
          dy = Math.sin(((cycleProgress - 0.48) / 0.04) * Math.PI) * (amp * 0.35);
        } else if (cycleProgress >= 0.55 && cycleProgress < 0.65) {
          // T wave
          dy = -Math.sin(((cycleProgress - 0.55) / 0.10) * Math.PI) * (amp * 0.3);
        }

        const y = midY + dy;
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      if (isPlaying) {
        // Beat rate scales slightly with speed
        phase += 0.8 + (speed === 30 ? 0.6 : speed === 10 ? 0.3 : 0.1);
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [networkStress, isPlaying, speed, networkHealth, theme, width, height]);

  return (
    <div
      className={`pulse-line-container ${className || ''}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '2px 8px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-color)',
        cursor: 'default'
      }}
      title={`Pulse Line: Network stress amplitude ${(networkStress * 100).toFixed(0)}% (reacts live to load and delays)`}
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ width: `${width}px`, height: `${height}px`, display: 'block' }}
      />
    </div>
  );
};
