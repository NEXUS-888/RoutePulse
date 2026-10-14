import React from 'react';
import { SimulationProvider, useSimulation } from './context/SimulationContext';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import { Screen1NetworkMap } from './components/screens/Screen1NetworkMap';
import { Screen2EtaBoard } from './components/screens/Screen2EtaBoard';
import { Screen3DemandAlerts } from './components/screens/Screen3DemandAlerts';
import { Screen4Recommendations } from './components/screens/Screen4Recommendations';
import { Screen5Disruptions } from './components/screens/Screen5Disruptions';
import { Screen6StudentView } from './components/screens/Screen6StudentView';
import { AlertTriangle, ArrowRight } from 'lucide-react';

const MainLayout: React.FC = () => {
  const { activeScreen, activeDisruptionAlert, setActiveScreen } = useSimulation();

  return (
    <div className="app-container">
      <Header />
      <Navigation />

      {/* Disruption Active Banner */}
      {activeDisruptionAlert && (
        <div className="disruption-banner">
          <div className="banner-left">
            <AlertTriangle size={17} style={{ color: 'var(--accent-red)' }} />
            <span>{activeDisruptionAlert}</span>
          </div>

          <button
            className="btn btn-outline"
            style={{ padding: '2px 8px', fontSize: '0.75rem', gap: 4 }}
            onClick={() => setActiveScreen('scenarios')}
          >
            <span>View Simulator & Re-opt</span>
            <ArrowRight size={13} />
          </button>
        </div>
      )}

      <main className="main-content">
        {activeScreen === 'map' && <Screen1NetworkMap />}
        {activeScreen === 'eta' && <Screen2EtaBoard />}
        {activeScreen === 'demand' && <Screen3DemandAlerts />}
        {activeScreen === 'recommendations' && <Screen4Recommendations />}
        {activeScreen === 'scenarios' && <Screen5Disruptions />}
        {activeScreen === 'student' && <Screen6StudentView />}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <SimulationProvider>
      <MainLayout />
    </SimulationProvider>
  );
};

export default App;
