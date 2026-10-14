import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { StudentRouteResponse, StudentRouteOption } from '../../types';
import { formatTimeMin, ROUTE_COLORS } from '../../utils/geo';
import { GlossaryPopover } from '../common/GlossaryPopover';
import { SkeletonLoader, EmptyState } from '../common/StateViews';
import {
  GraduationCap,
  ArrowRight,
  Accessibility,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  MapPin,
  CheckCircle2,
  Navigation,
  Smartphone,
  Maximize2
} from 'lucide-react';

export const Screen6StudentView: React.FC = () => {
  const { network, simTimeMin } = useSimulation();

  const [fromStop, setFromStop] = useState<string>('S13'); // Metro Gateway
  const [toStop, setToStop] = useState<string>('S04'); // Library
  const [accessibleOnly, setAccessibleOnly] = useState<boolean>(false);
  const [departureTime, setDepartureTime] = useState<number>(460); // 07:40
  const [routeResults, setRouteResults] = useState<StudentRouteResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isMobileFrame, setIsMobileFrame] = useState<boolean>(true);

  const searchRoutes = async () => {
    setLoading(true);
    const res = await api.getStudentRoute(fromStop, toStop, departureTime, accessibleOnly);
    setRouteResults(res.data);
    setLoading(false);
  };

  useEffect(() => {
    searchRoutes();
  }, [fromStop, toStop, accessibleOnly, departureTime]);

  const handleUseCurrentTime = () => {
    setDepartureTime(Math.floor(simTimeMin));
  };

  return (
    <div className="screen-scroll-container" style={{ alignItems: 'center' }}>
      {/* Top Toggle: Mobile 390x844 Frame vs Expanded */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', maxWidth: '820px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--route-r1)'
            }}
          >
            <GraduationCap size={20} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Student & Traveler Route Planner</h1>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Mobile-first passenger guidance with large arrival windows, transfer guarantees, and crowding alerts
            </p>
          </div>
        </div>

        <button
          className="btn"
          onClick={() => setIsMobileFrame(prev => !prev)}
          title="Toggle Mobile Simulator Frame (390×844)"
          style={{ gap: 6, fontSize: '0.76rem' }}
        >
          {isMobileFrame ? <Maximize2 size={13} /> : <Smartphone size={13} />}
          <span>{isMobileFrame ? 'Expand Full View' : 'Mobile Frame (390×844)'}</span>
        </button>
      </div>

      {/* Main Container (Mobile 390x844 frame or Expanded) */}
      <div
        style={{
          width: isMobileFrame ? '390px' : '100%',
          maxWidth: isMobileFrame ? '390px' : '820px',
          minHeight: isMobileFrame ? '760px' : 'auto',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: isMobileFrame ? '36px' : 'var(--radius-md)',
          boxShadow: isMobileFrame ? '0 20px 40px rgba(0,0,0,0.45)' : 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Mobile Device Status Bar */}
        {isMobileFrame && (
          <div
            style={{
              padding: '12px 20px 6px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.74rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              borderBottom: '1px solid var(--border-subtle)'
            }}
          >
            <span>{formatTimeMin(simTimeMin)}</span>
            <div style={{ width: 80, height: 16, borderRadius: 8, background: 'var(--bg-hover)' }} />
            <span>5G 100%</span>
          </div>
        )}

        {/* Mobile Header: App Title & Origin / Destination Form */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span className="font-display" style={{ fontWeight: 800, fontSize: '1rem', letterSpacing: '-0.02em' }}>
              RoutePulse Go
            </span>
            <button
              className="btn btn-outline"
              onClick={handleUseCurrentTime}
              style={{ padding: '2px 8px', fontSize: '0.72rem', gap: 4 }}
            >
              <Clock size={12} />
              <span>Now ({formatTimeMin(simTimeMin)})</span>
            </button>
          </div>

          {/* From / To Inputs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                Origin Station
              </label>
              <select
                value={fromStop}
                onChange={e => setFromStop(e.target.value)}
                aria-label="Origin Station"
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  color: 'var(--text-primary)',
                  fontSize: '0.84rem',
                  fontWeight: 600
                }}
              >
                {network?.stops.map(s => (
                  <option key={s.stop_id} value={s.stop_id}>
                    {s.stop_id} — {s.name} {s.is_hub ? '★' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                Destination Station
              </label>
              <select
                value={toStop}
                onChange={e => setToStop(e.target.value)}
                aria-label="Destination Station"
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  color: 'var(--text-primary)',
                  fontSize: '0.84rem',
                  fontWeight: 600
                }}
              >
                {network?.stops.map(s => (
                  <option key={s.stop_id} value={s.stop_id}>
                    {s.stop_id} — {s.name} {s.is_hub ? '★' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Accessibility Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', cursor: 'pointer', fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={accessibleOnly}
                  onChange={e => setAccessibleOnly(e.target.checked)}
                  style={{ accentColor: 'var(--load-teal)' }}
                />
                <Accessibility size={14} style={{ color: 'var(--load-teal)' }} />
                <span>Ramp Shuttles Only</span>
              </label>

              <span className="font-mono tabular-nums" style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                Dep: {formatTimeMin(departureTime)}
              </span>
            </div>
          </div>
        </div>

        {/* Itinerary Bottom-Sheet Feed */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
              Suggested Itineraries
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--load-teal)', fontWeight: 600 }}>
              80% Window Coverage
            </span>
          </div>

          {loading ? (
            <SkeletonLoader type="card" count={2} />
          ) : !routeResults || routeResults.options.length === 0 ? (
            <EmptyState
              title="No Direct Route Found"
              description="Try adjusting your departure station or uncheck ramp filter."
            />
          ) : (
            routeResults.options.map((option, idx) => {
              const isBestOption = idx === 1;
              const isCrowded = option.crowding_level === 'crowded';
              const durationMin = Math.round(option.eta_p50_min - option.departure_min);

              return (
                <div
                  key={option.itinerary_id}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: `1.5px solid ${isBestOption ? 'var(--load-teal)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    position: 'relative'
                  }}
                >
                  {isBestOption && (
                    <div
                      style={{
                        position: 'absolute',
                        top: -10,
                        right: 14,
                        background: 'var(--load-teal)',
                        color: '#FFFFFF',
                        fontSize: '0.66rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 3
                      }}
                    >
                      <Sparkles size={11} />
                      <span>RECOMMENDED FOR SEATS</span>
                    </div>
                  )}

                  {/* Route & Departure Header */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          padding: '2px 7px',
                          borderRadius: 'var(--radius-xs)',
                          background: `var(--route-${option.route_id.toLowerCase()})`,
                          color: '#FFFFFF',
                          fontWeight: 700,
                          fontSize: '0.78rem'
                        }}
                      >
                        {option.route_id}
                      </span>
                      <span style={{ fontSize: '0.84rem', fontWeight: 700 }}>
                        Depart {formatTimeMin(option.departure_min)}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      ~{durationMin} min trip
                    </span>
                  </div>

                  {/* Large ETA Window (p50 Big, Window Smaller) */}
                  <div
                    style={{
                      background: 'var(--bg-surface)',
                      borderRadius: 'var(--radius-xs)',
                      padding: '10px 12px',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
                        Expected Arrival (p50)
                      </span>
                      <div className="font-display tabular-nums" style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
                        {formatTimeMin(option.eta_p50_min)}
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
                        Arrival Window (80%)
                      </span>
                      <div className="font-mono tabular-nums" style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--load-teal)' }}>
                        {formatTimeMin(option.eta_p10_min)} – {formatTimeMin(option.eta_p90_min)}
                      </div>
                    </div>
                  </div>

                  {/* Transfer-Safe Indicator */}
                  {option.is_transfer && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.72rem',
                        color: 'var(--text-secondary)',
                        padding: '4px 8px',
                        borderRadius: 'var(--radius-xs)',
                        background: 'rgba(168, 85, 247, 0.1)'
                      }}
                    >
                      <span>Hub S03 Transfer (4m buffer):</span>
                      <strong style={{ color: 'var(--accent-hub)' }}>
                        {Math.round(option.transfer_safe_prob * 100)}% Safe Connection
                      </strong>
                    </div>
                  )}

                  {/* Crowding Warning & Later Alternative */}
                  {isCrowded ? (
                    <div
                      style={{
                        padding: '8px 10px',
                        borderRadius: 'var(--radius-xs)',
                        background: 'var(--load-coral-bg)',
                        border: '1px solid var(--load-coral-border)',
                        fontSize: '0.74rem',
                        lineHeight: 1.4
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--load-coral)', fontWeight: 700 }}>
                        <AlertTriangle size={13} />
                        <span>Next bus is crowded (92% load)</span>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                        Alternative departure 8 min later is predicted <strong>58% full</strong>.
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.72rem', color: 'var(--load-teal)', fontWeight: 600 }}>
                      ✓ Comfortable seating available (&lt;60% load)
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
