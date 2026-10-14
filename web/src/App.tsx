import React from 'react';
import { SimulationProvider, useSimulation } from './context/SimulationContext';
import { AppShell } from './components/shell/AppShell';
import { Screen1NetworkMap } from './components/screens/Screen1NetworkMap';
import { Screen2EtaBoard } from './components/screens/Screen2EtaBoard';
import { Screen3DemandAlerts } from './components/screens/Screen3DemandAlerts';
import { Screen4Recommendations } from './components/screens/Screen4Recommendations';
import { Screen5Disruptions } from './components/screens/Screen5Disruptions';
import { Screen6StudentView } from './components/screens/Screen6StudentView';
import { WelcomeModal } from './components/onboarding/WelcomeModal';
import { SpotlightTour } from './components/onboarding/SpotlightTour';
import { ShowcaseDemo } from './components/onboarding/ShowcaseDemo';
import { HelpDrawer } from './components/help/HelpDrawer';
import { CommandPalette } from './components/common/CommandPalette';

const MainLayout: React.FC = () => {
  const {
    activeScreen,
    setActiveScreen,
    toggleTheme,
    toggleMapViewMode,
    togglePlay,
    isCommandPaletteOpen,
    isHelpOpen
  } = useSimulation();

  // Screen shortcuts (1-6) and quick toggles when no modals or inputs are focused
  React.useEffect(() => {
    const handleGlobalShortcuts = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') {
        return;
      }
      if (isCommandPaletteOpen || isHelpOpen) return;

      if (e.key === '1') setActiveScreen('map');
      else if (e.key === '2') setActiveScreen('eta');
      else if (e.key === '3') setActiveScreen('demand');
      else if (e.key === '4') setActiveScreen('recommendations');
      else if (e.key === '5') setActiveScreen('scenarios');
      else if (e.key === '6') setActiveScreen('student');
      else if (e.key.toLowerCase() === 't') toggleTheme();
      else if (e.key.toLowerCase() === 'm') toggleMapViewMode();
      else if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
      }
    };

    window.addEventListener('keydown', handleGlobalShortcuts);
    return () => window.removeEventListener('keydown', handleGlobalShortcuts);
  }, [setActiveScreen, toggleTheme, toggleMapViewMode, togglePlay, isCommandPaletteOpen, isHelpOpen]);

  return (
    <AppShell>
      {/* Active Stage Screen */}
      {activeScreen === 'map' && <Screen1NetworkMap />}
      {activeScreen === 'eta' && <Screen2EtaBoard />}
      {activeScreen === 'demand' && <Screen3DemandAlerts />}
      {activeScreen === 'recommendations' && <Screen4Recommendations />}
      {activeScreen === 'scenarios' && <Screen5Disruptions />}
      {activeScreen === 'student' && <Screen6StudentView />}

      {/* Onboarding Modals, Tour & Help Drawer Overlays */}
      <WelcomeModal />
      <SpotlightTour />
      <ShowcaseDemo />
      <HelpDrawer />
      <CommandPalette />
    </AppShell>
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
