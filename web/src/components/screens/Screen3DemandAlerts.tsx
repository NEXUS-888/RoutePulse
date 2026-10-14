import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { api } from '../../api/client';
import { formatTimeMin, getLoadColor } from '../../utils/geo';
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
  const { network, alerts, setHighlightedEntity, setActiveScreen, simTimeMin } = useSimulation();
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
    setHighlightedEntity({
      type: alert.entity_type,
      id: alert.entity_id
    });
    setActiveScreen('map');
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 20 }}>
      {/* Left Column: Heatmap & Forecast Bands */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Heatmap Card */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Flame size={20} style={{ color: 'var(--accent-amber)' }} />
              <span>Campus Demand Heatmap (14 Stops × 15-min Slots)</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Click cell to inspect forecast distribution
            </div>
          </div>

          {/* Matrix Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-tertiary)', width: '130px' }}>
                    Stop
                  </th>
                  {timeSlots.map(t => (
                    <th
                      key={t}
                      style={{
                        padding: '6px 4px',
                        textAlign: 'center',
                        color: Math.abs(simTimeMin - t) < 15 ? 'var(--accent-blue)' : 'var(--text-tertiary)',
                        fontWeight: Math.abs(simTimeMin - t) < 15 ? 700 : 500,
                        backgroundColor: Math.abs(simTimeMin - t) < 15 ? 'var(--accent-blue-light)' : 'transparent'
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
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ color: stop.is_hub ? 'var(--accent-purple)' : 'var(--text-primary)' }}>
                            {stop.stop_id} {stop.name}
                          </span>
                        </div>
                      </td>

                      {timeSlots.map(slotTime => {
                        const slotData = stopDemand?.slots.find(s => s.slot_start_min === slotTime);
                        const p80 = slotData?.p80_arrivals || 20;
                        const ratio = p80 / capacity;

                        // Color scaling
                        let bgColor = 'rgba(16, 185, 129, 0.15)'; // light green
                        let textColor = '#10B981';
                        if (ratio > 1.3) {
                          bgColor = 'rgba(239, 68, 68, 0.55)'; // strong red
                          textColor = '#FFFFFF';
                        } else if (ratio > 1.0) {
                          bgColor = 'rgba(239, 68, 68, 0.3)'; // red warning
                          textColor = '#EF4444';
                        } else if (ratio > 0.75) {
                          bgColor = 'rgba(245, 158, 11, 0.3)'; // amber
                          textColor = '#F59E0B';
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
                              backgroundColor: isSelected ? 'var(--accent-blue)' : bgColor,
                              color: isSelected ? '#FFFFFF' : textColor,
                              fontWeight: 700,
                              borderRadius: 3,
                              border: isSelected ? '2px solid white' : '1px solid transparent'
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

          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 14, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            <span style={{ fontWeight: 600 }}>P80 Demand vs Stop Capacity Legend:</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 12, backgroundColor: 'rgba(16, 185, 129, 0.25)', borderRadius: 2 }} />
              <span>&lt;75% Normal</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 12, backgroundColor: 'rgba(245, 158, 11, 0.3)', borderRadius: 2 }} />
              <span>75–100% High</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 12, backgroundColor: 'rgba(239, 68, 68, 0.45)', borderRadius: 2 }} />
              <span>&gt;100% Capacity Risk</span>
            </div>
          </div>
        </div>

        {/* Selected Cell Forecast Band Inspector */}
        {selectedCell && (
          <div className="card">
            <div className="card-header">
              <div className="card-title" style={{ fontSize: '0.95rem' }}>
                <BarChart2 size={18} style={{ color: 'var(--accent-blue)' }} />
                <span>
                  Forecast Distribution: {selectedCell.stopId} ({network?.stops.find(s => s.stop_id === selectedCell.stopId)?.name}) at {formatTimeMin(selectedCell.slotStart)}
                </span>
              </div>
              <span className="badge badge-info">15-min Horizon</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 16 }}>
              <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>P50 EXPECTED</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>{selectedCell.p50} <span style={{ fontSize: '0.8rem' }}>pax</span></div>
              </div>
              <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>P80 SIZING BAND</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-amber)' }}>{selectedCell.p80} <span style={{ fontSize: '0.8rem' }}>pax</span></div>
              </div>
              <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>P90 WORST CASE</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-red)' }}>{selectedCell.p90} <span style={{ fontSize: '0.8rem' }}>pax</span></div>
              </div>
              <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>ACTUAL OBSERVED</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-blue)' }}>{selectedCell.actual ?? '—'} <span style={{ fontSize: '0.8rem' }}>pax</span></div>
              </div>
            </div>

            {/* Custom SVG Quantile Bar Chart */}
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Quantile Sizing vs Rated Vehicle Capacity (45 pax Bus)
              </div>
              <div style={{ position: 'relative', height: 26, backgroundColor: 'var(--bg-surface)', borderRadius: 4, overflow: 'hidden' }}>
                {/* Capacity Threshold Marker (45 pax) */}
                <div
                  style={{
                    position: 'absolute',
                    left: `${Math.min(100, (45 / 100) * 100)}%`,
                    height: '100%',
                    width: '2px',
                    backgroundColor: 'var(--accent-red)',
                    zIndex: 10
                  }}
                  title="Bus Capacity: 45 pax"
                />

                {/* P50 Bar */}
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    width: `${Math.min(100, (selectedCell.p50 / 100) * 100)}%`,
                    height: '100%',
                    backgroundColor: 'rgba(59, 130, 246, 0.6)'
                  }}
                />

                {/* P80 Extension */}
                <div
                  style={{
                    position: 'absolute',
                    left: `${(selectedCell.p50 / 100) * 100}%`,
                    width: `${Math.max(0, ((selectedCell.p80 - selectedCell.p50) / 100) * 100)}%`,
                    height: '100%',
                    backgroundColor: 'rgba(245, 158, 11, 0.6)'
                  }}
                />

                {/* P90 Extension */}
                <div
                  style={{
                    position: 'absolute',
                    left: `${(selectedCell.p80 / 100) * 100}%`,
                    width: `${Math.max(0, ((selectedCell.p90 - selectedCell.p80) / 100) * 100)}%`,
                    height: '100%',
                    backgroundColor: 'rgba(239, 68, 68, 0.6)'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: 4 }}>
                <span>0 pax</span>
                <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>Capacity Cutoff (45 pax)</span>
                <span>100 pax</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right Column: Alert Drawer A1 - A8 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="card">
          <div className="card-header" style={{ marginBottom: 10 }}>
            <div className="card-title">
              <ShieldAlert size={18} style={{ color: 'var(--accent-red)' }} />
              <span>System Alerts (A1–A8)</span>
            </div>

            <div style={{ display: 'flex', gap: 4 }}>
              <button
                className={`btn btn-outline ${severityFilter === 'all' ? 'active' : ''}`}
                style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                onClick={() => setSeverityFilter('all')}
              >
                All ({alerts.length})
              </button>
              <button
                className={`btn btn-outline ${severityFilter === 'hard-risk' ? 'active' : ''}`}
                style={{ padding: '3px 8px', fontSize: '0.72rem', color: 'var(--accent-red)' }}
                onClick={() => setSeverityFilter('hard-risk')}
              >
                Hard ({alerts.filter(a => a.severity === 'hard-risk').length})
              </button>
              <button
                className={`btn btn-outline ${severityFilter === 'soft' ? 'active' : ''}`}
                style={{ padding: '3px 8px', fontSize: '0.72rem', color: 'var(--accent-amber)' }}
                onClick={() => setSeverityFilter('soft')}
              >
                Soft ({alerts.filter(a => a.severity === 'soft').length})
              </button>
            </div>
          </div>

          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
            Sorted by severity and affected passenger count. Click any alert card to highlight the offending route or trip on the live campus map.
          </p>

          {/* Alert List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: '640px', overflowY: 'auto' }}>
            {filteredAlerts.map(alert => {
              const isHard = alert.severity === 'hard-risk';

              return (
                <div
                  key={alert.alert_id}
                  style={{
                    backgroundColor: 'var(--bg-surface-elevated)',
                    border: `1px solid ${isHard ? 'rgba(239, 68, 68, 0.4)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: 12,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: isHard ? 'var(--accent-red-light)' : 'var(--accent-amber-light)',
                          color: isHard ? 'var(--accent-red)' : 'var(--accent-amber)',
                          fontWeight: 700
                        }}
                      >
                        {alert.code}
                      </span>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{alert.title}</span>
                    </div>

                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        color: 'var(--text-tertiary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                    >
                      <Clock size={12} />
                      {formatTimeMin(alert.time_min)}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {alert.detail}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4, paddingTop: 6, borderTop: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Users size={12} />
                        <strong>{alert.pax_affected} pax affected</strong>
                      </span>
                      <span>Target: {alert.entity_id}</span>
                    </div>

                    <button
                      className="btn btn-outline"
                      style={{ padding: '3px 8px', fontSize: '0.72rem', gap: 4 }}
                      onClick={() => handleAlertClick(alert)}
                    >
                      <span>Highlight on Map</span>
                      <ArrowRight size={12} />
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
