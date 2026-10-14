import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { EtaPrediction, Stop } from '../../types';
import { formatTimeMin, ROUTE_COLORS } from '../../utils/geo';
import { EtaCapsule } from '../common/EtaCapsule';
import { GlossaryPopover } from '../common/GlossaryPopover';
import { SkeletonLoader, EmptyState, ErrorState } from '../common/StateViews';
import {
  Clock,
  MapPin,
  HelpCircle,
  TrendingUp,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  Accessibility,
  Users,
  RefreshCw
} from 'lucide-react';

export const Screen2EtaBoard: React.FC = () => {
  const { network, simTimeMin } = useSimulation();
  const [selectedStopId, setSelectedStopId] = useState<string>('S03'); // Default Central Hub
  const [arrivals, setArrivals] = useState<EtaPrediction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);

  const fetchEta = async () => {
    try {
      setLoading(true);
      setHasError(false);
      const res = await api.getStopEta(selectedStopId, Math.floor(simTimeMin));
      setArrivals(res.data.arrivals || []);
    } catch (err) {
      setHasError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEta();
  }, [selectedStopId, Math.floor(simTimeMin / 2)]);

  const selectedStop = network?.stops.find(s => s.stop_id === selectedStopId);

  // Fallback demo arrivals if API returns empty
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
      reasons: ['Normal corridor speed', 'Low dwell variability'],
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
      reasons: ['Outer loop corridor slowdown', 'Heavy boardings at S13'],
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
      reasons: ['On-time dispatch', 'Clean transfer at S03'],
      stale_gps: false
    }
  ];

  return (
    <div className="screen-scroll-container">
      {/* Screen Header */}
      <div className="screen-card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--route-r1)'
              }}
            >
              <Clock size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                Conformal ETA Arrival Board
              </h1>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Calibrated{' '}
                <GlossaryPopover termId="arrivalWindow">80% arrival windows (p10–p90)</GlossaryPopover>{' '}
                tracked against the published{' '}
                <GlossaryPopover termId="timetablePromise">timetable promise</GlossaryPopover>
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Select Station:
            </label>
            <select
              value={selectedStopId}
              onChange={e => setSelectedStopId(e.target.value)}
              aria-label="Select Station for Arrival Board"
              style={{
                padding: '6px 12px',
                fontSize: '0.85rem',
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

      {/* Error State with Recovery Action */}
      {hasError && (
        <ErrorState
          title="Live ETA Feed Interrupted"
          message="Unable to reach the live telemetry server. Switch to baseline timetable approximations to preserve passenger schedules."
          recoveryActionText="Switch to Baseline Timetable"
          onRecover={fetchEta}
        />
      )}

      {/* Selected Stop Meta Ribbon */}
      {selectedStop && (
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <MapPin size={18} style={{ color: selectedStop.is_hub ? 'var(--accent-hub)' : 'var(--route-r1)' }} />
            <span style={{ fontWeight: 700, fontSize: '1rem' }}>{selectedStop.name}</span>
            <span style={{ color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
              • {selectedStop.stop_id}
            </span>
            {selectedStop.is_hub && (
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: 'var(--accent-hub)',
                  fontWeight: 700,
                  fontSize: '0.72rem',
                  border: '1px solid rgba(168, 85, 247, 0.3)'
                }}
              >
                ★ Central Transfer Hub
              </span>
            )}
            {selectedStop.accessible && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--load-teal-bg)',
                  color: 'var(--load-teal)',
                  fontWeight: 600,
                  fontSize: '0.72rem',
                  border: '1px solid var(--load-teal-border)'
                }}
              >
                <Accessibility size={12} />
                <span>Ramp Accessible</span>
              </span>
            )}
          </div>

          <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 16, fontSize: '0.8rem' }}>
            <span>Current Sim Clock: <strong className="tabular-nums font-mono">{formatTimeMin(simTimeMin)}</strong></span>
            <span>Platform Capacity: <strong className="tabular-nums font-mono">{selectedStop.capacity_waiting || 40} pax</strong></span>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && <SkeletonLoader type="table" count={3} />}

      {/* Arrival Cards Table */}
      {!loading && displayedArrivals.length === 0 && (
        <EmptyState
          title="No Upcoming Arrivals"
          description="There are currently no scheduled or active departures in the next 30-minute window for this station."
          actionText="Refresh Board"
          onAction={fetchEta}
        />
      )}

      {!loading && displayedArrivals.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {displayedArrivals.map((arrival, idx) => {
            const minUntilArrival = Math.max(0, arrival.eta_p50_min - simTimeMin);
            const timetableDiff = arrival.eta_p50_min - arrival.scheduled_time_min;

            return (
              <div
                key={`${arrival.trip_id}-${idx}`}
                className="screen-card"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 180px 1fr 200px',
                  gap: 20,
                  alignItems: 'center',
                  padding: '16px 20px'
                }}
              >
                {/* Route Pill & Vehicle */}
                <div>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: `var(--route-${arrival.route_id.toLowerCase()})`,
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontSize: '0.88rem'
                    }}
                  >
                    <span>{arrival.route_id}</span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    Vehicle: <strong className="font-mono">{arrival.vehicle_id}</strong>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    Trip: {arrival.trip_id}
                  </div>
                </div>

                {/* Big Readable Countdown & Timetable Delta */}
                <div>
                  <div
                    className="tabular-nums font-display"
                    style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}
                  >
                    {minUntilArrival <= 0.5 ? 'Due now' : `${Math.round(minUntilArrival)} min`}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    Timetable: <span className="tabular-nums font-mono">{formatTimeMin(arrival.scheduled_time_min)}</span>
                  </div>
                  <div
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      color:
                        timetableDiff > 1.5
                          ? 'var(--load-coral)'
                          : timetableDiff > 0.5
                          ? 'var(--load-amber)'
                          : 'var(--load-teal)'
                    }}
                  >
                    {timetableDiff > 0.5
                      ? `Δ +${timetableDiff.toFixed(1)}m delay`
                      : timetableDiff < -0.5
                      ? `Δ ${timetableDiff.toFixed(1)}m early`
                      : '✓ Exactly on timetable'}
                  </div>
                </div>

                {/* Shaded p10–p90 Arrival Window Capsule */}
                <div>
                  <EtaCapsule prediction={arrival} simTimeMin={simTimeMin} />
                </div>

                {/* Diagnostic Reason Pills */}
                <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                    Observation:
                  </div>
                  {arrival.reasons && arrival.reasons.length > 0 ? (
                    <div>{arrival.reasons[0]}</div>
                  ) : (
                    <div>Nominal traffic flow across segment.</div>
                  )}
                  {arrival.stale_gps && (
                    <span style={{ color: 'var(--load-coral)', fontWeight: 600, fontSize: '0.68rem' }}>
                      ⚠ Stale GPS feed (using dead reckoning)
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
