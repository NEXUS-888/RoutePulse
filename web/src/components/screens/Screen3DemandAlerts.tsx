import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import { formatTimeMin, getLoadColor } from '../../utils/geo';
import { GlossaryPopover } from '../common/GlossaryPopover';
import { EmptyState } from '../common/StateViews';
import type { Alert } from '../../types';
import {
  BarChart2,
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldAlert,
  Users,
  MapPin,
  Clock
} from 'lucide-react';

export const Screen3DemandAlerts: React.FC = () => {
  const {
    network,
    alerts,
    setHighlightedEntity,
    setActiveScreen,
    simTimeMin,
    setSelectedEntity
  } = useSimulation();

  const [selectedCell, setSelectedCell] = useState<{
    stopId: string;
    slotStart: number;
    p50: number;
    p80: number;
    p90: number;
    actual?: number;
  } | null>({
    stopId: 'S13',
    slotStart: 465,
    p50: 58,
    p80: 74,
    p90: 82,
    actual: 71
  });

  const [severityFilter, setSeverityFilter] = useState<'all' | 'hard-risk' | 'soft'>('all');

  const allDemand = api.getAllDemandData();
  const timeSlots = [450, 465, 480, 495, 510, 525, 540, 555, 570, 585, 600, 615];

  const filteredAlerts = alerts.filter(a => {
    if (severityFilter === 'all') return true;
    return a.severity === severityFilter;
  });

  const handleAlertClick = (alert: Alert) => {
    setSelectedEntity({
      type: 'alert',
      id: alert.alert_id,
      data: alert
    });
  };

  const handleHighlightOnMap = (alert: Alert) => {
    setHighlightedEntity({
      type: alert.entity_type,
      id: alert.entity_id
    });
    setActiveScreen('map');
  };

  return (
    <div className="screen-scroll-container">
      {/* Header Card */}
      <div className="screen-card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
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
                color: 'var(--load-amber)'
              }}
            >
              <Flame size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                Demand Heatmap & Anomaly Alerts (A1–A8)
              </h1>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Comparing <GlossaryPopover termId="loadFactor">P80 arrival demand</GlossaryPopover> vs station platform capacities with proactive bottleneck detection
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className="btn"
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                background: severityFilter === 'all' ? 'var(--route-r1)' : 'var(--bg-surface-elevated)',
                color: severityFilter === 'all' ? '#FFFFFF' : 'var(--text-secondary)'
              }}
              onClick={() => setSeverityFilter('all')}
            >
              All Alerts ({alerts.length})
            </button>
            <button
              className="btn"
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                background: severityFilter === 'hard-risk' ? 'var(--load-coral-bg)' : 'var(--bg-surface-elevated)',
                color: severityFilter === 'hard-risk' ? 'var(--load-coral)' : 'var(--text-secondary)',
                border: severityFilter === 'hard-risk' ? '1px solid var(--load-coral-border)' : '1px solid var(--border-color)'
              }}
              onClick={() => setSeverityFilter('hard-risk')}
            >
              Critical Risk ({alerts.filter(a => a.severity === 'hard-risk').length})
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Heatmap + Alert Drawer */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: 20, alignItems: 'start' }}>
        {/* Left: Heatmap Matrix & Quantile Distribution */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="screen-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontSize: '0.92rem', fontWeight: 700 }}>
                Station Platform Demand Matrix (14 Stops × 15-min Slots)
              </span>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-tertiary)' }}>
                Click cell to inspect quantile distribution
              </span>
            </div>

            {/* Matrix Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.74rem' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-tertiary)', width: '130px' }}>
                      Station
                    </th>
                    {timeSlots.map(t => (
                      <th
                        key={t}
                        style={{
                          padding: '6px 4px',
                          textAlign: 'center',
                          color: Math.abs(simTimeMin - t) < 15 ? 'var(--route-r1)' : 'var(--text-tertiary)',
                          fontWeight: Math.abs(simTimeMin - t) < 15 ? 700 : 500,
                          backgroundColor: Math.abs(simTimeMin - t) < 15 ? 'var(--route-r1-bg)' : 'transparent',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        {formatTimeMin(t)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {network?.stops.map(stop => {
                    const stopDemand = allDemand[stop.stop_id];
                    const capacity = stop.capacity_waiting || 40;

                    return (
                      <tr key={stop.stop_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 600 }}>
                          <span style={{ color: stop.is_hub ? 'var(--accent-hub)' : 'var(--text-primary)' }}>
                            {stop.stop_id} {stop.name}
                          </span>
                        </td>

                        {timeSlots.map(slotTime => {
                          const slotData = stopDemand?.slots.find(s => s.slot_start_min === slotTime);
                          const p80 = slotData?.p80_arrivals || 20;
                          const ratio = p80 / capacity;

                          let bgColor = 'var(--load-teal-bg)';
                          let textColor = 'var(--load-teal)';
                          if (ratio > 1.2) {
                            bgColor = 'var(--load-coral-bg)';
                            textColor = 'var(--load-coral)';
                          } else if (ratio > 0.85) {
                            bgColor = 'var(--load-amber-bg)';
                            textColor = 'var(--load-amber)';
                          }

                          const isSelected = selectedCell?.stopId === stop.stop_id && selectedCell?.slotStart === slotTime;

                          return (
                            <td
                              key={slotTime}
                              onClick={() => {
                                if (slotData) {
                                  setSelectedCell({
                                    stopId: stop.stop_id,
                                    slotStart: slotTime,
                                    p50: slotData.p50_arrivals,
                                    p80: slotData.p80_arrivals,
                                    p90: slotData.p90_arrivals,
                                    actual: slotData.actual_arrivals
                                  });
                                }
                              }}
                              style={{
                                padding: '5px 2px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                backgroundColor: isSelected ? 'var(--route-r1)' : bgColor,
                                color: isSelected ? '#FFFFFF' : textColor,
                                fontWeight: 700,
                                borderRadius: 3,
                                border: isSelected ? '2px solid white' : '1px solid transparent',
                                fontFamily: 'var(--font-mono)'
                              }}
                              title={`${stop.name} @ ${formatTimeMin(slotTime)}: P80=${p80} pax vs Cap=${capacity}`}
                            >
                              {Math.round(p80)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Redundant Legend */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 14, fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              <span style={{ fontWeight: 600 }}>Capacity Load Ratio:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, backgroundColor: 'var(--load-teal-bg)', border: '1px solid var(--load-teal-border)', borderRadius: 2 }} />
                <span>&lt;85% (Optimal)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, backgroundColor: 'var(--load-amber-bg)', border: '1px solid var(--load-amber-border)', borderRadius: 2 }} />
                <span>85–100% (High Load)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, backgroundColor: 'var(--load-coral-bg)', border: '1px solid var(--load-coral-border)', borderRadius: 2 }} />
                <span>&gt;100% (Over Capacity Risk)</span>
              </div>
            </div>
          </div>

          {/* Quantile Sizing Inspector for Selected Cell */}
          {selectedCell && (
            <div className="screen-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BarChart2 size={16} style={{ color: 'var(--route-r1)' }} />
                  <span style={{ fontSize: '0.9rem', fontWeight: 700 }}>
                    Forecast Quantiles: {selectedCell.stopId} ({network?.stops.find(s => s.stop_id === selectedCell.stopId)?.name}) at {formatTimeMin(selectedCell.slotStart)}
                  </span>
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>15-min Horizon</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>P50 EXPECTED</span>
                  <div className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {selectedCell.p50} <span style={{ fontSize: '0.75rem' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--load-amber)' }}>P80 SIZING BAND</span>
                  <div className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-amber)' }}>
                    {selectedCell.p80} <span style={{ fontSize: '0.75rem' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--load-coral)' }}>P90 WORST CASE</span>
                  <div className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--load-coral)' }}>
                    {selectedCell.p90} <span style={{ fontSize: '0.75rem' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface-elevated)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--route-r1)' }}>ACTUAL OBSERVED</span>
                  <div className="tabular-nums font-display" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--route-r1)' }}>
                    {selectedCell.actual ?? '—'} <span style={{ fontSize: '0.75rem' }}>pax</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Alert Cards List A1–A8 */}
        <div className="screen-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={18} style={{ color: 'var(--load-coral)' }} />
              <span style={{ fontSize: '0.95rem', fontWeight: 700 }}>Active Bottlenecks ({filteredAlerts.length})</span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: '680px', overflowY: 'auto' }}>
            {filteredAlerts.map(alert => {
              const isHard = alert.severity === 'hard-risk';

              return (
                <div
                  key={alert.alert_id}
                  onClick={() => handleAlertClick(alert)}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: `1px solid ${isHard ? 'var(--load-coral-border)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          padding: '2px 6px',
                          borderRadius: 'var(--radius-xs)',
                          background: isHard ? 'var(--load-coral-bg)' : 'var(--load-amber-bg)',
                          color: isHard ? 'var(--load-coral)' : 'var(--load-amber)',
                          fontWeight: 700,
                          fontSize: '0.72rem',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        {alert.code}
                      </span>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{alert.title}</span>
                    </div>

                    <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      {formatTimeMin(alert.time_min)}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {alert.detail}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4, paddingTop: 6, borderTop: '1px solid var(--border-subtle)' }}>
                    <span style={{ fontSize: '0.72rem', color: isHard ? 'var(--load-coral)' : 'var(--text-secondary)', fontWeight: 600 }}>
                      {alert.pax_affected} pax affected
                    </span>

                    <button
                      className="btn"
                      onClick={e => {
                        e.stopPropagation();
                        handleHighlightOnMap(alert);
                      }}
                      style={{ padding: '2px 7px', fontSize: '0.7rem', gap: 3 }}
                    >
                      <span>Show on Map</span>
                      <ArrowRight size={11} />
                    </button>
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
