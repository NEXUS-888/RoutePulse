import React from 'react';
import { Map, Clock, AlertTriangle, Sparkles, Layers, GraduationCap } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

/**
 * Primary navigation. Every destination is always labelled (no hover-to-discover tooltips),
 * and a count bubble appears only where something needs the operator's attention.
 */
export const IconRail: React.FC = () => {
  const { activeScreen, setActiveScreen, alerts, recommendations, appliedRecIds } = useSimulation();

  const pendingRecsCount = recommendations.filter(r => !appliedRecIds.has(r.id)).length;
  const criticalAlertsCount = alerts.filter(a => a.severity === 'hard-risk').length;

  const navItems = [
    { id: 'map', label: 'Live map', shortcut: '1', icon: <Map size={20} /> },
    { id: 'eta', label: 'Arrivals', shortcut: '2', icon: <Clock size={20} /> },
    {
      id: 'demand',
      label: 'Crowding',
      shortcut: '3',
      icon: <AlertTriangle size={20} />,
      count: alerts.length,
      countTone: criticalAlertsCount > 0 ? 'bad' : 'warn'
    },
    {
      id: 'recommendations',
      label: 'Suggestions',
      shortcut: '4',
      icon: <Sparkles size={20} />,
      count: pendingRecsCount,
      countTone: 'warn'
    },
    { id: 'scenarios', label: 'What-if', shortcut: '5', icon: <Layers size={20} /> },
    { id: 'student', label: 'Student app', shortcut: '6', icon: <GraduationCap size={20} /> }
  ];

  return (
    <nav className="icon-rail" aria-label="Primary navigation">
      {navItems.map(item => {
        const isActive = activeScreen === item.id;
        return (
          <button
            key={item.id}
            data-testid={`nav-${item.id}`}
            aria-label={item.label}
            aria-current={isActive ? 'page' : undefined}
            title={`${item.label} (${item.shortcut})`}
            className={`rail-btn ${isActive ? 'active' : ''}`}
            onClick={() => setActiveScreen(item.id)}
          >
            <span className="rail-icon-wrapper">
              {item.icon}
              {item.count ? (
                <span className={`rail-count ${item.countTone}`}>{item.count}</span>
              ) : null}
            </span>
            <span className="rail-label-text">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
