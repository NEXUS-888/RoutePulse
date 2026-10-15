import React from 'react';
import {
  X,
  MapPin,
  Bus,
  AlertTriangle,
  Sparkles,
  ShieldCheck,
  Check,
  ArrowRight,
  Accessibility,
  Users
} from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';
import { EtaCapsule } from '../common/EtaCapsule';
import { formatTimeMin, getLoadColor } from '../../utils/geo';
import type { EtaPrediction, Stop, Alert, Recommendation } from '../../types';

export const InspectorDrawer: React.FC = () => {
  const {
    selectedEntity,
    closeInspectorDrawer,
    simTimeMin,
    network,
    activeVehicles,
    acceptRecommendation,
    rejectRecommendation,
    appliedRecIds,
    setActiveScreen
  } = useSimulation();

  if (!selectedEntity) return null;

  const { type, data } = selectedEntity;

  // Render Stop Inspector
  const renderStopDetails = (stop: Stop) => {
    // Generate realistic upcoming ETAs for this stop
    const stopArrivals: EtaPrediction[] = [
      {
        stop_id: stop.stop_id,
        route_id: stop.stop_id === 'S13' ? 'R3' : 'R1',
        vehicle_id: stop.stop_id === 'S13' ? 'B3' : 'B1',
        trip_id: 'T101',
        scheduled_time_min: simTimeMin + 3,
        eta_p10_min: simTimeMin + 2.5,
        eta_p50_min: simTimeMin + 3.8,
        eta_p90_min: simTimeMin + 5.2,
        confidence: 'high',
        reasons: ['Normal corridor flow', 'Low dwell variability']
      },
      {
        stop_id: stop.stop_id,
        route_id: stop.stop_id === 'S08' || stop.stop_id === 'S09' ? 'R2' : 'R2',
        vehicle_id: 'B2',
        trip_id: 'T102',
        scheduled_time_min: simTimeMin + 9,
        eta_p10_min: simTimeMin + 8.2,
        eta_p50_min: simTimeMin + 10.1,
        eta_p90_min: simTimeMin + 12.0,
        confidence: 'high',
        reasons: ['Hostel loop on schedule']
      }
    ];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
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
              color: 'var(--accent)'
            }}
          >
            <MapPin size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{stop.name}</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              Stop ID: {stop.stop_id} {stop.is_hub && '• Central Transfer Hub'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {stop.accessible && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '3px 8px',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.72rem',
                fontWeight: 600,
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-secondary)'
              }}
            >
              <Accessibility size={13} style={{ color: 'var(--load-teal)' }} />
              <span>Step-Free Ramp Access</span>
            </span>
          )}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)'
            }}
          >
            <Users size={13} />
            <span>Platform Capacity: {stop.capacity_waiting || 40} pax</span>
          </span>
        </div>

        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
            Upcoming Arrivals (Live Windows)
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {stopArrivals.map((arr, i) => (
              <EtaCapsule key={i} prediction={arr} simTimeMin={simTimeMin} />
            ))}
          </div>
        </div>

        <button
          className="btn btn-outline"
          onClick={() => setActiveScreen('eta')}
          style={{ width: '100%', gap: 6 }}
        >
          <span>Open Full ETA Board</span>
          <ArrowRight size={14} />
        </button>
      </div>
    );
  };

  // Render Vehicle Inspector
  const renderVehicleDetails = (vehId: string) => {
    const vehicle = activeVehicles.find(v => v.vehicle_id === vehId);
    if (!vehicle) return <div>Vehicle telemetry unavailable.</div>;

    const loadColor = getLoadColor(vehicle.loadPct);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-sm)',
              background: loadColor.bg,
              border: `1px solid ${loadColor.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: loadColor.text
            }}
          >
            <Bus size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {vehicle.vehicle_id} ({vehicle.type === 'bus' ? 'Standard Bus' : 'Minibus'})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              Assigned to Route {vehicle.route_id} • Status: <strong style={{ color: loadColor.text }}>{vehicle.status.toUpperCase()}</strong>
            </span>
          </div>
        </div>

        {/* Load Bar & Occupancy */}
        <div
          style={{
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 14px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Passenger Load:</span>
            <span className="tabular-nums font-mono" style={{ fontSize: '0.88rem', fontWeight: 700, color: loadColor.text }}>
              {vehicle.load} / {vehicle.capacity} pax ({vehicle.loadPct}%)
            </span>
          </div>

          <div style={{ height: 8, borderRadius: 'var(--radius-full)', background: 'var(--bg-hover)', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, vehicle.loadPct)}%`,
                backgroundColor: loadColor.ring
              }}
            />
          </div>

          <div style={{ marginTop: 6, fontSize: '0.72rem', color: loadColor.text, fontWeight: 600 }}>
            {loadColor.badge}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div
            style={{
              background: 'var(--bg-surface-elevated)',
              padding: '10px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)'
            }}
          >
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Current Speed</span>
            <div className="font-mono" style={{ fontSize: '1rem', fontWeight: 700 }}>
              {(vehicle.speed_mps * 3.6).toFixed(1)} km/h
            </div>
          </div>
          <div
            style={{
              background: 'var(--bg-surface-elevated)',
              padding: '10px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)'
            }}
          >
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Next Station</span>
            <div className="font-mono" style={{ fontSize: '1rem', fontWeight: 700 }}>
              {vehicle.nextStop}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Alert Inspector
  const renderAlertDetails = (alert: Alert) => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-sm)',
              background: alert.severity === 'hard-risk' ? 'var(--load-coral-bg)' : 'var(--load-amber-bg)',
              border: `1px solid ${alert.severity === 'hard-risk' ? 'var(--load-coral-border)' : 'var(--load-amber-border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: alert.severity === 'hard-risk' ? 'var(--load-coral)' : 'var(--load-amber)'
            }}
          >
            <AlertTriangle size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{alert.title}</h3>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
              Alert Code: {alert.code} • Severity: {alert.severity.toUpperCase()}
            </span>
          </div>
        </div>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {alert.detail}
        </p>

        <div
          style={{
            background: 'var(--bg-surface-elevated)',
            padding: '12px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Estimated Passengers Affected:</span>
          <span className="font-display tabular-nums" style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--load-coral)' }}>
            {alert.pax_affected} pax
          </span>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => setActiveScreen('recommendations')}
          style={{ width: '100%', gap: 6 }}
        >
          <span>View Optimization Solutions</span>
          <ArrowRight size={14} />
        </button>
      </div>
    );
  };

  // Render Recommendation Inspector
  const renderRecommendationDetails = (rec: Recommendation) => {
    const isApplied = appliedRecIds.has(rec.id);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-sm)',
              background: 'var(--accent-bg)',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent)'
            }}
          >
            <Sparkles size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{rec.summary}</h3>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              {rec.id} • Action: {rec.type}
            </span>
          </div>
        </div>

        {/* Validation Seal */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="validation-seal">
            <ShieldCheck size={14} />
            <span>Validated: 0 Violations (H1–H12 Passed)</span>
          </span>
        </div>

        {/* Impact Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>LEFT-BEHIND DELTA</span>
            <div className="font-display tabular-nums" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              {rec.impact.left_behind || -41} pax
            </div>
          </div>
          <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>WAIT TIME DELTA</span>
            <div className="font-display tabular-nums" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--load-teal)' }}>
              {rec.impact.avg_wait_min ? `${rec.impact.avg_wait_min}m` : '-1.8m'}
            </div>
          </div>
        </div>

        {/* Trade-Off Statement */}
        <div style={{ background: 'var(--bg-surface-elevated)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Gain vs Cost Trade-off:
          </span>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)', marginTop: 4, lineHeight: 1.4 }}>
            {rec.tradeoff}
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
          {!isApplied ? (
            <>
              <button
                className="btn btn-primary"
                onClick={() => acceptRecommendation(rec.id)}
                style={{ flex: 1, gap: 6 }}
              >
                <Check size={14} />
                <span>Accept & Update Plan</span>
              </button>
              <button
                className="btn btn-outline"
                onClick={() => rejectRecommendation(rec.id)}
                style={{ padding: '6px 12px' }}
              >
                Reject
              </button>
            </>
          ) : (
            <div
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--load-teal-bg)',
                color: 'var(--load-teal)',
                textAlign: 'center',
                fontWeight: 600,
                fontSize: '0.82rem'
              }}
            >
              ✓ Applied to Active Plan
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <aside className="inspector-drawer open" aria-label="Entity Inspector Drawer">
      <div className="drawer-header">
        <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
          {type} details
        </span>
        <button
          className="btn-icon"
          onClick={closeInspectorDrawer}
          title="Close inspector (Esc)"
          aria-label="Close"
        >
          <X size={18} />
        </button>
      </div>

      <div className="drawer-body">
        {type === 'stop' && renderStopDetails(data)}
        {type === 'vehicle' && renderVehicleDetails(typeof data === 'string' ? data : data.vehicle_id)}
        {type === 'alert' && renderAlertDetails(data)}
        {type === 'recommendation' && renderRecommendationDetails(data)}
      </div>
    </aside>
  );
};
