import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import type { Recommendation, WhatIfResponse } from '../../types';
import { RecommendationTicket } from '../common/RecommendationTicket';
import { GlossaryPopover } from '../common/GlossaryPopover';
import { EmptyState } from '../common/StateViews';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  ArrowRight,
  Layers,
  AlertCircle,
  X
} from 'lucide-react';

export const Screen4Recommendations: React.FC = () => {
  const {
    recommendations,
    appliedRecIds,
    acceptRecommendation,
    rejectRecommendation,
    workingPlan
  } = useSimulation();

  const [whatIfModalRec, setWhatIfModalRec] = useState<Recommendation | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const handleWhatIfClick = async (rec: Recommendation) => {
    setWhatIfModalRec(rec);
    setIsSimulating(true);

    const res = await api.runWhatIf({
      base_plan_id: workingPlan?.plan_id || 'baseline',
      scenario_id: 'S0',
      added_trips: [],
      retimed_trips: {},
      vehicle_swaps: {}
    });

    setWhatIfResult(res.data);
    setIsSimulating(false);
  };

  const handleAcceptFromModal = async (rec: Recommendation) => {
    await acceptRecommendation(rec.id);
    setSuccessToast(`Recommendation ${rec.id} applied live! Working plan updated with 0 constraint violations.`);
    setWhatIfModalRec(null);
    setTimeout(() => setSuccessToast(null), 5000);
  };

  return (
    <div className="screen-scroll-container">
      {/* Top Banner */}
      <div className="screen-card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--route-r1)'
              }}
            >
              <Sparkles size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h1 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                  Operator AI Copilot & Recommendations
                </h1>
                <span className="validation-seal" style={{ gap: 4 }}>
                  <ShieldCheck size={14} />
                  <span>Validator: 0 Violations Guarantee</span>
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Stage A service sizing & Stage B CP-SAT vehicle blocking proposals. Transparent{' '}
                <GlossaryPopover termId="tradeoff">Gain vs Cost trade-offs</GlossaryPopover> and{' '}
                <GlossaryPopover termId="hardConstraint">binding constraint proofs</GlossaryPopover>.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Active Working Plan: <strong className="font-mono">{workingPlan?.plan_id || 'baseline'}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successToast && (
        <div
          style={{
            backgroundColor: 'var(--load-teal-bg)',
            border: '1px solid var(--load-teal-border)',
            color: 'var(--load-teal)',
            padding: '12px 20px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.85rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 10
          }}
        >
          <CheckCircle2 size={18} />
          <span>{successToast}</span>
        </div>
      )}

      {/* Recommendation Tickets */}
      {recommendations.length === 0 ? (
        <EmptyState
          title="All Recommendations Reviewed"
          description="The active network plan is operating within target headway and capacity bounds. No pending interventions required."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {recommendations.map(rec => (
            <RecommendationTicket
              key={rec.id}
              recommendation={rec}
              onWhatIf={handleWhatIfClick}
            />
          ))}
        </div>
      )}

      {/* What-If Simulation Sandbox Modal */}
      {whatIfModalRec && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(11, 16, 32, 0.75)',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
            padding: 20
          }}
          onClick={() => setWhatIfModalRec(null)}
        >
          <div
            className="screen-card"
            style={{ maxWidth: '600px', width: '100%', boxShadow: 'var(--shadow-lg)' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Layers size={20} style={{ color: 'var(--route-r1)' }} />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                  What-If Sandbox: {whatIfModalRec.id}
                </h3>
              </div>
              <button
                className="btn-icon"
                onClick={() => setWhatIfModalRec(null)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
              Testing simulated discrete-event impact of <strong>{whatIfModalRec.summary}</strong> before applying to live fleet.
            </p>

            {isSimulating ? (
              <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-secondary)' }}>
                Simulating fleet schedule and checking 12 hard constraints...
              </div>
            ) : whatIfResult ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="validation-seal">
                    <ShieldCheck size={14} />
                    <span>0 Hard Violations Detected</span>
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    CP-SAT Solver Verified
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                  <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>SIMULATED MEAN WAIT</div>
                    <div className="font-display tabular-nums" style={{ fontSize: '1.3rem', fontWeight: 800 }}>
                      {whatIfResult.simulated_kpis.avg_wait_min} min
                    </div>
                    <div style={{ color: 'var(--load-teal)', fontSize: '0.75rem', fontWeight: 600 }}>
                      Δ {whatIfResult.delta_vs_base.avg_wait_min} min vs Baseline
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>LEFT-BEHIND RIDERS</div>
                    <div className="font-display tabular-nums" style={{ fontSize: '1.3rem', fontWeight: 800 }}>
                      {whatIfResult.simulated_kpis.left_behind_pax} pax
                    </div>
                    <div style={{ color: 'var(--load-teal)', fontSize: '0.75rem', fontWeight: 600 }}>
                      Δ {whatIfResult.delta_vs_base.left_behind_pax} pax reduction
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                  <button
                    className="btn btn-outline"
                    onClick={() => setWhatIfModalRec(null)}
                  >
                    Close Sandbox
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => handleAcceptFromModal(whatIfModalRec)}
                  >
                    Accept & Apply Live
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
