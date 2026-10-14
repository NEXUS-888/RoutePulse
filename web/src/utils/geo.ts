// Coordinate projection & path interpolation for RoutePulse Campus SVG Map

const MAP_BOUNDS = {
  minX: -1650,
  maxX: 1550,
  minY: -750,
  maxY: 1450,
  viewWidth: 960,
  viewHeight: 600,
  padding: 40
};

export function projectToSvg(x: number, y: number): { x: number; y: number } {
  const spanX = MAP_BOUNDS.maxX - MAP_BOUNDS.minX;
  const spanY = MAP_BOUNDS.maxY - MAP_BOUNDS.minY;

  const svgX = MAP_BOUNDS.padding + ((x - MAP_BOUNDS.minX) / spanX) * (MAP_BOUNDS.viewWidth - 2 * MAP_BOUNDS.padding);
  // Invert Y so higher Y is North (upwards in SVG)
  const svgY = MAP_BOUNDS.padding + ((MAP_BOUNDS.maxY - y) / spanY) * (MAP_BOUNDS.viewHeight - 2 * MAP_BOUNDS.padding);

  return { x: Math.round(svgX * 10) / 10, y: Math.round(svgY * 10) / 10 };
}

export function formatTimeMin(min: number): string {
  const totalMin = Math.floor(min);
  const hours = Math.floor(totalMin / 60);
  const mins = totalMin % 60;
  const secs = Math.floor((min - totalMin) * 60);
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}${secs > 0 ? `:${secs.toString().padStart(2, '0')}` : ''}`;
}

export function formatMinutesDelta(delta: number): string {
  if (delta > 0) return `+${delta.toFixed(1)}m`;
  return `${delta.toFixed(1)}m`;
}

export function getLoadColor(loadPct: number): { ring: string; bg: string; text: string; badge: string } {
  if (loadPct < 70) {
    return {
      ring: '#10B981', // green
      bg: 'rgba(16, 185, 129, 0.15)',
      text: '#10B981',
      badge: 'Normal (<70%)'
    };
  }
  if (loadPct <= 85) {
    return {
      ring: '#F59E0B', // amber
      bg: 'rgba(245, 158, 11, 0.15)',
      text: '#F59E0B',
      badge: 'Moderate (70-85%)'
    };
  }
  return {
    ring: '#EF4444', // red
    bg: 'rgba(239, 68, 68, 0.2)',
    text: '#EF4444',
    badge: 'Critical (>85%)'
  };
}

export const ROUTE_COLORS: Record<string, { stroke: string; lightBg: string; name: string }> = {
  R1: { stroke: '#3B82F6', lightBg: 'rgba(59, 130, 246, 0.12)', name: 'Main Loop' },
  R2: { stroke: '#8B5CF6', lightBg: 'rgba(139, 92, 246, 0.12)', name: 'Hostel Express' },
  R3: { stroke: '#10B981', lightBg: 'rgba(16, 185, 129, 0.12)', name: 'Metro Connector' },
  R4: { stroke: '#F59E0B', lightBg: 'rgba(245, 158, 11, 0.12)', name: 'Sports Shuttle' }
};

// Interpolate vehicle position along a polyline given a progress fraction [0, 1]
export function interpolatePolyline(polyline: [number, number][], progress: number): { x: number; y: number; angle: number } {
  if (polyline.length === 0) return { x: 0, y: 0, angle: 0 };
  if (polyline.length === 1) return { x: polyline[0][0], y: polyline[0][1], angle: 0 };

  const clampedProgress = Math.max(0, Math.min(1, progress));

  // Compute lengths between segments
  const segLengths: number[] = [];
  let totalLength = 0;
  for (let i = 0; i < polyline.length - 1; i++) {
    const dx = polyline[i + 1][0] - polyline[i][0];
    const dy = polyline[i + 1][1] - polyline[i][1];
    const len = Math.hypot(dx, dy);
    segLengths.push(len);
    totalLength += len;
  }

  if (totalLength === 0) return { x: polyline[0][0], y: polyline[0][1], angle: 0 };

  const targetDist = clampedProgress * totalLength;
  let accumulated = 0;

  for (let i = 0; i < segLengths.length; i++) {
    const len = segLengths[i];
    if (accumulated + len >= targetDist || i === segLengths.length - 1) {
      const segFraction = len > 0 ? (targetDist - accumulated) / len : 0;
      const x0 = polyline[i][0];
      const y0 = polyline[i][1];
      const x1 = polyline[i + 1][0];
      const y1 = polyline[i + 1][1];

      const x = x0 + (x1 - x0) * segFraction;
      const y = y0 + (y1 - y0) * segFraction;
      const angle = Math.atan2(y1 - y0, x1 - x0) * (180 / Math.PI);

      return { x, y, angle };
    }
    accumulated += len;
  }

  const last = polyline[polyline.length - 1];
  return { x: last[0], y: last[1], angle: 0 };
}
