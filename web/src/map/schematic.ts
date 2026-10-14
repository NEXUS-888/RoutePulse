// RoutePulse Hand-Authored Schematic Transit Map Layout
// 45°/90° Octolinear Segments, Rounded Corners, Station Ticks, Central Interchange Ring

export interface SchematicPoint {
  x: number;
  y: number;
}

export interface SchematicStopLayout {
  stop_id: string;
  name: string;
  x: number;
  y: number;
  labelPosition: 'top' | 'bottom' | 'left' | 'right' | 'top-right' | 'bottom-left';
  is_hub?: boolean;
  is_gateway?: boolean;
}

export const SCHEMATIC_VIEWBOX = {
  width: 1000,
  height: 640
};

// Hand-authored schematic stop coordinates
export const SCHEMATIC_STOPS: Record<string, SchematicStopLayout> = {
  S13: {
    stop_id: 'S13',
    name: 'Metro Gateway',
    x: 90,
    y: 530,
    labelPosition: 'bottom',
    is_gateway: true
  },
  S01: {
    stop_id: 'S01',
    name: 'Main Gate',
    x: 230,
    y: 390,
    labelPosition: 'bottom-left'
  },
  S02: {
    stop_id: 'S02',
    name: 'Admin Block',
    x: 360,
    y: 390,
    labelPosition: 'bottom'
  },
  S03: {
    stop_id: 'S03',
    name: 'Central Hub',
    x: 500,
    y: 320,
    labelPosition: 'top-right',
    is_hub: true
  },
  S04: {
    stop_id: 'S04',
    name: 'Library',
    x: 640,
    y: 320,
    labelPosition: 'bottom'
  },
  S05: {
    stop_id: 'S05',
    name: 'Engineering',
    x: 760,
    y: 240,
    labelPosition: 'right'
  },
  S06: {
    stop_id: 'S06',
    name: 'Science Precinct',
    x: 760,
    y: 130,
    labelPosition: 'top-right'
  },
  S07: {
    stop_id: 'S07',
    name: 'Auditorium',
    x: 370,
    y: 130,
    labelPosition: 'top'
  },
  S10: {
    stop_id: 'S10',
    name: 'Food Court',
    x: 500,
    y: 220,
    labelPosition: 'left'
  },
  S08: {
    stop_id: 'S08',
    name: 'Hostel A',
    x: 430,
    y: 90,
    labelPosition: 'left'
  },
  S09: {
    stop_id: 'S09',
    name: 'Hostel B',
    x: 570,
    y: 90,
    labelPosition: 'right'
  },
  S14: {
    stop_id: 'S14',
    name: 'Medical Centre',
    x: 640,
    y: 440,
    labelPosition: 'bottom'
  },
  S12: {
    stop_id: 'S12',
    name: 'Research Park',
    x: 770,
    y: 440,
    labelPosition: 'bottom'
  },
  S11: {
    stop_id: 'S11',
    name: 'Sports Complex',
    x: 900,
    y: 510,
    labelPosition: 'top'
  }
};

// Hand-authored 45°/90° polyline routes with aesthetic offsets
export const SCHEMATIC_ROUTES: Record<string, SchematicPoint[]> = {
  // R1: Main Loop (Blue)
  // S01 -> S02 -> S03 -> S04 -> S05 -> S06 -> S07 -> S01
  R1: [
    { x: 230, y: 390 }, // S01
    { x: 360, y: 390 }, // S02
    { x: 430, y: 390 },
    { x: 500, y: 320 }, // S03 Central Hub
    { x: 640, y: 320 }, // S04 Library
    { x: 690, y: 320 },
    { x: 760, y: 250 }, // transition to S05
    { x: 760, y: 240 }, // S05 Engineering
    { x: 760, y: 130 }, // S06 Science
    { x: 370, y: 130 }, // S07 Auditorium
    { x: 230, y: 270 }, // 45 degree down to S01
    { x: 230, y: 390 }  // Back to S01
  ],

  // R2: Hostel Express (Green)
  // S03 -> S10 -> S08 -> S09 -> S03
  R2: [
    { x: 500, y: 320 }, // S03 Central Hub
    { x: 500, y: 220 }, // S10 Food Court
    { x: 500, y: 160 },
    { x: 430, y: 90 },  // S08 Hostel A
    { x: 570, y: 90 },  // S09 Hostel B
    { x: 570, y: 160 },
    { x: 500, y: 230 },
    { x: 500, y: 320 }  // S03 Loop complete
  ],

  // R3: Metro Connector (Purple)
  // S13 -> S01 -> S02 -> S03
  R3: [
    { x: 90, y: 530 },  // S13 Metro Gateway
    { x: 160, y: 460 }, // 45° incline
    { x: 230, y: 390 }, // S01 Main Gate
    { x: 360, y: 390 }, // S02 Admin Block
    { x: 430, y: 390 },
    { x: 500, y: 320 }  // S03 Central Hub
  ],

  // R4: Research & Sports Shuttle (Amber)
  // S03 -> S14 -> S12 -> S11
  R4: [
    { x: 500, y: 320 }, // S03 Central Hub
    { x: 570, y: 390 }, // 45° decline
    { x: 640, y: 440 }, // S14 Medical
    { x: 770, y: 440 }, // S12 Research
    { x: 840, y: 440 },
    { x: 900, y: 500 }, // 45° to S11
    { x: 900, y: 510 }  // S11 Sports Complex
  ]
};

// Hub interchange 4-minute walking link coordinates (dashed corridor)
export const HUB_WALK_CORRIDOR = {
  ring: { cx: 500, cy: 320, r: 24 },
  walkLink: [
    { x: 480, y: 320 },
    { x: 520, y: 320 }
  ],
  transferLabel: '4 min walk'
};

// Helper: Calculate point along a schematic route polyline by fractional distance (0.0 to 1.0)
export function getSchematicPointAtProgress(routeId: string, progress: number): SchematicPoint {
  const points = SCHEMATIC_ROUTES[routeId];
  if (!points || points.length === 0) return { x: 500, y: 320 };
  if (points.length === 1) return points[0];

  const clamped = Math.max(0, Math.min(1, progress));

  // Compute lengths of each segment
  const segLengths: number[] = [];
  let totalLength = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1].x - points[i].x;
    const dy = points[i + 1].y - points[i].y;
    const len = Math.hypot(dx, dy);
    segLengths.push(len);
    totalLength += len;
  }

  if (totalLength === 0) return points[0];

  const targetDist = clamped * totalLength;
  let accumulated = 0;

  for (let i = 0; i < segLengths.length; i++) {
    const len = segLengths[i];
    if (accumulated + len >= targetDist || i === segLengths.length - 1) {
      const segFraction = len > 0 ? (targetDist - accumulated) / len : 0;
      return {
        x: points[i].x + segFraction * (points[i + 1].x - points[i].x),
        y: points[i].y + segFraction * (points[i + 1].y - points[i].y)
      };
    }
    accumulated += len;
  }

  return points[points.length - 1];
}

// Convert points array to SVG path string with rounded corners
export function pointsToSvgPath(points: SchematicPoint[], radius = 12): string {
  if (points.length < 2) return '';
  let d = `M ${points[0].x} ${points[0].y}`;

  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];

    if (!next) {
      d += ` L ${curr.x} ${curr.y}`;
      break;
    }

    // Corner rounding logic
    const dx1 = curr.x - prev.x;
    const dy1 = curr.y - prev.y;
    const dx2 = next.x - curr.x;
    const dy2 = next.y - curr.y;

    const len1 = Math.hypot(dx1, dy1);
    const len2 = Math.hypot(dx2, dy2);

    const r = Math.min(radius, len1 / 2, len2 / 2);

    if (r < 1 || (dx1 === dx2 && dy1 === dy2)) {
      d += ` L ${curr.x} ${curr.y}`;
    } else {
      const startX = curr.x - (dx1 / len1) * r;
      const startY = curr.y - (dy1 / len1) * r;
      const endX = curr.x + (dx2 / len2) * r;
      const endY = curr.y + (dy2 / len2) * r;

      d += ` L ${startX} ${startY}`;
      d += ` Q ${curr.x} ${curr.y} ${endX} ${endY}`;
    }
  }

  return d;
}
