import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { projectToSvg, getLoadColor, ROUTE_COLORS, formatTimeMin } from '../../utils/geo';
import type { Stop, Route } from '../../types';
import {
  Layers,
  MapPin,
  Bus,
  AlertTriangle,
  Info,
  CheckCircle2,
  Maximize2
} from 'lucide-react';

export const Screen1NetworkMap: React.FC = () => {
  const {
    network,
    activeVehicles,
    highlightedEntity,
    setHighlightedEntity,
    simTimeMin,
    scenario,
    alerts
  } = useSimulation();

  const [selectedStop, setSelectedStop] = useState<Stop | null>(null);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [showRoutes, setShowRoutes] = useState<Record<string, boolean>>({
    R1: true,
    R2: true,
    R3: true,
    R4: true
  });

  if (!network) {
    return <div style={{ padding: 40, textAlign: 'center' }}>Loading campus network map...</div>;
  }

  const selectedVehicle = activeVehicles.find(v => v.vehicle_id === selectedVehicleId);

  // Toggle route visibility
  const toggleRoute = (routeId: string) => {
    setShowRoutes(prev => ({ ...prev, [routeId]: !prev[routeId] }));
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>
      {/* Map Column */}
      <div className="card" style={{ padding: 14 }}>
        <div className="card-header" style={{ marginBottom: 10 }}>
          <div className="card-title">
            <Layers size={18} style={{ color: 'var(--accent-blue)' }} />
            <span>Interactive Campus Network & Real-Time Replay</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {network.routes.map(r => {
              const active = showRoutes[r.route_id];
              const color = ROUTE_COLORS[r.route_id];
              return (
                <button
                  key={r.route_id}
                  onClick={() => toggleRoute(r.route_id)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    borderRadius: 'var(--radius-full)',
                    border: `1px solid ${color.stroke}`,
                    backgroundColor: active ? color.lightBg : 'transparent',
                    color: active ? color.stroke : 'var(--text-tertiary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}
                >
                  <span style={{ width: 8, height: 3, backgroundColor: color.stroke, borderRadius: 2 }} />
                  {r.route_id} {r.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* SVG Container */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '560px',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
            border: '1px solid var(--border-color)'
          }}
        >
          <svg
            viewBox="0 0 960 600"
            style={{ width: '100%', height: '100%', userSelect: 'none' }}
          >
            {/* Campus Background Grid & Zones */}
            <defs>
              <pattern id="campusGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--border-color)" strokeWidth="0.5" strokeOpacity="0.4" />
              </pattern>
              {/* Radial gradient for central hub S03 */}
              <radialGradient id="hubHalo" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.45" />
                <stop offset="70%" stopColor="#8B5CF6" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
              </radialGradient>
              {/* Vehicle marker filter */}
              <filter id="markerShadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.4" />
              </filter>
            </defs>

            <rect width="960" height="600" fill="url(#campusGrid)" />

            {/* Geographic zones / labels */}
            <text x="60" y="580" fill="var(--text-tertiary)" fontSize="12" fontWeight="600" letterSpacing="1">
              SOUTH-WEST CORRIDOR (METRO FEEDER)
            </text>
            <text x="620" y="40" fill="var(--text-tertiary)" fontSize="12" fontWeight="600" letterSpacing="1">
              NORTH ZONE (HOSTEL PRECINCT)
            </text>
            <text x="760" y="320" fill="var(--text-tertiary)" fontSize="12" fontWeight="600" letterSpacing="1">
              EAST CAMPUS (RESEARCH & SPORTS)
            </text>

            {/* Route Polylines */}
            {network.routes.map(route => {
              if (!showRoutes[route.route_id]) return null;
              const color = ROUTE_COLORS[route.route_id] || { stroke: '#888' };
              const isRouteHighlighted = highlightedEntity?.type === 'route' && highlightedEntity.id === route.route_id;

              // Convert polyline coordinates to SVG
              const points = route.polyline
                .map(pt => {
                  const svgPt = projectToSvg(pt[0], pt[1]);
                  return `${svgPt.x},${svgPt.y}`;
                })
                .join(' ');

              return (
                <g key={route.route_id}>
                  {/* Outer glow if highlighted */}
                  {isRouteHighlighted && (
                    <polyline
                      points={points}
                      fill="none"
                      stroke={color.stroke}
                      strokeWidth="10"
                      strokeOpacity="0.4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}
                  {/* Background route casing */}
                  <polyline
                    points={points}
                    fill="none"
                    stroke="var(--bg-surface)"
                    strokeWidth="6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {/* Colored polyline */}
                  <polyline
                    points={points}
                    fill="none"
                    stroke={color.stroke}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray={route.type === 'linear' ? '6,3' : undefined}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setHighlightedEntity({ type: 'route', id: route.route_id })}
                  />
                </g>
              );
            })}

            {/* Central Hub S03 Aura */}
            {(() => {
              const hubStop = network.stops.find(s => s.is_hub);
              if (!hubStop) return null;
              const p = projectToSvg(hubStop.x, hubStop.y);
              return (
                <g>
                  <circle cx={p.x} cy={p.y} r="38" fill="url(#hubHalo)" />
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="24"
                    fill="none"
                    stroke="#8B5CF6"
                    strokeWidth="1.5"
                    strokeDasharray="4,4"
                  >
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from={`0 ${p.x} ${p.y}`}
                      to={`360 ${p.x} ${p.y}`}
                      dur="14s"
                      repeatCount="indefinite"
                    />
                  </circle>
                </g>
              );
            })()}

            {/* Campus Stops (14 total) */}
            {network.stops.map(stop => {
              const p = projectToSvg(stop.x, stop.y);
              const isHub = stop.is_hub;
              const isDepot = stop.stop_id === 'S01';
              const isSelected = selectedStop?.stop_id === stop.stop_id;
              const isHighlighted = highlightedEntity?.type === 'stop' && highlightedEntity.id === stop.stop_id;

              return (
                <g
                  key={stop.stop_id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedStop(stop);
                    setSelectedVehicleId(null);
                  }}
                >
                  {/* Highlight halo */}
                  {(isSelected || isHighlighted) && (
                    <circle cx={p.x} cy={p.y} r="18" fill="rgba(37, 99, 235, 0.25)" stroke="#2563EB" strokeWidth="2" />
                  )}

                  {/* Stop Marker Circle */}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={isHub ? 11 : (isDepot ? 9 : 7)}
                    fill={isHub ? '#7C3AED' : (isDepot ? '#2563EB' : 'var(--bg-surface)')}
                    stroke={isHub ? '#FFFFFF' : (isDepot ? '#FFFFFF' : 'var(--text-secondary)')}
                    strokeWidth="2.5"
                    filter="url(#markerShadow)"
                  />

                  {/* Inner dot for normal stops */}
                  {!isHub && !isDepot && (
                    <circle cx={p.x} cy={p.y} r="3" fill="var(--text-primary)" />
                  )}

                  {/* Stop Label */}
                  <text
                    x={p.x}
                    y={p.y - (isHub ? 16 : 12)}
                    textAnchor="middle"
                    fill="var(--text-primary)"
                    fontSize={isHub ? "11.5" : "10"}
                    fontWeight={isHub ? "700" : "600"}
                    style={{ pointerEvents: 'none', paintOrder: 'stroke', stroke: 'var(--bg-surface)', strokeWidth: 3 }}
                  >
                    {stop.name} {isHub && '★'}
                  </text>
                  <text
                    x={p.x}
                    y={p.y + (isHub ? 22 : 18)}
                    textAnchor="middle"
                    fill="var(--text-tertiary)"
                    fontSize="8.5"
                    fontWeight="500"
                    style={{ pointerEvents: 'none' }}
                  >
                    {stop.stop_id}
                  </text>
                </g>
              );
            })}

            {/* Active Moving Vehicles */}
            {activeVehicles.map(veh => {
              const loadColor = getLoadColor(veh.loadPct);
              const isSelected = selectedVehicleId === veh.vehicle_id;
              const isTripHighlighted =
                highlightedEntity?.type === 'trip' && highlightedEntity.id === veh.tripId;
              const isVehicleHighlighted =
                highlightedEntity?.type === 'vehicle' && highlightedEntity.id === veh.vehicle_id;

              return (
                <g
                  key={veh.vehicle_id}
                  transform={`translate(${veh.svgX}, ${veh.svgY})`}
                  style={{ cursor: 'pointer', transition: 'transform 0.1s linear' }}
                  onClick={e => {
                    e.stopPropagation();
                    setSelectedVehicleId(veh.vehicle_id);
                    setSelectedStop(null);
                  }}
                >
                  {/* Highlight ring */}
                  {(isSelected || isTripHighlighted || isVehicleHighlighted) && (
                    <circle cx="0" cy="0" r="22" fill="none" stroke="#2563EB" strokeWidth="2.5" strokeDasharray="3,2" />
                  )}

                  {/* Outer Load Indicator Ring (Green <70%, Amber 70-85%, Red >85%) */}
                  <circle
                    cx="0"
                    cy="0"
                    r="14"
                    fill="var(--bg-surface)"
                    stroke={loadColor.ring}
                    strokeWidth="3.5"
                    filter="url(#markerShadow)"
                  />

                  {/* Inner Vehicle Body */}
                  <circle
                    cx="0"
                    cy="0"
                    r="9"
                    fill={veh.status === 'breakdown' ? '#DC2626' : (veh.type === 'bus' ? '#1E293B' : '#334155')}
                  />

                  {/* Direction Pointer or breakdown symbol */}
                  {veh.status === 'breakdown' ? (
                    <text x="0" y="3.5" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="900">
                      !
                    </text>
                  ) : (
                    <text x="0" y="3" textAnchor="middle" fill="#FFFFFF" fontSize="8" fontWeight="800">
                      {veh.vehicle_id}
                    </text>
                  )}

                  {/* Load percentage badge pill above vehicle */}
                  <g transform="translate(0, -18)">
                    <rect
                      x="-18"
                      y="-7"
                      width="36"
                      height="13"
                      rx="3"
                      fill={loadColor.ring}
                    />
                    <text
                      x="0"
                      y="2.5"
                      textAnchor="middle"
                      fill="#FFFFFF"
                      fontSize="8"
                      fontWeight="700"
                    >
                      {veh.loadPct}%
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>

          {/* Map Overlay Floating Info Pill */}
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              left: 12,
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              boxShadow: 'var(--shadow-md)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10B981' }} />
              <span>Load &lt;70%</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#F59E0B' }} />
              <span>70–85%</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#EF4444' }} />
              <span>&gt;85% Critical</span>
            </div>
            <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: 8, color: 'var(--text-tertiary)' }}>
              Hub: S03 Central Hub ★
            </div>
          </div>
        </div>
      </div>

      {/* Side Inspector Column */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Selected Vehicle Card */}
        {selectedVehicle ? (
          <div className="card" style={{ borderColor: 'var(--accent-blue)' }}>
            <div className="card-header">
              <div className="card-title" style={{ fontSize: '0.95rem' }}>
                <Bus size={17} style={{ color: 'var(--accent-blue)' }} />
                <span>Vehicle {selectedVehicle.vehicle_id}</span>
              </div>
              <span
                className="badge"
                style={{
                  backgroundColor: getLoadColor(selectedVehicle.loadPct).bg,
                  color: getLoadColor(selectedVehicle.loadPct).text
                }}
              >
                {selectedVehicle.loadPct}% Load
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.82rem', marginBottom: 12 }}>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>ROUTE</div>
                <div style={{ fontWeight: 600 }}>{selectedVehicle.route_id} ({ROUTE_COLORS[selectedVehicle.route_id]?.name})</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>TYPE / CAPACITY</div>
                <div style={{ fontWeight: 600 }}>{selectedVehicle.type.toUpperCase()} ({selectedVehicle.load}/{selectedVehicle.capacity} pax)</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>SPEED</div>
                <div style={{ fontWeight: 600 }}>{(selectedVehicle.speed_mps * 3.6).toFixed(1)} km/h</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>NEXT STOP</div>
                <div style={{ fontWeight: 600 }}>{selectedVehicle.nextStop}</div>
              </div>
            </div>

            {selectedVehicle.status === 'breakdown' && (
              <div
                style={{
                  backgroundColor: 'var(--accent-red-light)',
                  border: '1px solid var(--accent-red)',
                  padding: 8,
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  color: 'var(--accent-red)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginBottom: 10
                }}
              >
                <AlertTriangle size={15} />
                <span>Vehicle Out of Service: Mechanical breakdown reported at 08:05</span>
              </div>
            )}

            <button
              className="btn btn-outline"
              style={{ width: '100%', fontSize: '0.8rem' }}
              onClick={() => setSelectedVehicleId(null)}
            >
              Close Inspector
            </button>
          </div>
        ) : selectedStop ? (
          <div className="card" style={{ borderColor: 'var(--accent-purple)' }}>
            <div className="card-header">
              <div className="card-title" style={{ fontSize: '0.95rem' }}>
                <MapPin size={17} style={{ color: 'var(--accent-purple)' }} />
                <span>{selectedStop.name} ({selectedStop.stop_id})</span>
              </div>
              {selectedStop.is_hub && <span className="badge badge-info">Transfer Hub</span>}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.82rem', marginBottom: 12 }}>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>WAITING CAPACITY</div>
                <div style={{ fontWeight: 600 }}>{selectedStop.capacity_waiting || 40} pax</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>ACCESSIBLE</div>
                <div style={{ fontWeight: 600 }}>{selectedStop.accessible ? '✓ Ramp Equipped' : 'No'}</div>
              </div>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              Serving routes:{' '}
              {network.routes
                .filter(r => r.stop_sequence.includes(selectedStop.stop_id))
                .map(r => r.route_id)
                .join(', ')}
            </div>

            <button
              className="btn btn-outline"
              style={{ width: '100%', fontSize: '0.8rem' }}
              onClick={() => setSelectedStop(null)}
            >
              Close Inspector
            </button>
          </div>
        ) : (
          <div className="card">
            <div className="card-title" style={{ fontSize: '0.9rem', marginBottom: 8 }}>
              <Info size={16} style={{ color: 'var(--accent-blue)' }} />
              <span>Inspector Guide</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Click any moving vehicle marker or stop icon on the SVG campus canvas to inspect real-time load, capacity, speed, and schedule progression.
            </p>
          </div>
        )}

        {/* Live Active Fleet Summary */}
        <div className="card">
          <div className="card-header">
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>Active Fleet Status</span>
            <span className="badge badge-info">{activeVehicles.length} Vehicles</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {activeVehicles.map(veh => {
              const loadColor = getLoadColor(veh.loadPct);
              return (
                <div
                  key={veh.vehicle_id}
                  onClick={() => {
                    setSelectedVehicleId(veh.vehicle_id);
                    setSelectedStop(null);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 10px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: selectedVehicleId === veh.vehicle_id ? 'var(--bg-hover)' : 'var(--bg-surface-elevated)',
                    cursor: 'pointer',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.8rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: loadColor.ring
                      }}
                    />
                    <span style={{ fontWeight: 600 }}>{veh.vehicle_id}</span>
                    <span style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>({veh.route_id})</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, color: loadColor.text }}>{veh.loadPct}%</span>
                    <span style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>{veh.load}/{veh.capacity}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
