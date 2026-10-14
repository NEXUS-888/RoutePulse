import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import {
  SCHEMATIC_VIEWBOX,
  SCHEMATIC_STOPS,
  SCHEMATIC_ROUTES,
  HUB_WALK_CORRIDOR,
  pointsToSvgPath
} from '../../map/schematic';
import { projectToSvg, getLoadColor, ROUTE_COLORS, formatTimeMin } from '../../utils/geo';
import type { Stop, Route } from '../../types';
import {
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Compass,
  AlertTriangle,
  Info,
  Accessibility,
  Eye,
  EyeOff
} from 'lucide-react';

export const SchematicMap: React.FC = () => {
  const {
    network,
    activeVehicles,
    simTimeMin,
    scenario,
    alerts,
    mapViewMode,
    toggleMapViewMode,
    setSelectedEntity,
    mapLayers,
    toggleLayer,
    theme
  } = useSimulation();

  // Pan and zoom state
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [followedVehicleId, setFollowedVehicleId] = useState<string | null>(null);

  // Hover tooltip state
  const [hoveredStopId, setHoveredStopId] = useState<string | null>(null);

  // Legend collapsed state
  const [legendOpen, setLegendOpen] = useState(true);
  const [layersMenuOpen, setLayersMenuOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
    setFollowedVehicleId(null);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoom = (delta: number) => {
    setZoom(prev => Math.min(2.5, Math.max(0.7, prev + delta)));
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setFollowedVehicleId(null);
  };

  // Follow vehicle centering effect
  useEffect(() => {
    if (!followedVehicleId || !containerRef.current) return;
    const veh = activeVehicles.find(v => v.vehicle_id === followedVehicleId);
    if (!veh) return;

    const targetX = mapViewMode === 'schematic' ? veh.schematicX : veh.svgX;
    const targetY = mapViewMode === 'schematic' ? veh.schematicY : veh.svgY;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const scale = (rect.width / 1000) * zoom;

    setPan({
      x: centerX - targetX * scale,
      y: centerY - targetY * scale
    });
  }, [followedVehicleId, activeVehicles, zoom, mapViewMode]);

  // Convert SVG coordinates based on current view mode
  const getStopCoords = useCallback(
    (stopId: string) => {
      if (mapViewMode === 'schematic') {
        const schematicStop = SCHEMATIC_STOPS[stopId];
        if (schematicStop) return { x: schematicStop.x, y: schematicStop.y };
      }
      // Fallback or Geographic
      const geoStop = network?.stops.find(s => s.stop_id === stopId);
      if (geoStop) {
        return projectToSvg(geoStop.x, geoStop.y);
      }
      return { x: 500, y: 320 };
    },
    [mapViewMode, network]
  );

  if (!network) {
    return <div style={{ padding: 40, textAlign: 'center' }}>Loading campus transit map...</div>;
  }

  return (
    <div
      ref={containerRef}
      className="map-hero-wrapper"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
    >
      {/* Floating View Controls (Top Left) */}
      <div className="map-floating-panel">
        <button
          className="btn"
          onClick={toggleMapViewMode}
          title="Toggle between Schematic Metro diagram and Geographic real-metre map"
          style={{ padding: '3px 8px', fontSize: '0.74rem', gap: 5 }}
        >
          <Compass size={13} />
          <span>{mapViewMode === 'schematic' ? 'Metro Schematic' : 'Geographic'}</span>
        </button>

        <div style={{ height: 16, width: 1, backgroundColor: 'var(--border-color)' }} />

        <button className="btn-icon" onClick={() => handleZoom(0.2)} title="Zoom In">
          <ZoomIn size={15} />
        </button>
        <button className="btn-icon" onClick={() => handleZoom(-0.2)} title="Zoom Out">
          <ZoomOut size={15} />
        </button>
        <button className="btn-icon" onClick={resetView} title="Fit Entire Network (Reset)">
          <Maximize2 size={15} />
        </button>

        <div style={{ height: 16, width: 1, backgroundColor: 'var(--border-color)' }} />

        {/* Follow Vehicle Selector */}
        <select
          value={followedVehicleId || ''}
          onChange={e => setFollowedVehicleId(e.target.value || null)}
          aria-label="Follow moving vehicle"
          title="Track and follow vehicle as it moves"
          style={{
            padding: '3px 8px',
            fontSize: '0.74rem',
            background: 'var(--bg-surface-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            maxWidth: 135
          }}
        >
          <option value="">Follow: Off</option>
          {activeVehicles.map(v => (
            <option key={v.vehicle_id} value={v.vehicle_id}>
              Follow {v.vehicle_id} ({v.route_id})
            </option>
          ))}
        </select>

        <div style={{ height: 16, width: 1, backgroundColor: 'var(--border-color)' }} />

        {/* Layers Dropdown Button */}
        <button
          className="btn"
          onClick={() => setLayersMenuOpen(prev => !prev)}
          title="Toggle Map Data Layers"
          style={{ padding: '3px 8px', fontSize: '0.74rem', gap: 5 }}
        >
          <Layers size={13} />
          <span>Layers</span>
        </button>
      </div>

      {/* Layers Menu Modal */}
      {layersMenuOpen && (
        <div
          style={{
            position: 'absolute',
            top: 56,
            left: 16,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            padding: 12,
            boxShadow: 'var(--shadow-lg)',
            zIndex: 30,
            width: 220,
            display: 'flex',
            flexDirection: 'column',
            gap: 6
          }}
        >
          <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 4 }}>
            Map Layers
          </div>
          {(
            [
              ['routes', 'Route Corridors'],
              ['stops', 'Station Nodes'],
              ['vehicles', 'Vehicle Glyphs'],
              ['loadRings', 'Load Ring Rings'],
              ['demandGlow', 'Station Demand Glow'],
              ['alerts', 'Disruption Alerts'],
              ['transfers', 'Central Hub Ring'],
              ['accessibility', 'Wheelchair Ramps'],
              ['disruptions', 'Disruption Zones']
            ] as const
          ).map(([key, label]) => (
            <label
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.78rem',
                cursor: 'pointer',
                color: 'var(--text-primary)'
              }}
            >
              <span>{label}</span>
              <input
                type="checkbox"
                checked={mapLayers[key]}
                onChange={() => toggleLayer(key)}
                style={{ accentColor: 'var(--route-r1)' }}
              />
            </label>
          ))}
        </div>
      )}

      {/* Collapsible Transit Legend (Bottom Left) */}
      <div className="map-legend-panel">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            fontSize: '0.76rem',
            fontWeight: 700
          }}
          onClick={() => setLegendOpen(prev => !prev)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color: 'var(--text-primary)' }}>TRANSIT LEGEND</span>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
            {legendOpen ? 'Hide' : 'Show'}
          </span>
        </div>

        {legendOpen && (
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.72rem' }}>
            {/* Routes */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              {network.routes.map(r => (
                <div key={r.route_id} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span
                    style={{
                      width: 12,
                      height: 3,
                      borderRadius: 1.5,
                      background: `var(--route-${r.route_id.toLowerCase()})`
                    }}
                  />
                  <span style={{ color: 'var(--text-secondary)' }}>
                    <strong>{r.route_id}</strong> {r.name.split(' ')[0]}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ height: 1, backgroundColor: 'var(--border-subtle)', margin: '4px 0' }} />

            {/* Semantic Load Language */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--load-teal)' }} />
                <span>&lt;85% (Seats)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--load-amber)' }} />
                <span>85–100% (High)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--load-coral)' }} />
                <span>&gt;100% (Full)</span>
              </div>
            </div>

            <div style={{ height: 1, backgroundColor: 'var(--border-subtle)', margin: '4px 0' }} />

            {/* Key Symbols */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
              <span>◎ S03 Grand Hub (4m walk)</span>
              <span>⧉ S13 Metro Gateway</span>
            </div>
          </div>
        )}
      </div>

      {/* Main SVG Transit Map */}
      <svg
        className="map-svg"
        viewBox={`0 0 ${SCHEMATIC_VIEWBOX.width} ${SCHEMATIC_VIEWBOX.height}`}
      >
        <defs>
          {/* Subtle Grid */}
          <pattern id="schematicGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="var(--grid-line-color)"
              strokeWidth="0.75"
            />
          </pattern>

          {/* S1 Disruption Hatched Overlay */}
          <pattern id="disruptionHatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--load-amber)" strokeWidth="2.5" strokeOpacity="0.4" />
          </pattern>

          {/* S2 Breakdown Warning Pattern */}
          <pattern id="breakdownHatch" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--load-coral)" strokeWidth="2.5" strokeOpacity="0.45" />
          </pattern>

          {/* Soft Hub Glow */}
          <radialGradient id="hubHalo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--accent-hub)" stopOpacity="0.35" />
            <stop offset="70%" stopColor="var(--accent-hub)" stopOpacity="0.08" />
            <stop offset="100%" stopColor="var(--accent-hub)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <rect width="100%" height="100%" fill="url(#schematicGrid)" />

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Layer: Disruption Zones (Hatched Segments) */}
          {mapLayers.disruptions && scenario === 'S1' && (
            <path
              d={
                mapViewMode === 'schematic'
                  ? 'M 90 530 L 160 460 L 230 390'
                  : 'M 90 530 L 230 390'
              }
              fill="none"
              stroke="url(#disruptionHatch)"
              strokeWidth="16"
              strokeLinecap="round"
            />
          )}

          {mapLayers.disruptions && scenario === 'S2' && (
            <circle
              cx={mapViewMode === 'schematic' ? 360 : 350}
              cy={mapViewMode === 'schematic' ? 390 : 150}
              r="34"
              fill="url(#breakdownHatch)"
              stroke="var(--load-coral)"
              strokeWidth="1.5"
              strokeDasharray="4 3"
            />
          )}

          {/* Layer: Route Paths */}
          {mapLayers.routes &&
            network.routes.map(r => {
              const routeKey = r.route_id as keyof typeof SCHEMATIC_ROUTES;
              let pathData = '';

              if (mapViewMode === 'schematic' && SCHEMATIC_ROUTES[routeKey]) {
                pathData = pointsToSvgPath(SCHEMATIC_ROUTES[routeKey], 14);
              } else {
                pathData = pointsToSvgPath(
                  r.polyline.map(pt => projectToSvg(pt[0], pt[1])),
                  14
                );
              }

              const strokeVar = `var(--route-${r.route_id.toLowerCase()})`;

              return (
                <g key={r.route_id}>
                  {/* Subtle Route Background Shadow */}
                  <path
                    d={pathData}
                    fill="none"
                    stroke={strokeVar}
                    strokeWidth="8"
                    strokeOpacity={theme === 'dark' ? '0.22' : '0.15'}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {/* Core Sharp Metro Line */}
                  <path
                    d={pathData}
                    fill="none"
                    stroke={strokeVar}
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </g>
              );
            })}

          {/* Layer: Central Hub S03 Interchange Ring */}
          {mapLayers.transfers && (
            <g>
              {/* Hub Outer Halo */}
              <circle
                cx={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cx : getStopCoords('S03').x}
                cy={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cy : getStopCoords('S03').y}
                r="30"
                fill="url(#hubHalo)"
              />
              {/* Grand Interchange Ring */}
              <circle
                cx={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cx : getStopCoords('S03').x}
                cy={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cy : getStopCoords('S03').y}
                r="18"
                fill="var(--bg-surface)"
                stroke="var(--accent-hub)"
                strokeWidth="3.5"
              />
              {/* Inner Hub Circle */}
              <circle
                cx={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cx : getStopCoords('S03').x}
                cy={mapViewMode === 'schematic' ? HUB_WALK_CORRIDOR.ring.cy : getStopCoords('S03').y}
                r="7"
                fill="var(--accent-hub)"
              />
              {/* 4-Minute Walk Corridor Dashed Link */}
              {mapViewMode === 'schematic' && (
                <g>
                  <line
                    x1="466"
                    y1="340"
                    x2="534"
                    y2="340"
                    stroke="var(--accent-hub)"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                  />
                  <text
                    x="500"
                    y="354"
                    textAnchor="middle"
                    fill="var(--text-secondary)"
                    fontSize="10"
                    fontWeight="600"
                    fontFamily="var(--font-mono)"
                  >
                    4 min walk
                  </text>
                </g>
              )}
            </g>
          )}

          {/* Layer: S13 Metro Gateway Portal */}
          {mapLayers.stops && (
            <g
              transform={`translate(${getStopCoords('S13').x}, ${getStopCoords('S13').y})`}
              onClick={() => {
                const s13 = network.stops.find(s => s.stop_id === 'S13');
                if (s13) setSelectedEntity({ type: 'stop', id: 'S13', data: s13 });
              }}
              style={{ cursor: 'pointer' }}
            >
              {/* Entry Portal Shape */}
              <rect
                x="-14"
                y="-14"
                width="28"
                height="28"
                rx="6"
                fill="var(--bg-surface)"
                stroke="var(--accent-metro)"
                strokeWidth="3"
              />
              <path
                d="M -7 -4 L 0 5 L 7 -4"
                fill="none"
                stroke="var(--accent-metro)"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <text
                x="0"
                y="26"
                textAnchor="middle"
                fill="var(--accent-metro)"
                fontSize="11"
                fontWeight="700"
                fontFamily="var(--font-display)"
              >
                METRO GATEWAY (S13)
              </text>
            </g>
          )}

          {/* Layer: Station Stops Nodes */}
          {mapLayers.stops &&
            network.stops.map(stop => {
              if (stop.stop_id === 'S13') return null; // already drawn above
              if (stop.stop_id === 'S03') return null; // already drawn above as hub

              const coords = getStopCoords(stop.stop_id);
              const isHovered = hoveredStopId === stop.stop_id;

              return (
                <g
                  key={stop.stop_id}
                  transform={`translate(${coords.x}, ${coords.y})`}
                  onClick={() => setSelectedEntity({ type: 'stop', id: stop.stop_id, data: stop })}
                  onMouseEnter={() => setHoveredStopId(stop.stop_id)}
                  onMouseLeave={() => setHoveredStopId(null)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer White / Surface Node */}
                  <circle
                    r={isHovered ? 8 : 6}
                    fill="var(--bg-surface)"
                    stroke="var(--text-primary)"
                    strokeWidth="2.5"
                    style={{ transition: 'r 0.15s ease' }}
                  />

                  {/* Wheelchair Accessibility Indicator */}
                  {mapLayers.accessibility && stop.accessible && (
                    <circle r="12" fill="none" stroke="var(--load-teal)" strokeWidth="1.5" strokeDasharray="2 2" />
                  )}

                  {/* Station Label */}
                  <text
                    x={0}
                    y={-12}
                    textAnchor="middle"
                    fill="var(--text-primary)"
                    fontSize="11"
                    fontWeight="600"
                    fontFamily="var(--font-body)"
                    style={{ textShadow: theme === 'dark' ? '0 1px 3px #000' : '0 1px 2px #fff' }}
                  >
                    {stop.name}
                  </text>
                </g>
              );
            })}

          {/* Layer: Moving Vehicles Glyphs */}
          {mapLayers.vehicles &&
            activeVehicles.map(veh => {
              const x = mapViewMode === 'schematic' ? veh.schematicX : veh.svgX;
              const y = mapViewMode === 'schematic' ? veh.schematicY : veh.svgY;
              const loadColor = getLoadColor(veh.loadPct);
              const isBreakdown = veh.status === 'breakdown';
              const isOverloaded = veh.loadPct > 85;

              return (
                <g
                  key={veh.vehicle_id}
                  transform={`translate(${x}, ${y})`}
                  onClick={e => {
                    e.stopPropagation();
                    setSelectedEntity({ type: 'vehicle', id: veh.vehicle_id, data: veh });
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Pulsing halo for >85% load or breakdown */}
                  {isOverloaded && !isBreakdown && (
                    <circle
                      r="22"
                      fill={loadColor.bg}
                      stroke={loadColor.ring}
                      strokeWidth="1.5"
                      opacity="0.6"
                      className="pulsing-vehicle-halo"
                    />
                  )}

                  {/* Breakdown Ghost Marker (S2) */}
                  {isBreakdown ? (
                    <g opacity="0.85">
                      <rect
                        x="-18"
                        y="-12"
                        width="36"
                        height="24"
                        rx="6"
                        fill="rgba(239, 68, 68, 0.2)"
                        stroke="var(--load-coral)"
                        strokeWidth="2"
                        strokeDasharray="4 3"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fill="var(--load-coral)"
                        fontSize="10"
                        fontWeight="700"
                        fontFamily="var(--font-mono)"
                      >
                        BROKEN
                      </text>
                    </g>
                  ) : (
                    /* Active Vehicle Capsule */
                    <g>
                      {/* Vehicle Body Capsule */}
                      <rect
                        x="-16"
                        y="-10"
                        width="32"
                        height="20"
                        rx="5"
                        fill="var(--bg-surface)"
                        stroke="var(--border-strong)"
                        strokeWidth="1.5"
                        filter="drop-shadow(0 2px 4px rgba(0,0,0,0.4))"
                      />

                      {/* Load Ring Encircling Vehicle */}
                      {mapLayers.loadRings && (
                        <circle
                          r="14"
                          fill="none"
                          stroke={loadColor.ring}
                          strokeWidth="2.5"
                          strokeDasharray="88"
                          strokeDashoffset={88 - (88 * Math.min(100, veh.loadPct)) / 100}
                        />
                      )}

                      {/* Route Pill in Capsule */}
                      <text
                        x="0"
                        y="3"
                        textAnchor="middle"
                        fill="var(--text-primary)"
                        fontSize="9"
                        fontWeight="700"
                        fontFamily="var(--font-mono)"
                      >
                        {veh.vehicle_id}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
        </g>
      </svg>

      {/* Interactive Minimap (Bottom Right) */}
      <div
        className="map-minimap-panel"
        style={{
          position: 'absolute',
          bottom: 16,
          right: 16,
          width: 140,
          height: 90,
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-sm)',
          boxShadow: 'var(--shadow-elevation-2)',
          overflow: 'hidden',
          pointerEvents: 'none',
          zIndex: 10
        }}
      >
        <svg viewBox="0 0 1000 640" width="100%" height="100%" style={{ opacity: 0.7 }}>
          {network.routes.map(r => {
            const routeKey = r.route_id as keyof typeof SCHEMATIC_ROUTES;
            let pathData = '';
            if (mapViewMode === 'schematic' && SCHEMATIC_ROUTES[routeKey]) {
              pathData = pointsToSvgPath(SCHEMATIC_ROUTES[routeKey], 14);
            } else {
              pathData = pointsToSvgPath(
                r.polyline.map(pt => projectToSvg(pt[0], pt[1])),
                14
              );
            }
            return (
              <path
                key={r.route_id}
                d={pathData}
                fill="none"
                stroke={`var(--route-${r.route_id.toLowerCase()})`}
                strokeWidth="16"
              />
            );
          })}
          {/* Viewport Box */}
          <rect
            x={Math.max(0, -pan.x / (Math.max(1, (containerRef.current?.clientWidth || 1000) / 1000) * zoom))}
            y={Math.max(0, -pan.y / (Math.max(1, (containerRef.current?.clientHeight || 640) / 640) * zoom))}
            width={Math.min(1000, 1000 / zoom)}
            height={Math.min(640, 640 / zoom)}
            fill="none"
            stroke="var(--route-r1)"
            strokeWidth="18"
            strokeDasharray="24 12"
            opacity="0.85"
          />
        </svg>
        <div
          style={{
            position: 'absolute',
            bottom: 2,
            right: 4,
            fontSize: '0.55rem',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700
          }}
        >
          MINIMAP
        </div>
      </div>
    </div>
  );
};
