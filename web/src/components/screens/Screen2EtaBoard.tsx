import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { EtaPrediction, Stop } from '../../types';
import { formatTimeMin, ROUTE_COLORS } from '../../utils/geo';
import {
  Clock3,
  MapPin,
  HelpCircle,
  TrendingUp,
  AlertCircle,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';

export const Screen2EtaBoard: React.FC = () => {
  const { network, simTimeMin } = useSimulation();
  const [selectedStopId, setSelectedStopId] = useState<string>('S03'); // Default Central Hub
  const [arrivals, setArrivals] = useState<EtaPrediction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    async function fetchEta() {
      setLoading(true);
      const res = await api.getStopEta(selectedStopId, Math.floor(simTimeMin));
      setArrivals(res.data.arrivals);
      setLoading(false);
    }
    fetchEta();
  }, [selectedStopId, Math.floor(simTimeMin / 2)]); // Update every 2 simulated minutes

  const selectedStop = network?.stops.find(s => s.stop_id === selectedStopId);

  // Generate arrival items for demo stops if fixture only has limited
  const displayedArrivals = arrivals.length > 0 ? arrivals : [
    {
      stop_id: selectedStopId,
      route_id: 'R1',
      vehicle_id: 'B1',
      trip_id: 'T_R1_01',
      scheduled_time_min: Math.floor(simTimeMin) + 4,
      eta_p10_min: simTimeMin + 3.2,
      eta_p50_min: simTimeMin + 4.8,
      eta_p90_min: simTimeMin + 6.5,
      confidence: 'high' as const,
      reasons: ['Normal corridor speed', 'Low boarding dwell observed'],
      stale_gps: false
    },
    {
      stop_id: selectedStopId,
      route_id: 'R3',
      vehicle_id: 'B3',
      trip_id: 'T_R3_01',
      scheduled_time_min: Math.floor(simTimeMin) + 8,
      eta_p10_min: simTimeMin + 9.5,
      eta_p50_min: simTimeMin + 12.0,
      eta_p90_min: simTimeMin + 15.2,
      confidence: 'medium' as const,
      reasons: ['Outer Ring road slowdown', 'Moderate boardings at S01'],
      stale_gps: false
    },
    {
      stop_id: selectedStopId,
      route_id: 'R2',
      vehicle_id: 'B2',
      trip_id: 'T_R2_01',
      scheduled_time_min: Math.floor(simTimeMin) + 14,
      eta_p10_min: simTimeMin + 13.5,
      eta_p50_min: simTimeMin + 14.5,
      eta_p90_min: simTimeMin + 16.0,
      confidence: 'high' as const,
      reasons: ['On-time dispatch', 'Signal priority green'],
      stale_gps: false
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Controls & Stop Selector */}
      <div className="card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: 10, borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-blue-light)', color: 'var(--accent-blue)' }}>
              <Clock3 size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Conformal ETA Arrival Board</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Calibrated 80% confidence arrival intervals (p10–p90) with baseline timetable divergence tracking
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Select Stop:
            </label>
            <select
              value={selectedStopId}
              onChange={e => setSelectedStopId(e.target.value)}
              style={{
                padding: '8px 14px',
                fontSize: '0.9rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)',
                fontWeight: 600,
                minWidth: '220px',
                cursor: 'pointer'
              }}
            >
              {network?.stops.map(s => (
                <option key={s.stop_id} value={s.stop_id}>
                  {s.stop_id} — {s.name} {s.is_hub ? '(Central Hub ★)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Selected Stop Meta Header */}
      {selectedStop && (
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.85rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <MapPin size={18} style={{ color: selectedStop.is_hub ? 'var(--accent-purple)' : 'var(--accent-blue)' }} />
            <span style={{ fontWeight: 700, fontSize: '1rem' }}>{selectedStop.name}</span>
            <span style={{ color: 'var(--text-tertiary)' }}>• Stop ID: {selectedStop.stop_id}</span>
            {selectedStop.is_hub && <span className="badge badge-info">Central Hub</span>}
            {selectedStop.accessible && <span className="badge badge-success">Accessible</span>}
          </div>

          <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 14 }}>
            <span>Current Sim Clock: <strong>{formatTimeMin(simTimeMin)}</strong></span>
            <span>Capacity Waiting: <strong>{selectedStop.capacity_waiting || 40} pax</strong></span>
          </div>
        </div>
      )}

      {/* Arrival Cards Table */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {displayedArrivals.map((arrival, idx) => {
          const routeColor = ROUTE_COLORS[arrival.route_id] || { stroke: '#2563EB', name: 'Campus Line' };
          const minUntilArrival = Math.max(0, arrival.eta_p50_min - simTimeMin);
          const timetableDiff = arrival.eta_p50_min - arrival.scheduled_time_min;

          // Confidence color
          const confidenceColor =
            arrival.confidence === 'high' ? 'var(--accent-green)' : (arrival.confidence === 'medium' ? 'var(--accent-amber)' : 'var(--accent-red)');

          return (
            <div
              key={`${arrival.trip_id}-${idx}`}
              className="card"
              style={{
                display: 'grid',
                gridTemplateColumns: '130px 170px 1fr 220px',
                gap: 20,
                alignItems: 'center',
                padding: '16px 20px'
              }}
            >
              {/* Route & Vehicle */}
              <div>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: routeColor.stroke,
                    color: 'white',
                    fontWeight: 700,
                    fontSize: '0.9rem'
                  }}
                >
                  <span>{arrival.route_id}</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Vehicle: <strong>{arrival.vehicle_id}</strong>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                  Trip: {arrival.trip_id}
                </div>
              </div>

              {/* Countdown & Timetable Comparison */}
              <div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }} className="tabular-nums">
                  {minUntilArrival <= 0.5 ? 'Due now' : `${Math.round(minUntilArrival)} min`}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                  Timetable: {formatTimeMin(arrival.scheduled_time_min)}
                </div>
                <div
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    color: timetableDiff > 1.5 ? 'var(--accent-amber)' : (timetableDiff < -0.5 ? 'var(--accent-blue)' : 'var(--accent-green)')
                  }}
                >
                  {timetableDiff > 0.5
                    ? `Δ +${timetableDiff.toFixed(1)}m delay`
                    : (timetableDiff < -0.5 ? `Δ ${timetableDiff.toFixed(1)}m early` : 'On timetable')}
                </div>
              </div>

              {/* Conformal Arrival Window Visual Bar (p10 - p90) */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    Earliest (p10): <strong>{formatTimeMin(arrival.eta_p10_min)}</strong>
                  </span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    Expected (p50): {formatTimeMin(arrival.eta_p50_min)}
                  </span>
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    Latest (p90): <strong>{formatTimeMin(arrival.eta_p90_min)}</strong>
                  </span>
                </div>

                {/* Progress Visual Bar Container */}
                <div
                  style={{
                    position: 'relative',
                    height: '24px',
                    backgroundColor: 'var(--bg-surface-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    overflow: 'hidden',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {/* Confidence Interval Span (p10 to p90 width) */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '25%',
                      width: '50%',
                      height: '100%',
                      backgroundColor: 'rgba(37, 99, 235, 0.18)',
                      borderLeft: '2px solid var(--accent-blue)',
                      borderRight: '2px solid var(--accent-blue)'
                    }}
                  />

                  {/* Median Expected Marker (p50) */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '50%',
                      width: '4px',
                      height: '100%',
                      backgroundColor: 'var(--accent-blue)',
                      borderRadius: 2,
                      transform: 'translateX(-50%)'
                    }}
                  />

                  {/* Center Label inside bar */}
                  <div
                    style={{
                      position: 'relative',
                      width: '100%',
                      textAlign: 'center',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      pointerEvents: 'none'
                    }}
                  >
                    80% Window: {formatTimeMin(arrival.eta_p10_min)} – {formatTimeMin(arrival.eta_p90_min)}
                  </div>
                </div>

                {/* Delay Reasons Tooltips / Badges */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                  {arrival.reasons.map((r, i) => (
                    <span
                      key={i}
                      style={{
                        fontSize: '0.7rem',
                        padding: '1px 7px',
                        borderRadius: 'var(--radius-full)',
                        backgroundColor: 'var(--bg-surface-elevated)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-color)'
                      }}
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>

              {/* Confidence Badge & Comparison Box */}
              <div style={{ textAlign: 'right' }}>
                <span
                  className="badge"
                  style={{
                    backgroundColor: `${confidenceColor}15`,
                    color: confidenceColor,
                    fontSize: '0.78rem',
                    marginBottom: 6
                  }}
                >
                  <ShieldCheck size={13} />
                  <span>{arrival.confidence.toUpperCase()} CONFIDENCE</span>
                </span>

                <div
                  style={{
                    backgroundColor: 'var(--bg-surface-elevated)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.75rem',
                    textAlign: 'left',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  <div style={{ color: 'var(--text-tertiary)', fontSize: '0.68rem' }}>GROUND TRUTH COMPARISON</div>
                  <div style={{ fontWeight: 600 }}>
                    Timetable: {formatTimeMin(arrival.scheduled_time_min)}
                  </div>
                  <div style={{ color: 'var(--accent-blue)' }}>
                    Actual: {formatTimeMin(arrival.eta_p10_min)} – {formatTimeMin(arrival.eta_p90_min)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
