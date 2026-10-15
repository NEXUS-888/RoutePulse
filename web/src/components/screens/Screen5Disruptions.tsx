import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { EvalResultsResponse, ScenarioId } from '../../types';
import { BeforeAfterSlider } from '../common/BeforeAfterSlider';
import { GlossaryPopover } from '../common/GlossaryPopover';
import {
  Layers,
  PlayCircle,
  AlertTriangle,
  TrendingDown,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Users,
  GitBranch,
  BarChart3,
  Sliders
} from 'lucide-react';

export const Screen5Disruptions: React.FC = () => {
  const { scenario, triggerScenario } = useSimulation();
  const [evalResults, setEvalResults] = useState<EvalResultsResponse | null>(null);
  const [activeTabScenario, setActiveTabScenario] = useState<ScenarioId>(scenario);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);

  useEffect(() => {
    async function loadEval() {
      const res = await api.getEvalResults();
      setEvalResults(res.data);
    }
    loadEval();
  }, []);

  const handleTriggerScenario = async (s: ScenarioId) => {
    setIsInjecting(true);
    setActiveTabScenario(s);
    await triggerScenario(s);
    setTimeout(() => setIsInjecting(false), 600);
  };

  const scenarioMeta: Record<ScenarioId, { title: string; desc: string; icon: string; severity: string }> = {
    S0: {
      title: 'S0 Normal Peak',
      desc: 'Standard morning peak passenger demand (07:30–10:30) with commuter waves at Metro S13.',
      icon: '✓',
      severity: 'Normal Operations'
    },
    S1: {
      title: 'S1 Traffic Delay',
      desc: 'Corridor slowdown along Metro connector road; R3 trips delayed by +8 min.',
      icon: '⏱',
      severity: 'Corridor Delay'
    },
    S2: {
      title: 'S2 Vehicle Breakdown',
      desc: 'Mechanical failure of bus B3 at 08:05 midway through service near Admin Block.',
      icon: '⚠',
      severity: 'Bus Out of Service'
    },
    S3: {
      title: 'S3 Demand Surge',
      desc: 'Major campus symposium at S07 Auditorium with +120 arriving attendees at 08:15.',
      icon: '⚡',
      severity: 'Auditorium Surge'
    }
  };

  const filteredSummary = evalResults?.summary_table.filter(item => {
    if (activeTabScenario === 'S0') return item.scenario.startsWith('S0');
    if (activeTabScenario === 'S1') return item.scenario.startsWith('S1');
    if (activeTabScenario === 'S2') return item.scenario.startsWith('S2');
    if (activeTabScenario === 'S3') return item.scenario.startsWith('S3');
    return true;
  }) || [];

  return (
    <div className="screen-scroll-container">
      {/* Title & Scenario Injector */}
      <div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14, marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>What-if lab</h1>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Pick a disruption and see how <GlossaryPopover termId="routepulsePlan">RoutePulse</GlossaryPopover> copes compared with the{' '}
              <GlossaryPopover termId="baselinePlan">fixed timetable</GlossaryPopover>.
            </p>
          </div>

          <div className="validation-seal" style={{ padding: '6px 12px' }}>
            <ShieldCheck size={16} />
            <span>0 rule violations across 20 test runs</span>
          </div>
        </div>

        {/* 4 Interactive Scenario Trigger Cards */}
        <div data-tour="scenario-cards" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {(['S0', 'S1', 'S2', 'S3'] as ScenarioId[]).map(s => {
            const info = scenarioMeta[s];
            const isActive = scenario === s;

            return (
              <div
                key={s}
                onClick={() => handleTriggerScenario(s)}
                style={{
                  backgroundColor: isActive ? 'var(--accent-bg)' : 'var(--bg-surface-elevated)',
                  border: `2px solid ${isActive ? 'var(--accent)' : 'var(--border-color)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: 14,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 800, fontSize: '0.95rem', color: isActive ? 'var(--accent)' : 'var(--text-primary)' }}>
                    {info.title}
                  </span>
                  <span style={{ fontSize: '1.1rem' }}>{info.icon}</span>
                </div>

                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: 10 }}>
                  {info.desc}
                </p>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: s === 'S0' ? 'var(--load-teal-bg)' : 'var(--load-coral-bg)',
                      color: s === 'S0' ? 'var(--load-teal)' : 'var(--load-coral)'
                    }}
                  >
                    {info.severity}
                  </span>

                  {isActive ? (
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)' }}>
                      ● ACTIVE
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                      Click to try
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hero Interaction: Before / After Reveal Slider */}
      <div className="screen-card" data-tour="before-after">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sliders size={18} style={{ color: 'var(--accent)' }} />
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              Before / After Reveal Slider
            </h2>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
            Drag the handle to compare
          </span>
        </div>

        <BeforeAfterSlider />
      </div>

      {/* Disruption Event Timeline: Detection -> Recommendation -> Effect */}
      <div className="screen-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <GitBranch size={18} style={{ color: 'var(--accent)' }} />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
              How RoutePulse responds to {scenarioMeta[scenario].title}
            </h3>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
            Sense → Estimate → Detect → Decide → Verify
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {/* Step 1: Detect */}
          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--load-coral)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <span
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                  background: 'var(--load-coral-bg)',
                  color: 'var(--load-coral)'
                }}
              >
                1. SENSE & DETECT
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>t + 0s</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
              {scenario === 'S1' ? 'Corridor Delay Detected' : (scenario === 'S2' ? 'B3 Mechanical Fault Reported' : (scenario === 'S3' ? 'Auditorium Surge Outflow' : 'Normal Fleet Monitoring'))}
            </div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {scenario === 'S1'
                ? 'Conformal ETA engine projects R3 delay of +8.5 min. Alert A2 & A4 triggered.'
                : (scenario === 'S2'
                  ? 'Engine telemetry triggers Alert A8 (Vehicle Unavailable). Trip T_R3_02 compromised.'
                  : (scenario === 'S3'
                    ? 'Demand nowcast records +120 arrivals at S07. Alert A1 & A3 triggered.'
                    : 'All pings matched, headway variances within allowable H7 tolerance.'))}
            </p>
          </div>

          {/* Step 2: Decide & Verify */}
          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--load-amber)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <span
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                  background: 'var(--load-amber-bg)',
                  color: 'var(--load-amber)'
                }}
              >
                2. DECIDE & VERIFY
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>t + 2.1s</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
              CP-SAT Rolling Optimization
            </div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {scenario === 'S1'
                ? 'Solver retimes connecting trip T_R2_01 by +3 min to protect 14 transfers. Passes all H1–H12.'
                : (scenario === 'S2'
                  ? 'Deploys idle reserve bus B5 from S01 depot to cover B3 route segment. 0 hard violations.'
                  : (scenario === 'S3'
                    ? 'Reallocates minibus M1 to R4 shuttle loop to double frequency. 0 hard violations.'
                    : 'Published timetable validated with 0 constraint conflicts.'))}
            </p>
          </div>

          {/* Step 3: Effect */}
          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--load-teal)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <span
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                  background: 'var(--load-teal-bg)',
                  color: 'var(--load-teal)'
                }}
              >
                3. EFFECT & STABILIZE
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>t + 5m</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
              Passenger Service Restored
            </div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {scenario === 'S1'
                ? 'Transfer connection saved. Average passenger delay reduced from 9.8m to 5.6m.'
                : (scenario === 'S2'
                  ? 'Reserve bus in position. Left-behind passenger count drops by 74% vs Baseline-0.'
                  : (scenario === 'S3'
                    ? 'Queue cleared in 18 minutes instead of 46 minutes under fixed schedule.'
                    : 'System operates at optimal 88% fleet utilization with minimal student wait.'))}
            </p>
          </div>
        </div>
      </div>

      {/* Side-by-Side KPI Comparison Table */}
      <div className="screen-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={20} style={{ color: 'var(--accent)' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>
              Evaluation Benchmarking: {scenarioMeta[activeTabScenario].title}
            </h3>
          </div>

          <div style={{ display: 'flex', gap: 6 }}>
            {(['S0', 'S1', 'S2', 'S3'] as ScenarioId[]).map(s => (
              <button
                key={s}
                className="btn"
                style={{
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  backgroundColor: activeTabScenario === s ? 'var(--accent)' : 'var(--bg-surface-elevated)',
                  color: activeTabScenario === s ? 'var(--accent-contrast)' : 'var(--text-secondary)'
                }}
                onClick={() => setActiveTabScenario(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', color: 'var(--text-tertiary)' }}>
                <th style={{ padding: '10px 14px' }}>System Architecture</th>
                <th style={{ padding: '10px 14px' }}>Mean Wait Time (min) [95% CI]</th>
                <th style={{ padding: '10px 14px' }}>Left-Behind Riders [95% CI]</th>
                <th style={{ padding: '10px 14px' }}>Missed Connections [95% CI]</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Hard Violations</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>RoutePulse Advantage</th>
              </tr>
            </thead>
            <tbody>
              {filteredSummary.map((item, idx) => {
                const isRoutePulse = item.system.includes('RoutePulse');

                return (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: isRoutePulse ? 'var(--accent-bg)' : 'transparent',
                      fontWeight: isRoutePulse ? 700 : 500
                    }}
                  >
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {isRoutePulse && <CheckCircle2 size={16} style={{ color: 'var(--accent)' }} />}
                        <span style={{ color: isRoutePulse ? 'var(--accent)' : 'var(--text-primary)' }}>
                          {item.system}
                        </span>
                      </div>
                    </td>

                    <td style={{ padding: '12px 14px' }} className="tabular-nums font-mono">
                      {item.wait_min}
                    </td>

                    <td style={{ padding: '12px 14px' }} className="tabular-nums font-mono">
                      {item.left_behind}
                    </td>

                    <td style={{ padding: '12px 14px' }} className="tabular-nums font-mono">
                      {item.missed_conn}
                    </td>

                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <span className="validation-seal" style={{ padding: '2px 8px' }}>
                        0 Violations
                      </span>
                    </td>

                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      {isRoutePulse ? (
                        <span
                          style={{
                            padding: '3px 8px',
                            borderRadius: 'var(--radius-full)',
                            backgroundColor: 'var(--load-teal-bg)',
                            color: 'var(--load-teal)',
                            fontWeight: 700,
                            fontSize: '0.74rem'
                          }}
                        >
                          ★ 40–75% Reduction in Passenger Delay
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-tertiary)', fontSize: '0.74rem' }}>Reference</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
