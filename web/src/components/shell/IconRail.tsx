import React, { useState } from 'react';
import {
  Map,
  Clock,
  AlertTriangle,
  Sparkles,
  Layers,
  GraduationCap,
  HelpCircle,
  ChevronRight
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

  const [isHovered, setIsHovered] = useState(false);

  const pendingRecsCount = recommendations.filter(r => !appliedRecIds.has(r.id)).length;
  const criticalAlertsCount = alerts.filter(a => a.severity === 'hard-risk').length;

  const navItems = [
    {
      id: 'map',
      label: 'Command Centre',
      icon: <Map size={18} />,
      badge: `${activeVehicles.length} buses`
    },
    {
      id: 'eta',
      label: 'ETA Arrival Board',
      icon: <Clock size={18} />,
      badge: 'p10–p90'
    },
    {
      id: 'demand',
      label: 'Demand & Alerts',
      icon: <AlertTriangle size={18} />,
      badge: alerts.length > 0 ? `${alerts.length}` : undefined,
      badgeColor: criticalAlertsCount > 0 ? 'var(--load-coral)' : 'var(--load-amber)'
    },
    {
      id: 'recommendations',
      label: 'Recommendations',
      icon: <Sparkles size={18} />,
      badge: pendingRecsCount > 0 ? `${pendingRecsCount}` : '0',
      badgeColor: pendingRecsCount > 0 ? 'var(--load-amber)' : 'var(--load-teal)'
    },
    {
      id: 'scenarios',
      label: 'Scenario Lab',
      icon: <Layers size={18} />,
      badge: 'S0–S3'
    },
    {
      id: 'student',
      label: 'Student View',
      icon: <GraduationCap size={18} />,
      badge: 'Mobile'
    }
  ];

  return (
    <aside
      className={`icon-rail ${isHovered ? 'expanded' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
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
              title={`${item.label} (${item.badge || ''})`}
            >
              <div className="rail-icon-wrapper">
                {item.icon}
                {item.badge && !isHovered && (
                  <span
                    className="rail-badge-pip"
                    style={{ backgroundColor: item.badgeColor || 'var(--route-r1)' }}
                  />
                )}
              </div>

              {isHovered && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', overflow: 'hidden' }}>
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.label}
                  </span>
                  {item.badge && (
                    <span
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        padding: '1px 5px',
                        borderRadius: 'var(--radius-xs)',
                        backgroundColor: 'var(--bg-hover)',
                        color: 'var(--text-secondary)'
                      }}
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

      {/* Rail Bottom Action: Quick Help */}
      <div className="rail-nav-group">
        <button
          className="rail-btn"
          onClick={toggleHelp}
          title={!isHovered ? "Help Centre & Glossary (?)" : undefined}
        >
          <div className="rail-icon-wrapper">
            <HelpCircle size={18} />
          </div>
          {isHovered && <span>Help & Docs</span>}
        </button>
      </div>
    </aside>
  );
};
