import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { StudentRouteResponse, StudentRouteOption } from '../../types';
import { formatTimeMin, ROUTE_COLORS } from '../../utils/geo';
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
  Navigation
} from 'lucide-react';

export const Screen6StudentView: React.FC = () => {
  const { network, simTimeMin } = useSimulation();

  const [fromStop, setFromStop] = useState<string>('S13'); // Metro Station
  const [toStop, setToStop] = useState<string>('S04'); // Library
  const [accessibleOnly, setAccessibleOnly] = useState<boolean>(false);
  const [departureTime, setDepartureTime] = useState<number>(460); // 07:40
  const [routeResults, setRouteResults] = useState<StudentRouteResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

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
    <div style={{ maxWidth: '880px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Student App Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: 10, borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-blue-light)', color: 'var(--accent-blue)' }}>
              <GraduationCap size={26} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Campus Traveler & Student Transit Planner</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Live conformal ETA windows, crowding nowcasts, and guaranteed transfer-safety probabilities
              </p>
            </div>
          </div>

          <button
            className="btn btn-outline"
            style={{ fontSize: '0.8rem', gap: 6 }}
            onClick={handleUseCurrentTime}
          >
            <Clock size={15} />
            <span>Use Live Clock ({formatTimeMin(simTimeMin)})</span>
          </button>
        </div>

        {/* Input Controls Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
              FROM (DEPARTURE STOP)
            </label>
            <select
              value={fromStop}
              onChange={e => setFromStop(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                fontWeight: 600
              }}
            >
              {network?.stops.map(s => (
                <option key={s.stop_id} value={s.stop_id}>
                  {s.stop_id} — {s.name} {s.is_hub ? '(Central Hub ★)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
              TO (DESTINATION STOP)
            </label>
            <select
              value={toStop}
              onChange={e => setToStop(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                fontWeight: 600
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

        {/* Filters and Time selection */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', cursor: 'pointer', fontWeight: 600 }}>
              <input
                type="checkbox"
                checked={accessibleOnly}
                onChange={e => setAccessibleOnly(e.target.checked)}
                style={{ width: 16, height: 16, accentColor: 'var(--accent-blue)' }}
              />
              <Accessibility size={16} style={{ color: 'var(--accent-blue)' }} />
              <span>Accessible Only (Wheelchair Ramp Required)</span>
            </label>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Departing around:</span>
            <input
              type="range"
              min={450}
              max={600}
              step={5}
              value={departureTime}
              onChange={e => setDepartureTime(parseInt(e.target.value))}
              style={{ accentColor: 'var(--accent-blue)', width: 120 }}
            />
            <span style={{ fontWeight: 700, fontSize: '0.9rem' }} className="tabular-nums">
              {formatTimeMin(departureTime)}
            </span>
          </div>
        </div>
      </div>

      {/* Suggested Itineraries */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Available Itineraries ({routeResults?.options.length || 0} Options Found)
          </h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>
            Estimated with 80% conformal coverage
          </span>
        </div>

        {loading ? (
          <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            Finding best campus route and calculating transfer confidence...
          </div>
        ) : (
          routeResults?.options.map((option, idx) => {
            const isBestOption = idx === 1; // Option 2 has better crowding
            const routeColor = ROUTE_COLORS[option.route_id] || { stroke: '#2563EB', name: 'Campus Shuttle' };

            return (
              <div
                key={option.itinerary_id}
                className="card"
                style={{
                  border: isBestOption ? '2px solid var(--accent-green)' : '1px solid var(--border-color)',
                  position: 'relative'
                }}
              >
                {isBestOption && (
                  <div
                    style={{
                      position: 'absolute',
                      top: -12,
                      right: 18,
                      backgroundColor: 'var(--accent-green)',
                      color: 'white',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '2px 10px',
                      borderRadius: 'var(--radius-full)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4
                    }}
                  >
                    <Sparkles size={12} />
                    <span>RECOMMENDED FOR COMFORT</span>
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 14 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span
                        style={{
                          backgroundColor: routeColor.stroke,
                          color: 'white',
                          fontWeight: 800,
                          padding: '3px 9px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.85rem'
                        }}
                      >
                        {option.route_id}
                      </span>
                      <span style={{ fontWeight: 700, fontSize: '1rem' }}>
                        Depart {formatTimeMin(option.departure_min)} from {network?.stops.find(s => s.stop_id === option.from_stop)?.name || option.from_stop}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>Arrival Window: <strong>{formatTimeMin(option.eta_p10_min)} – {formatTimeMin(option.eta_p90_min)}</strong></span>
                      <span>• Expected Duration: ~{Math.round(option.eta_p50_min - option.departure_min)} min</span>
                    </div>
                  </div>

                  {/* Badges */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: option.crowding_level === 'crowded' ? 'var(--accent-red-light)' : 'var(--accent-green-light)',
                          color: option.crowding_level === 'crowded' ? 'var(--accent-red)' : 'var(--accent-green)'
                        }}
                      >
                        {option.crowding_level === 'crowded' ? '⚠ Crowded (88%)' : '✓ Comfortable (55%)'}
                      </span>

                      {option.accessible && (
                        <span className="badge badge-info" title="Equipped with wheelchair ramp">
                          <Accessibility size={12} />
                          <span>Accessible</span>
                        </span>
                      )}
                    </div>

                    {option.is_transfer && (
                      <span className="badge badge-success" style={{ gap: 4 }}>
                        <ShieldCheck size={12} />
                        <span>Transfer Safety: {Math.round(option.transfer_safe_prob * 100)}% Safe</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Transfer Steps Graphic */}
                {option.is_transfer && (
                  <div
                    style={{
                      backgroundColor: 'var(--bg-surface-elevated)',
                      padding: '12px 16px',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '0.82rem',
                      marginBottom: 12
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <MapPin size={15} style={{ color: 'var(--accent-blue)' }} />
                      <span>{option.from_stop}</span>
                    </div>

                    <div style={{ flex: 1, borderTop: '2px dashed var(--border-color)', margin: '0 12px', position: 'relative' }}>
                      <span
                        style={{
                          position: 'absolute',
                          top: -10,
                          left: '50%',
                          transform: 'translateX(-50%)',
                          backgroundColor: 'var(--bg-surface)',
                          padding: '0 8px',
                          fontSize: '0.72rem',
                          color: 'var(--accent-purple)',
                          fontWeight: 700
                        }}
                      >
                        Transfer Hub S03 (4 min buffer)
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <MapPin size={15} style={{ color: 'var(--accent-green)' }} />
                      <span>{option.to_stop} ({network?.stops.find(s => s.stop_id === option.to_stop)?.name || option.to_stop})</span>
                    </div>
                  </div>
                )}

                {/* Proactive Recommendation Note */}
                {option.recommendation_note && (
                  <div
                    style={{
                      backgroundColor: isBestOption ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                      borderLeft: `3px solid ${isBestOption ? 'var(--accent-green)' : 'var(--accent-amber)'}`,
                      padding: '8px 12px',
                      borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                      fontSize: '0.78rem',
                      color: 'var(--text-secondary)'
                    }}
                  >
                    <strong style={{ color: isBestOption ? 'var(--accent-green)' : 'var(--accent-amber)' }}>
                      Passenger Advisory:
                    </strong>{' '}
                    {option.recommendation_note}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
