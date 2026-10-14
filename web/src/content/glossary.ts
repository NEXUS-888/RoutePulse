// RoutePulse Glossary — Single Source of Truth
// Used by contextual (i) popovers, In-App Help Centre, and docs/USER_GUIDE.md

export interface GlossaryEntry {
  id: string;
  term: string;
  shortDefinition: string;
  detailedExplanation: string;
  category: 'metrics' | 'operations' | 'routing' | 'constraints';
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  networkHealth: {
    id: 'networkHealth',
    term: 'Network Health',
    shortDefinition: 'A 0–100 score measuring overall campus service quality, penalizing overcrowding, left-behind riders, missed transfers, and delays.',
    detailedExplanation: 'Calculated in real time as: max(0, 100 - 40×(trips over capacity) - 30×(left-behind share) - 20×(missed connection share) - 10×(trips delayed >3 min)). Scores 80–100 are Teal (optimal), 60–79 Amber (strained), and <60 Coral (critical).',
    category: 'metrics'
  },
  arrivalWindow: {
    id: 'arrivalWindow',
    term: 'Arrival Window (p10–p90)',
    shortDefinition: 'The 80% confidence interval showing the earliest (p10) and latest (p90) realistic arrival times.',
    detailedExplanation: 'Rather than a fragile single-minute ETA, RoutePulse computes conformal arrival windows calibrated on historical journey distributions and live traffic conditions.',
    category: 'metrics'
  },
  p50Eta: {
    id: 'p50Eta',
    term: 'p50 Median ETA',
    shortDefinition: 'The most probable arrival time: exactly half of simulated outcomes arrive earlier, and half later.',
    detailedExplanation: 'Displayed as the bold tick mark within the horizontal ETA capsule. When traffic is smooth, the window narrows tightly around the p50 tick.',
    category: 'metrics'
  },
  timetablePromise: {
    id: 'timetablePromise',
    term: 'Timetable Promise',
    shortDefinition: 'The published paper schedule time before real-world traffic, passenger surges, or boarding delays occur.',
    detailedExplanation: 'Drawn as a faint ghost tick on ETA capsules to immediately show whether a bus is running ahead, on time, or delayed against the printed schedule.',
    category: 'metrics'
  },
  loadFactor: {
    id: 'loadFactor',
    term: 'Load Factor',
    shortDefinition: 'The ratio of onboard passengers to rated vehicle capacity. Teal is <85%, Amber is 85–100%, and Coral is >100%.',
    detailedExplanation: 'Represented visually as the circular load ring encircling each vehicle glyph on the schematic map, pulsing dynamically when exceeding 85%.',
    category: 'metrics'
  },
  leftBehind: {
    id: 'leftBehind',
    term: 'Left-Behind Passenger',
    shortDefinition: 'A waiting passenger unable to board because the arriving bus has reached 100% capacity.',
    detailedExplanation: 'Left-behind passengers compound waiting times, miss scheduled lectures, and represent the highest penalty in the RoutePulse objective function.',
    category: 'operations'
  },
  missedConnection: {
    id: 'missedConnection',
    term: 'Missed Connection',
    shortDefinition: 'When a passenger arriving at an interchange arrives too late to make their connecting departure within the walking window.',
    detailedExplanation: 'At Central Hub S03, passengers need a 4-minute walking buffer. RoutePulse explicitly protects transfers with retiming and hold-for-connection tactics.',
    category: 'operations'
  },
  hardConstraint: {
    id: 'hardConstraint',
    term: 'Hard Rule / Constraint (H1–H12)',
    shortDefinition: 'Non-negotiable operational requirements including vehicle capacities, driver layovers, and fleet availability that must have 0 violations.',
    detailedExplanation: 'The 12 mathematical constraints (H1: Vehicle capacity, H2: Speed limits, H3: Layover rests, H4: Single assignment, H5: Yard returns, H6: Fleet limits, H7: Route coverage, H8: Headways, H9: Max shift, H10: Battery/fuel, H11: Walking buffer, H12: Stop order) are formally checked by the validator.',
    category: 'constraints'
  },
  tradeoff: {
    id: 'tradeoff',
    term: 'Trade-Off (Gain vs Cost)',
    shortDefinition: 'The explicit balance between operational cost (vehicle-km, fleet hours) and passenger service improvements.',
    detailedExplanation: 'RoutePulse recommendations never hide costs. Every recommendation card states what is gained (e.g. -41 left-behind) and what is spent (e.g. +14.2 vehicle-km).',
    category: 'operations'
  },
  baselinePlan: {
    id: 'baselinePlan',
    term: 'Baseline-0 (Static Plan)',
    shortDefinition: 'The published, fixed timetable with static vehicle assignments and no live optimization.',
    detailedExplanation: 'Baseline-0 experiences severe crowding on Route R3 during morning peak hours and cannot automatically recover from vehicle breakdowns.',
    category: 'operations'
  },
  routepulsePlan: {
    id: 'routepulsePlan',
    term: 'RoutePulse Optimized Plan',
    shortDefinition: 'The proactive schedule optimized via CP-SAT solver to balance fleet utilization and eliminate passenger bottlenecks with 0 constraint violations.',
    detailedExplanation: 'Dynamically shifts departure times, injects reserve fleet, and swaps high-capacity vehicles onto heavy corridors to achieve up to 50% fewer left-behind riders.',
    category: 'operations'
  },
  centralHub: {
    id: 'centralHub',
    term: 'Central Hub (S03)',
    shortDefinition: 'The primary transfer interchange connecting all campus routes with a 4-minute walking corridor.',
    detailedExplanation: 'Rendered as a prominent interchange ring on the schematic map. Synchronized arrivals at S03 guarantee seamless campus-wide transfers.',
    category: 'routing'
  },
  metroGateway: {
    id: 'metroGateway',
    term: 'Metro Station (S13)',
    shortDefinition: 'The south-west campus entry gateway connecting regional city metro riders with campus shuttle routes.',
    detailedExplanation: 'Major demand generation node during morning peak hours (08:00–09:00), generating large transfer waves toward the Academic Core.',
    category: 'routing'
  },
  disruptionMode: {
    id: 'disruptionMode',
    term: 'Disruption Recovery Mode',
    shortDefinition: 'Automated rolling re-optimization triggered during vehicle breakdowns (S2), heavy traffic (S1), or event surges (S3).',
    detailedExplanation: 'Re-runs the CP-SAT solver with a 10-minute departure freeze and minimal-change penalties to stabilize service without chaotic schedule churning.',
    category: 'operations'
  }
};
