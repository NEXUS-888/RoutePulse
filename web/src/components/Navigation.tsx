import React from 'react';
import {
  Map,
  Clock3,
  BarChart2,
  Sparkles,
  Layers,
  GraduationCap
} from 'lucide-react';
import { useSimulation } from '../context/SimulationContext';

export const Navigation: React.FC = () => {
  const { activeScreen, setActiveScreen, alerts, recommendations, appliedRecIds, activeVehicles } = useSimulation();

  const unappliedRecCount = recommendations.filter(r => !appliedRecIds.has(r.id)).length;
  const hardAlertsCount = alerts.filter(a => a.severity === 'hard-risk').length;

  const tabs = [
    {
      id: 'map',
      label: '1. Network Map & Replay',
      icon: <Map size={16} />,
      badge: `${activeVehicles.length} active`
    },
    {
      id: 'eta',
      label: '2. ETA Arrival Board',
      icon: <Clock3 size={16} />,
      badge: 'p10-p90'
    },
    {
      id: 'demand',
      label: '3. Demand & Alerts',
      icon: <BarChart2 size={16} />,
      badge: hardAlertsCount > 0 ? `${alerts.length} (${hardAlertsCount} critical)` : `${alerts.length}`
    },
    {
      id: 'recommendations',
      label: '4. Operator Recommendations',
      icon: <Sparkles size={16} />,
      badge: unappliedRecCount > 0 ? `${unappliedRecCount} pending` : 'All Applied'
    },
    {
      id: 'scenarios',
      label: '5. Scenario Simulator',
      icon: <Layers size={16} />,
      badge: 'S0–S3'
    },
    {
      id: 'student',
      label: '6. Student Planner (P1)',
      icon: <GraduationCap size={16} />,
      badge: 'Student View'
    }
  ];

  return (
    <nav className="nav-bar">
      {tabs.map(tab => {
        const isActive = activeScreen === tab.id;
        return (
          <button
            key={tab.id}
            className={`nav-tab ${isActive ? 'active' : ''}`}
            onClick={() => setActiveScreen(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.badge && <span className="nav-badge">{tab.badge}</span>}
          </button>
        );
      })}
    </nav>
  );
};
