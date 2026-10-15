import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import { formatTimeMin } from '../../utils/geo';
import { GlossaryPopover } from '../common/GlossaryPopover';
import type { Alert } from '../../types';
import {
  BarChart2,
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldAlert,
  Users,
  MapPin,
  Clock,
  Layers,
  Sparkles
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
    capacity: number;
  }>({
    stopId: 'S13',
    slotStart: 465,
    p50: 58,
    p80: 74,
    p90: 82,
    actual: 71,
    capacity: 60
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
      {/* Screen Title & Severity Filter Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>
            Crowding
          </h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            Expected passengers per stop in 15-minute slots, against platform capacity (
            <GlossaryPopover termId="loadFactor">P80 estimate</GlossaryPopover>). Only busy cells are coloured.
          </p>
        </div>

        {/* Severity Filter Toggle */}
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className="btn"
            style={{
              padding: '4px 11px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: severityFilter === 'all' ? 'var(--accent)' : 'var(--bg-surface-elevated)',
              color: severityFilter === 'all' ? 'var(--accent-contrast)' : 'var(--text-secondary)'
            }}
            onClick={() => setSeverityFilter('all')}
          >
            All Bottlenecks ({alerts.length})
          </button>
          <button
            className="btn"
            style={{
              padding: '4px 11px',
              fontSize: '0.75rem',
              fontWeight: 600,
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

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16, alignItems: 'start' }}>
        {/* Left Column: Demand Matrix + Sizing Inspector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Matrix Card */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: '0.92rem', fontWeight: 800 }}>
                  Station Platform Demand Matrix (14 Stops × 15-min Slots)
                </span>
                <span style={{ fontSize: '0.68rem', padding: '1px 6px', background: 'var(--bg-hover)', color: 'var(--text-tertiary)', borderRadius: 'var(--radius-xs)', fontFamily: 'var(--font-mono)' }}>
                  P80 Sizing Band
                </span>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                Click cell to inspect quantile distribution
              </span>
            </div>

            {/* Matrix Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.74rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-tertiary)', width: '145px', fontWeight: 700 }}>
                      Station (Cap)
                    </th>
                    {timeSlots.map(t => {
                      const isCurrentSlot = Math.abs(simTimeMin - t) < 7.5;
                      return (
                        <th
                          key={t}
                          style={{
                            padding: '6px 4px',
                            textAlign: 'center',
                            color: isCurrentSlot ? 'var(--accent)' : 'var(--text-tertiary)',
                            fontWeight: isCurrentSlot ? 800 : 600,
                            backgroundColor: isCurrentSlot ? 'var(--accent-bg)' : 'transparent',
                            borderTop: isCurrentSlot ? '2px solid var(--accent)' : 'none',
                            fontFamily: 'var(--font-mono)',
                            letterSpacing: '0.02em'
                          }}
                        >
                          {formatTimeMin(t)}
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {network?.stops.map((stop, sIdx) => {
                    const stopDemand = allDemand[stop.stop_id];
                    const capacity = stop.capacity_waiting || 40;

                    return (
                      <tr
                        key={stop.stop_id}
                        style={{
                          borderBottom: '1px solid var(--border-subtle)',
                          backgroundColor: sIdx % 2 === 0 ? 'transparent' : 'var(--border-subtle)'
                        }}
                      >
                        <td style={{ padding: '6px 8px', fontWeight: 600 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span
                              style={{
                                color: stop.is_hub
                                  ? 'var(--accent-hub)'
                                  : stop.stop_id === 'S13'
                                  ? 'var(--accent-metro)'
                                  : 'var(--text-primary)',
                                fontWeight: stop.is_hub ? 800 : 600,
                                fontSize: '0.78rem'
                              }}
                            >
                              {stop.stop_id} {stop.name}
                            </span>
                            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                              ({capacity})
                            </span>
                          </div>
                        </td>

                        {timeSlots.map(slotTime => {
                          const slotData = stopDemand?.slots.find(s => s.slot_start_min === slotTime);
                          const p80 = slotData?.p80_arrivals || 20;
                          const ratio = p80 / capacity;
                          const isCurrentSlot = Math.abs(simTimeMin - slotTime) < 7.5;

                          // Continuous, authoritative transit color mapping
                          let cellBg = 'var(--bg-surface-elevated)';
                          let cellColor = 'var(--text-secondary)';
                          let cellWeight = 500; // calm cells stay quiet so the problems pop
                          let cellBorder = '1px solid transparent';

                          if (ratio >= 1.15) {
                            cellBg = 'var(--load-coral-bg)';
                            cellColor = 'var(--load-coral)';
                            cellBorder = '1px solid var(--load-coral-border)';
                            cellWeight = 700;
                          } else if (ratio >= 0.85) {
                            cellBg = 'var(--load-amber-bg)';
                            cellColor = 'var(--load-amber)';
                            cellBorder = '1px solid var(--load-amber-border)';
                            cellWeight = 700;
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
                                    actual: slotData.actual_arrivals,
                                    capacity
                                  });
                                }
                              }}
                              style={{
                                padding: '4px 2px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                backgroundColor: isSelected ? 'var(--accent)' : cellBg,
                                color: isSelected ? 'var(--accent-contrast)' : cellColor,
                                fontWeight: isSelected ? 700 : cellWeight,
                                borderRadius: 'var(--radius-xs)',
                                border: isSelected ? '2px solid var(--text-primary)' : isCurrentSlot ? '1px dashed var(--accent)' : cellBorder,
                                fontFamily: 'var(--font-mono)',
                                transition: 'all 120ms ease'
                              }}
                              title={`${stop.name} @ ${formatTimeMin(slotTime)}: P80=${p80} pax vs Cap=${capacity} (${Math.round(ratio * 100)}%)`}
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

            {/* Heatmap Legend Strip */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: 12,
                paddingTop: 10,
                borderTop: '1px solid var(--border-subtle)',
                fontSize: '0.72rem',
                color: 'var(--text-secondary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span style={{ fontWeight: 600, color: 'var(--text-tertiary)' }}>
                  Key
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 10, backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-strong)', borderRadius: 2 }} />
                  <span>Under 85% of capacity</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 10, backgroundColor: 'var(--load-amber-bg)', border: '1px solid var(--load-amber-border)', borderRadius: 2 }} />
                  <span>85–115% busy</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 10, backgroundColor: 'var(--load-coral-bg)', border: '1px solid var(--load-coral-border)', borderRadius: 2 }} />
                  <span>Over 115% overload risk</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <span>Dashed outline = current time</span>
              </div>
            </div>
          </div>

          {/* Sizing Quantile Inspector Strip (Single Solari Banner instead of 4 separate cards) */}
          {selectedCell && (
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 14,
                boxShadow: 'var(--shadow-sm)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 'var(--radius-xs)',
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)'
                  }}
                >
                  <BarChart2 size={16} />
                </div>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.88rem' }}>
                    {selectedCell.stopId} — {network?.stops.find(s => s.stop_id === selectedCell.stopId)?.name}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    Slot Window: {formatTimeMin(selectedCell.slotStart)} – {formatTimeMin(selectedCell.slotStart + 15)} (15-min horizon)
                  </div>
                </div>
              </div>

              {/* Quantiles Solari Strip */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', fontWeight: 700, textTransform: 'uppercase' }}>
                    P50 Expected
                  </div>
                  <div className="tabular-nums font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {selectedCell.p50} <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--load-amber-bg)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--load-amber-border)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--load-amber)', fontWeight: 700, textTransform: 'uppercase' }}>
                    P80 Sizing Band
                  </div>
                  <div className="tabular-nums font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--load-amber)' }}>
                    {selectedCell.p80} <span style={{ fontSize: '0.7rem' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--load-coral-bg)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--load-coral-border)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--load-coral)', fontWeight: 700, textTransform: 'uppercase' }}>
                    P90 Worst-Case
                  </div>
                  <div className="tabular-nums font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--load-coral)' }}>
                    {selectedCell.p90} <span style={{ fontSize: '0.7rem' }}>pax</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface-elevated)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Platform Saturation
                  </div>
                  <div className="tabular-nums font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: selectedCell.p80 > selectedCell.capacity ? 'var(--load-coral)' : 'var(--load-teal)' }}>
                    {Math.round((selectedCell.p80 / selectedCell.capacity) * 100)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Active Bottlenecks & Anomaly Alerts A1–A8 */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <div data-tour="bottlenecks" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={18} style={{ color: 'var(--load-coral)' }} />
              <span style={{ fontSize: '0.92rem', fontWeight: 800 }}>Active Bottlenecks ({filteredAlerts.length})</span>
            </div>
            <button
              className="btn btn-outline"
              onClick={() => setActiveScreen('recommendations')}
              style={{ padding: '2px 8px', fontSize: '0.7rem', gap: 4 }}
              title="Go to AI Operator Recommendations to resolve bottlenecks"
            >
              <Sparkles size={12} style={{ color: 'var(--load-amber)' }} />
              <span>Fix Plan</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: '640px', overflowY: 'auto' }}>
            {filteredAlerts.map(alert => {
              const isHard = alert.severity === 'hard-risk';

              return (
                <div
                  key={alert.alert_id}
                  onClick={() => handleAlertClick(alert)}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: `1px solid ${isHard ? 'var(--load-coral-border)' : 'var(--border-color)'}`,
                    borderLeft: `3px solid ${isHard ? 'var(--load-coral)' : 'var(--load-amber)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 5,
                    cursor: 'pointer',
                    transition: 'all 120ms ease'
                  }}
                  className="bottleneck-card"
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          padding: '1px 5px',
                          borderRadius: 'var(--radius-xs)',
                          background: isHard ? 'var(--load-coral-bg)' : 'var(--load-amber-bg)',
                          color: isHard ? 'var(--load-coral)' : 'var(--load-amber)',
                          fontWeight: 800,
                          fontSize: '0.7rem',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        {alert.code}
                      </span>
                      <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                        {alert.title}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      {formatTimeMin(alert.time_min)}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', lineHeight: 1.35, margin: 0 }}>
                    {alert.detail}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 3, paddingTop: 5, borderTop: '1px solid var(--border-subtle)' }}>
                    <span style={{ fontSize: '0.7rem', color: isHard ? 'var(--load-coral)' : 'var(--text-secondary)', fontWeight: 600 }}>
                      {alert.pax_affected} pax affected
                    </span>

                    <button
                      className="btn"
                      onClick={e => {
                        e.stopPropagation();
                        handleHighlightOnMap(alert);
                      }}
                      style={{ padding: '2px 7px', fontSize: '0.68rem', gap: 3 }}
                    >
                      <span>Show on Map</span>
                      <ArrowRight size={10} />
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
