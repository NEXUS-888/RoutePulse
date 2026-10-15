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
  const [legendOpen, setLegendOpen] = useState(() => window.innerWidth >= 1280);
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
      {/* Floating View Controls (Top Left): map style, zoom, layers — nothing else */}
      <div className="map-toolbar" onMouseDown={e => e.stopPropagation()}>
        <div className="segmented" role="group" aria-label="Map style">
          <button
            className={mapViewMode === 'schematic' ? 'active' : ''}
            aria-pressed={mapViewMode === 'schematic'}
            onClick={() => mapViewMode !== 'schematic' && toggleMapViewMode()}
            title="Clean metro-style diagram (M)"
          >
            Schematic
          </button>
          <button
            className={mapViewMode === 'geographic' ? 'active' : ''}
            aria-pressed={mapViewMode === 'geographic'}
            onClick={() => mapViewMode !== 'geographic' && toggleMapViewMode()}
            title="True-to-scale campus geography (M)"
          >
            Geographic
          </button>
        </div>

        <div className="map-toolbar-group">
          <button className="btn-icon" onClick={() => handleZoom(-0.2)} title="Zoom out" aria-label="Zoom out">
            <ZoomOut size={16} />
          </button>
          <button className="btn-icon" onClick={() => handleZoom(0.2)} title="Zoom in" aria-label="Zoom in">
            <ZoomIn size={16} />
          </button>
          <button className="btn-icon" onClick={resetView} title="Fit the whole network" aria-label="Fit network">
            <Maximize2 size={16} />
          </button>
        </div>

        <button
          className="btn"
          onClick={() => setLayersMenuOpen(prev => !prev)}
          aria-expanded={layersMenuOpen}
          title="Choose what the map shows"
          style={{ boxShadow: 'var(--shadow-md)' }}
        >
          <Layers size={15} />
          <span>Layers</span>
        </button>
      </div>

      {/* Layers & follow popover */}
      {layersMenuOpen && (
        <div className="map-popover" onMouseDown={e => e.stopPropagation()}>
          <h4>Show on map</h4>
          {(
            [
              ['routes', 'Route lines'],
              ['stops', 'Stops'],
              ['vehicles', 'Vehicles'],
              ['loadRings', 'Load rings'],
              ['alerts', 'Alerts'],
              ['transfers', 'Hub interchange'],
              ['accessibility', 'Wheelchair access'],
              ['disruptions', 'Disruption zones']
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="toggle-row">
              <span>{label}</span>
              <input type="checkbox" checked={mapLayers[key]} onChange={() => toggleLayer(key)} />
            </label>
          ))}

          <div style={{ height: 1, background: 'var(--border-subtle)', margin: '4px 0' }} />

          <h4>Follow a vehicle</h4>
          <select
            className="select"
            value={followedVehicleId || ''}
            onChange={e => setFollowedVehicleId(e.target.value || null)}
            aria-label="Follow moving vehicle"
          >
            <option value="">Not following</option>
            {activeVehicles.map(v => (
              <option key={v.vehicle_id} value={v.vehicle_id}>
                {v.vehicle_id} · {v.route_id}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Compact legend (bottom left): what the lines and rings mean */}
      <div className="map-legend-panel" onMouseDown={e => e.stopPropagation()}>
        <button className="legend-head" onClick={() => setLegendOpen(prev => !prev)} aria-expanded={legendOpen}>
          <span>Legend</span>
          <span>{legendOpen ? 'Hide' : 'Show'}</span>
        </button>

        {legendOpen && (
          <div className="legend-body">
            <div className="legend-routes">
              {network.routes.map(r => (
                <div key={r.route_id} className="legend-route">
                  <i style={{ background: `var(--route-${r.route_id.toLowerCase()})` }} />
                  <span>
                    <strong style={{ color: 'var(--text-primary)' }}>{r.route_id}</strong> {r.name.split(' ')[0]}
                  </span>
                </div>
              ))}
            </div>

            <div className="legend-load" aria-label="Vehicle load ring colours">
              <span><i style={{ background: 'var(--load-teal)' }} />Seats free</span>
              <span><i style={{ background: 'var(--load-amber)' }} />Filling up</span>
              <span><i style={{ background: 'var(--load-coral)' }} />Full</span>
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
              {/* Hub caption: the 4-minute interchange walk, placed clear of the route lines */}
              {mapViewMode === 'schematic' && (
                <text
                  x={HUB_WALK_CORRIDOR.ring.cx - 26}
                  y={HUB_WALK_CORRIDOR.ring.cy - 24}
                  textAnchor="end"
                  fill="var(--text-secondary)"
                  stroke="var(--map-label-halo)"
                  strokeWidth="3.5"
                  strokeLinejoin="round"
                  style={{ paintOrder: 'stroke fill' }}
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="var(--font-body)"
                >
                  Central Hub · 4 min walk
                </text>
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
              const layout = SCHEMATIC_STOPS[stop.stop_id];

              let labelX = 0;
              let labelY = -12;
              let anchor: 'start' | 'middle' | 'end' = 'middle';

              if (mapViewMode === 'schematic' && layout) {
                if (layout.labelPosition === 'left') {
                  labelX = -12;
                  labelY = 4;
                  anchor = 'end';
                } else if (layout.labelPosition === 'right') {
                  labelX = 12;
                  labelY = 4;
                  anchor = 'start';
                } else if (layout.labelPosition === 'bottom') {
                  labelX = 0;
                  labelY = 18;
                  anchor = 'middle';
                } else if (layout.labelPosition === 'bottom-left') {
                  labelX = -10;
                  labelY = 16;
                  anchor = 'end';
                } else if (layout.labelPosition === 'top-right') {
                  labelX = 12;
                  labelY = -10;
                  anchor = 'start';
                } else {
                  labelX = 0;
                  labelY = -12;
                  anchor = 'middle';
                }
              }

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

                  {/* Station Label with Crisp Contrast Halo */}
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor={anchor}
                    fill="var(--text-primary)"
                    stroke={'var(--map-label-halo)'}
                    strokeWidth="3.5"
                    strokeLinejoin="round"
                    style={{ paintOrder: 'stroke fill' }}
                    fontSize="11"
                    fontWeight="700"
                    fontFamily="var(--font-body)"
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
                        fill="var(--load-coral-bg)"
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
                    /* Active vehicle: route colour = which line, ring = how full */
                    <g>
                      {mapLayers.loadRings && (
                        <>
                          <circle r="18" fill="var(--bg-surface)" stroke="var(--border-strong)" strokeWidth="1" opacity="0.9" />
                          <circle
                            r="16"
                            fill="none"
                            stroke={loadColor.ring}
                            strokeWidth="3.5"
                            strokeLinecap="round"
                            strokeDasharray="100.53"
                            strokeDashoffset={100.53 - (100.53 * Math.min(100, Math.max(6, veh.loadPct))) / 100}
                            transform="rotate(-90)"
                          />
                        </>
                      )}
                      <circle r="12" fill={`var(--route-${veh.route_id.toLowerCase()}, var(--text-secondary))`} />
                      <text
                        x="0"
                        y="3.5"
                        textAnchor="middle"
                        fill="var(--on-route)"
                        fontSize="10"
                        fontWeight="800"
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

      {/* Minimap (bottom right): only useful once the view is zoomed in or panned */}
      {(zoom > 1.05 || Math.abs(pan.x) > 8 || Math.abs(pan.y) > 8) && (
      <div className="map-minimap-panel" aria-hidden="true">
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
            stroke="var(--accent)"
            strokeWidth="18"
            strokeDasharray="24 12"
            opacity="0.85"
          />
        </svg>
      </div>
      )}
    </div>
  );
};
