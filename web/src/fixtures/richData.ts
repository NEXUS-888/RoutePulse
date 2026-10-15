import type { Alert, Recommendation, DemandResponse, EvalResultsResponse } from '../types';
import evalFixture from './eval_results.json';

export const ALL_ALERTS: Alert[] = [
  {
    alert_id: "ALT-001",
    code: "A2",
    severity: "hard-risk",
    title: "Capacity Violation Risk on Route R3",
    detail: "P80 demand (74 pax) exceeds bus capacity (45 pax) on trip T_R3_01 departing 07:45 from S13.",
    entity_type: "trip",
    entity_id: "T_R3_01",
    time_min: 465,
    pax_affected: 29
  },
  {
    alert_id: "ALT-002",
    code: "A4",
    severity: "soft",
    title: "Tight Transfer Connection at Hub S03",
    detail: "Feeder trip T_R3_01 projected to arrive S03 at 07:44:30; connecting trip T_R2_01 departs 07:45 (buffer < 4 min).",
    entity_type: "trip",
    entity_id: "T_R2_01",
    time_min: 465,
    pax_affected: 14
  },
  {
    alert_id: "ALT-003",
    code: "A1",
    severity: "soft",
    title: "Overcrowding on Route R1 Main Loop",
    detail: "Projected peak load 91% (>85% soft threshold) between S04 Library and S05 Engineering at 08:15.",
    entity_type: "trip",
    entity_id: "T_R1_01",
    time_min: 495,
    pax_affected: 22
  },
  {
    alert_id: "ALT-004",
    code: "A6",
    severity: "soft",
    title: "Headway Bunching Risk on Route R2",
    detail: "Projected headway between B2 and M1 dropped to 2.8 min (<40% of scheduled 8 min headway).",
    entity_type: "route",
    entity_id: "R2",
    time_min: 510,
    pax_affected: 18
  },
  {
    alert_id: "ALT-005",
    code: "A3",
    severity: "hard-risk",
    title: "Unmet Passenger Demand at S13 Metro",
    detail: "Over 35 passengers left behind during 08:00–08:15 surge slot with no immediate departure.",
    entity_type: "stop",
    entity_id: "S13",
    time_min: 490,
    pax_affected: 35
  },
  {
    alert_id: "ALT-006",
    code: "A7",
    severity: "soft",
    title: "Headway Service Gap on R4 Shuttle",
    detail: "Gap between departures exceeds maximum off-peak headway (gap = 23 min vs max 20 min).",
    entity_type: "route",
    entity_id: "R4",
    time_min: 540,
    pax_affected: 12
  },
  {
    alert_id: "ALT-007",
    code: "A8",
    severity: "hard-risk",
    title: "Vehicle Unavailability (Simulated Breakdown)",
    detail: "Bus B3 reported engine warning; scheduled trip T_R3_02 requires reallocation or reserve deployment.",
    entity_type: "vehicle",
    entity_id: "B3",
    time_min: 485,
    pax_affected: 45
  },
  {
    alert_id: "ALT-008",
    code: "A5",
    severity: "soft",
    title: "Tight Layover Schedule at Depot S01",
    detail: "Vehicle B1 scheduled layover before next block is 3.5 min (<4.0 min minimum H3 requirement).",
    entity_type: "vehicle",
    entity_id: "B1",
    time_min: 475,
    pax_affected: 0
  }
];

export const ALL_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "rec-0007",
    type: "ADD_TRIP",
    summary: "Add an R3 departure at 08:21 from S13 using bus B5 (idle reserve)",
    reason_codes: ["A2_CAPACITY_RISK", "A4_MISSED_CONNECTION"],
    evidence: {
      p80_load_before: 1.34,
      p80_load_after: 0.91,
      pax_affected: 62
    },
    impact: {
      avg_wait_min: -1.8,
      left_behind: -41,
      missed_connections: -17,
      vehicle_km: 14.2
    },
    tradeoff: "Uses a reserve bus for 52 min (+14.2 vehicle-km). Reduces R3 left-behind passengers by 41. R1 headway unchanged.",
    binding_constraints: [
      "H1 Vehicle Availability: B5 idle at S01 depot",
      "H3 Minimum Layover: 6 min > 4 min required",
      "H6 Fleet Cap: 9 active / 10 available vehicles",
      "H7 Headway: 6 min headway satisfies bounds [3, 12] min"
    ],
    alternatives_rejected: [
      {
        option: "Retime 08:24 trip earlier to 08:18",
        why: "Violates H8 shift limit and still leaves P80 load at 1.12 (>1.0 rated capacity)."
      },
      {
        option: "Deploy minibus M2 instead of bus B5",
        why: "Minibus capacity 22 pax insufficient for 62 affected morning peak riders."
      }
    ],
    validated: true,
    violations: [],
    confidence: "high"
  },
  {
    id: "rec-0008",
    type: "RETIME_TRIP",
    summary: "Retime trip T_R2_01 departure at S03 Central Hub by +3 min (07:45 -> 07:48)",
    reason_codes: ["A4_MISSED_CONNECTION"],
    evidence: {
      feeder_arrival_s03: "07:44:30",
      original_departure: "07:45:00",
      protected_connection_pax: 14
    },
    impact: {
      avg_wait_min: -0.4,
      left_behind: 0,
      missed_connections: -14,
      vehicle_km: 0.0
    },
    tradeoff: "Adds 3 min wait for 8 originating passengers at Hub S03, but saves 14 transferring students from a 15-min missed connection penalty.",
    binding_constraints: [
      "H8 Shift Limit: 3 min shift <= 5 min max allowance",
      "H7 Headway: Post-shift headway 11 min <= 12 min peak cap",
      "H2 Overlap: No trip overlap detected on vehicle B2"
    ],
    alternatives_rejected: [
      {
        option: "Hold feeder T_R3_01 at Metro Station",
        why: "Feeder is already en route; cannot accelerate past physical speed bounds."
      }
    ],
    validated: true,
    violations: [],
    confidence: "high"
  },
  {
    id: "rec-0009",
    type: "SWAP_VEHICLE",
    summary: "Swap bus B4 (45 pax, accessible) with minibus M3 (22 pax) on Route R1 08:30 block",
    reason_codes: ["A1_OVERCROWDING", "H10_ACCESSIBLE_SERVICE"],
    evidence: {
      demand_r1_0830: 41,
      demand_r4_0830: 16
    },
    impact: {
      avg_wait_min: -0.6,
      left_behind: -19,
      missed_connections: -3,
      vehicle_km: 0.0
    },
    tradeoff: "Matches larger vehicle capacity to surge corridor without adding vehicle kilometers or fuel overhead.",
    binding_constraints: [
      "H10 Accessibility: Accessible vehicle allocated to high-demand branch",
      "H12 Capacity: Load ratio drops from 1.86 to 0.91",
      "H4 Continuity: Both vehicles swap at central depot S01 during common layover"
    ],
    alternatives_rejected: [
      {
        option: "Dispatch extra deadhead bus from off-campus",
        why: "Takes 22 minutes to arrive, missing the student morning bell."
      }
    ],
    validated: true,
    violations: [],
    confidence: "high"
  },
  {
    id: "rec-0010",
    type: "REALLOCATE_VEHICLE",
    summary: "Reallocate reserve minibus M1 to Route R4 shuttle for 09:00 lecture rush",
    reason_codes: ["A7_SERVICE_GAP", "A3_UNMET_DEMAND"],
    evidence: {
      pax_waiting_s11: 28,
      headway_before_min: 22,
      headway_after_min: 11
    },
    impact: {
      avg_wait_min: -2.3,
      left_behind: -14,
      missed_connections: -5,
      vehicle_km: 8.4
    },
    tradeoff: "Reduces peak wait times at Sports Complex & Research Park by half. Requires 8.4 vehicle-km fuel expenditure.",
    binding_constraints: [
      "H6 Fleet Limit: M1 is currently idle in reserve",
      "H9 Driver Hours: Relief driver D04 available within 15 min"
    ],
    alternatives_rejected: [
      {
        option: "Short-turn R1 Main Loop at S05",
        why: "Isolates Science Block S06 and Hostel passengers."
      }
    ],
    validated: true,
    violations: [],
    confidence: "high"
  }
];

// Measured results (copied from results/results.json by `eval.report.compute_headline`).
export const MOCK_EVAL_RESULTS: EvalResultsResponse = evalFixture as unknown as EvalResultsResponse;

// Generate full stop demand matrix for Screen 3 heatmap
export function generateStopDemandHeatmap(stops: { stop_id: string; name: string }[]): Record<string, DemandResponse> {
  const result: Record<string, DemandResponse> = {};
  
  // 12 slots from 07:30 (450) to 10:30 (630)
  const slotStarts = [450, 465, 480, 495, 510, 525, 540, 555, 570, 585, 600, 615];
  
  stops.forEach((stop) => {
    // Generate realistic profile based on stop role
    const isMetro = stop.stop_id === 'S13';
    const isHub = stop.stop_id === 'S03';
    const isHostel = stop.stop_id === 'S08' || stop.stop_id === 'S09';
    const isAcademic = ['S04', 'S05', 'S06', 'S07'].includes(stop.stop_id);
    
    const slots = slotStarts.map((startMin) => {
      let baseLoad = 12;
      const progress = (startMin - 450) / 180; // 0 to 1
      
      if (isMetro) {
        // High surge 07:45-08:45
        baseLoad = 40 + Math.sin(progress * Math.PI) * 35;
      } else if (isHostel) {
        // High surge 08:00-08:45
        baseLoad = 30 + Math.sin(progress * Math.PI * 0.9) * 28;
      } else if (isHub) {
        // Consistently bustling transfer hub
        baseLoad = 35 + Math.sin(progress * Math.PI) * 30;
      } else if (isAcademic) {
        // Destination stop, moderate pickups
        baseLoad = 10 + Math.sin(progress * Math.PI) * 15;
      } else {
        baseLoad = 8 + Math.sin(progress * Math.PI) * 10;
      }
      
      const p50 = Math.round(baseLoad);
      const p80 = Math.round(p50 * 1.25);
      const p90 = Math.round(p50 * 1.45);
      const actual = Math.round(p50 * (0.95 + Math.sin(startMin) * 0.15));
      
      return {
        slot_start_min: startMin,
        slot_end_min: startMin + 15,
        p50_arrivals: p50,
        p80_arrivals: p80,
        p90_arrivals: p90,
        actual_arrivals: actual
      };
    });

    result[stop.stop_id] = {
      stop_id: stop.stop_id,
      date: "2026-10-14",
      slots
    };
  });

  return result;
}
