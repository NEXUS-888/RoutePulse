import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { StatusRibbon } from './StatusRibbon';
import { IconRail } from './IconRail';
import { TimeDeck } from './TimeDeck';
import { InspectorDrawer } from './InspectorDrawer';
import { AlertTriangle, ArrowRight } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { activeDisruptionAlert, setActiveScreen } = useSimulation();

  return (
    <div className="app-container">
      {/* Zone Top: Status Ribbon */}
      <StatusRibbon />

      {/* Disruption Warning Strip */}
      {activeDisruptionAlert && (
        <div className="disruption-banner">
          <div className="banner-left">
            <AlertTriangle size={16} style={{ color: 'var(--load-coral)' }} />
            <span>{activeDisruptionAlert}</span>
          </div>

          <button
            className="btn btn-outline"
            style={{ padding: '2px 8px', fontSize: '0.72rem', gap: 4 }}
            onClick={() => setActiveScreen('scenarios')}
          >
            <span>Scenario Lab & Re-Opt</span>
            <ArrowRight size={12} />
          </button>
        </div>
      )}

      {/* Main Body: Rail (Left) + Stage (Center) + Inspector (Right) */}
      <div className="app-body-layout">
        <IconRail />

        <main className="stage-container" id="main-stage">
          {children}
        </main>

        <InspectorDrawer />
      </div>

      {/* Zone Bottom: Time Deck */}
      <TimeDeck />
    </div>
  );
};
