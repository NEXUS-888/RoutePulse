import React, { useState } from 'react';
import {
  Map,
  Clock,
  AlertTriangle,
  Sparkles,
  Layers,
  GraduationCap,
  HelpCircle,
  PanelLeft,
  PanelLeftClose
} from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export const IconRail: React.FC = () => {
  const {
    activeScreen,
    setActiveScreen,
    alerts,
    recommendations,
    appliedRecIds,
    activeVehicles,
    toggleHelp
  } = useSimulation();

  // Pinned mode: persistent docking without hover jitter or layout shifts
  const [isPinned, setIsPinned] = useState<boolean>(() => {
    return localStorage.getItem('routepulse_rail_pinned') === 'true';
  });

  const togglePin = () => {
    setIsPinned(prev => {
      const next = !prev;
      localStorage.setItem('routepulse_rail_pinned', String(next));
      return next;
    });
  };

  const pendingRecsCount = recommendations.filter(r => !appliedRecIds.has(r.id)).length;
  const criticalAlertsCount = alerts.filter(a => a.severity === 'hard-risk').length;

  const navItems = [
    {
      id: 'map',
      label: 'Command Centre',
      shortcut: '1',
      icon: <Map size={18} />,
      badge: `${activeVehicles.length} active`
    },
    {
      id: 'eta',
      label: 'ETA Arrival Board',
      shortcut: '2',
      icon: <Clock size={18} />,
      badge: 'p10–p90'
    },
    {
      id: 'demand',
      label: 'Demand & Alerts',
      shortcut: '3',
      icon: <AlertTriangle size={18} />,
      badge: alerts.length > 0 ? `${alerts.length}` : undefined,
      badgeColor: criticalAlertsCount > 0 ? 'var(--load-coral)' : 'var(--load-amber)'
    },
    {
      id: 'recommendations',
      label: 'Recommendations',
      shortcut: '4',
      icon: <Sparkles size={18} />,
      badge: pendingRecsCount > 0 ? `${pendingRecsCount}` : '0',
      badgeColor: pendingRecsCount > 0 ? 'var(--load-amber)' : 'var(--load-teal)'
    },
    {
      id: 'scenarios',
      label: 'Scenario Lab',
      shortcut: '5',
      icon: <Layers size={18} />,
      badge: 'S0–S3'
    },
    {
      id: 'student',
      label: 'Student View',
      shortcut: '6',
      icon: <GraduationCap size={18} />,
      badge: 'Mobile'
    }
  ];

  return (
    <aside
      className={`icon-rail ${isPinned ? 'pinned' : ''}`}
      aria-label="Primary Navigation Rail"
    >
      <div className="rail-nav-group">
        {navItems.map(item => {
          const isActive = activeScreen === item.id;
          return (
            <button
              key={item.id}
              data-testid={`nav-${item.id}`}
              aria-label={item.label}
              className={`rail-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveScreen(item.id)}
            >
              <div className="rail-icon-wrapper">
                {item.icon}
                {item.badge && !isPinned && (
                  <span
                    className="rail-badge-pip"
                    style={{ backgroundColor: item.badgeColor || 'var(--route-r1)' }}
                  />
                )}
              </div>

              {/* Pinned inline view: stable text and badge */}
              {isPinned && (
                <div className="rail-inline-content">
                  <span className="rail-label-text">{item.label}</span>
                  {item.badge && (
                    <span
                      className="rail-badge-chip"
                      style={{ color: item.badgeColor }}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}

              {/* Floating flyout tooltip when collapsed: zero layout reflow */}
              {!isPinned && (
                <div className="rail-flyout-tooltip" role="tooltip">
                  <span className="tooltip-title">{item.label}</span>
                  <kbd className="tooltip-kbd">{item.shortcut}</kbd>
                  {item.badge && (
                    <span
                      className="tooltip-badge"
                      style={{ color: item.badgeColor }}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Rail Bottom Actions: Dock Toggle & Quick Help */}
      <div className="rail-nav-group rail-bottom-group">
        <button
          className="rail-btn"
          onClick={toggleHelp}
          aria-label="Help Centre & Glossary"
        >
          <div className="rail-icon-wrapper">
            <HelpCircle size={18} />
          </div>
          {isPinned ? (
            <div className="rail-inline-content">
              <span className="rail-label-text">Help & Docs</span>
              <kbd className="tooltip-kbd">?</kbd>
            </div>
          ) : (
            <div className="rail-flyout-tooltip" role="tooltip">
              <span className="tooltip-title">Help Centre</span>
              <kbd className="tooltip-kbd">?</kbd>
            </div>
          )}
        </button>

        <button
          className="rail-btn rail-dock-btn"
          onClick={togglePin}
          title={isPinned ? 'Collapse rail' : 'Dock & expand sidebar'}
          aria-label={isPinned ? 'Collapse rail' : 'Dock & expand sidebar'}
        >
          <div className="rail-icon-wrapper">
            {isPinned ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
          </div>
          {isPinned ? (
            <span className="rail-label-text" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              Collapse Rail
            </span>
          ) : (
            <div className="rail-flyout-tooltip" role="tooltip">
              <span className="tooltip-title">Pin Sidebar</span>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
};
