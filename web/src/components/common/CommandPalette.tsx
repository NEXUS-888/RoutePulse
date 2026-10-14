import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  Map,
  Clock,
  AlertTriangle,
  Sparkles,
  Layers,
  GraduationCap,
  HelpCircle,
  Sun,
  Moon,
  Compass,
  RotateCcw,
  Play,
  Pause,
  Bus,
  MapPin,
  Flame,
  ArrowRight
} from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';
import { ROUTE_COLORS } from '../../utils/geo';
import type { ScenarioId } from '../../types';

interface PaletteItem {
  id: string;
  category: 'Screens' | 'Actions' | 'Routes' | 'Stops' | 'Vehicles' | 'Scenarios';
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: string;
  onSelect: () => void;
}

export const CommandPalette: React.FC = () => {
  const {
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    activeScreen,
    setActiveScreen,
    theme,
    toggleTheme,
    mapViewMode,
    toggleMapViewMode,
    isPlaying,
    togglePlay,
    resetToBaseline,
    startTour,
    toggleHelp,
    network,
    activeVehicles,
    triggerScenario,
    setSelectedEntity
  } = useSimulation();

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Global keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K or forward slash when not in an input
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(!isCommandPaletteOpen);
        return;
      }

      if (e.key === '/' && !isCommandPaletteOpen) {
        const activeTag = document.activeElement?.tagName.toLowerCase();
        if (activeTag !== 'input' && activeTag !== 'textarea' && activeTag !== 'select') {
          e.preventDefault();
          setIsCommandPaletteOpen(true);
          return;
        }
      }

      // Help drawer shortcut
      if (e.key === '?' && !isCommandPaletteOpen) {
        const activeTag = document.activeElement?.tagName.toLowerCase();
        if (activeTag !== 'input' && activeTag !== 'textarea') {
          e.preventDefault();
          toggleHelp();
          return;
        }
      }

      // Close on Escape
      if (e.key === 'Escape' && isCommandPaletteOpen) {
        e.preventDefault();
        setIsCommandPaletteOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen, setIsCommandPaletteOpen, toggleHelp]);

  // Focus input when opened
  useEffect(() => {
    if (isCommandPaletteOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isCommandPaletteOpen]);

  // Build items catalog
  const allItems = useMemo<PaletteItem[]>(() => {
    const items: PaletteItem[] = [
      // Screens
      {
        id: 'screen-map',
        category: 'Screens',
        title: 'Command Centre',
        subtitle: 'Full campus transit map and real-time stress radar',
        icon: <Map size={16} />,
        badge: 'Screen 1',
        onSelect: () => setActiveScreen('map')
      },
      {
        id: 'screen-eta',
        category: 'Screens',
        title: 'ETA Arrival Board',
        subtitle: 'Confidence arrival windows (p10–p90) and headway gaps',
        icon: <Clock size={16} />,
        badge: 'Screen 2',
        onSelect: () => setActiveScreen('eta')
      },
      {
        id: 'screen-demand',
        category: 'Screens',
        title: 'Demand & Bottlenecks',
        subtitle: '14-stop matrix and passenger left-behind alert deck',
        icon: <AlertTriangle size={16} />,
        badge: 'Screen 3',
        onSelect: () => setActiveScreen('demand')
      },
      {
        id: 'screen-recommendations',
        category: 'Screens',
        title: 'Recommendations & What-If',
        subtitle: 'Validated dispatch actions and simulation sandbox',
        icon: <Sparkles size={16} />,
        badge: 'Screen 4',
        onSelect: () => setActiveScreen('recommendations')
      },
      {
        id: 'screen-scenarios',
        category: 'Screens',
        title: 'Scenario Lab & Results',
        subtitle: 'Before/After slider and closed-loop disruption triggers',
        icon: <Layers size={16} />,
        badge: 'Screen 5',
        onSelect: () => setActiveScreen('scenarios')
      },
      {
        id: 'screen-student',
        category: 'Screens',
        title: 'Student Passenger View',
        subtitle: 'Mobile-first trip planner with accessible ramp filter',
        icon: <GraduationCap size={16} />,
        badge: 'Screen 6',
        onSelect: () => setActiveScreen('student')
      },

      // Actions
      {
        id: 'action-theme',
        category: 'Actions',
        title: `Switch to ${theme === 'dark' ? 'Paper Light' : 'Control Room Dark'} Theme`,
        subtitle: 'Toggle high-contrast transit visual mode',
        icon: theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />,
        badge: 'Key T',
        onSelect: () => toggleTheme()
      },
      {
        id: 'action-map-mode',
        category: 'Actions',
        title: `Switch to ${mapViewMode === 'schematic' ? 'Geographic Real-Metre' : 'Metro Schematic'} Map`,
        subtitle: 'Toggle subway-style octolinear vs true campus geometry',
        icon: <Compass size={16} />,
        badge: 'Key M',
        onSelect: () => toggleMapViewMode()
      },
      {
        id: 'action-play',
        category: 'Actions',
        title: isPlaying ? 'Pause Simulation' : 'Resume Simulation',
        subtitle: 'Control clock playback of transit movements',
        icon: isPlaying ? <Pause size={16} /> : <Play size={16} />,
        badge: 'Space',
        onSelect: () => togglePlay()
      },
      {
        id: 'action-tour',
        category: 'Actions',
        title: 'Start 90-Second Guided Tour',
        subtitle: 'Interactive spotlight walk through core features',
        icon: <Sparkles size={16} />,
        badge: 'Tour',
        onSelect: () => startTour()
      },
      {
        id: 'action-help',
        category: 'Actions',
        title: 'Open Help Centre & Operator Recipes',
        subtitle: 'Terminology glossary, FAQ, and 5-step operational guides',
        icon: <HelpCircle size={16} />,
        badge: 'Key ?',
        onSelect: () => toggleHelp()
      },
      {
        id: 'action-reset',
        category: 'Actions',
        title: 'Reset to Baseline-0',
        subtitle: 'Clear all applied recommendations and restore initial schedule',
        icon: <RotateCcw size={16} />,
        onSelect: () => resetToBaseline()
      },

      // Scenarios
      {
        id: 'scenario-s0',
        category: 'Scenarios',
        title: 'Scenario S0: Morning Peak Rush',
        subtitle: 'Baseline heavy commuter surge into campus hub',
        icon: <Flame size={16} />,
        badge: 'S0',
        onSelect: () => triggerScenario('S0')
      },
      {
        id: 'scenario-s1',
        category: 'Scenarios',
        title: 'Scenario S1: Traffic Delay (+8m Corridor)',
        subtitle: 'Congestion wavefront delay propagating across stops',
        icon: <Flame size={16} />,
        badge: 'S1',
        onSelect: () => triggerScenario('S1')
      },
      {
        id: 'scenario-s2',
        category: 'Scenarios',
        title: 'Scenario S2: Vehicle Breakdown (Bus B3)',
        subtitle: 'Mechanical failure requiring instant headway redistribution',
        icon: <Flame size={16} />,
        badge: 'S2',
        onSelect: () => triggerScenario('S2')
      },
      {
        id: 'scenario-s3',
        category: 'Scenarios',
        title: 'Scenario S3: Demand Surge (+120pax Event)',
        subtitle: 'Special campus symposium crowding Science Quad',
        icon: <Flame size={16} />,
        badge: 'S3',
        onSelect: () => triggerScenario('S3')
      }
    ];

    // Add Routes
    if (network?.routes) {
      network.routes.forEach(route => {
        const color = ROUTE_COLORS[route.route_id]?.stroke || '#64748B';
        items.push({
          id: `route-${route.route_id}`,
          category: 'Routes',
          title: `Route ${route.route_id} (${route.name})`,
          subtitle: `${route.stop_sequence.length} stops · Type: ${route.type}`,
          icon: <Bus size={16} style={{ color }} />,
          badge: route.route_id,
          badgeColor: color,
          onSelect: () => {
            setActiveScreen('map');
            if (route.stop_sequence.length > 0) {
              const stopId = route.stop_sequence[0];
              const stop = network.stops.find(s => s.stop_id === stopId);
              if (stop) {
                setSelectedEntity({ type: 'stop', id: stopId, data: stop });
              }
            }
          }
        });
      });
    }

    // Add Stops
    if (network?.stops) {
      network.stops.forEach(stop => {
        const isHub = stop.stop_id === 'S03';
        const isMetro = stop.stop_id === 'S13';
        items.push({
          id: `stop-${stop.stop_id}`,
          category: 'Stops',
          title: `${stop.stop_id}: ${stop.name}`,
          subtitle: isHub ? 'Interchange Ring Hub (4m walk transfer)' : isMetro ? 'Metro Rail Campus Gateway' : 'Bus Station',
          icon: <MapPin size={16} style={{ color: isHub ? 'var(--route-r3)' : isMetro ? 'var(--route-r1)' : 'var(--text-secondary)' }} />,
          badge: isHub ? 'HUB' : isMetro ? 'METRO' : undefined,
          onSelect: () => {
            setActiveScreen('map');
            setSelectedEntity({ type: 'stop', id: stop.stop_id, data: stop });
          }
        });
      });
    }

    // Add Active Vehicles
    activeVehicles.forEach(veh => {
      items.push({
        id: `vehicle-${veh.vehicle_id}`,
        category: 'Vehicles',
        title: `Vehicle ${veh.vehicle_id} (${veh.type.toUpperCase()})`,
        subtitle: `Route ${veh.route_id} · Next: ${veh.nextStop} · Load: ${Math.round(veh.loadPct)}%`,
        icon: <Bus size={16} />,
        badge: `${Math.round(veh.loadPct)}%`,
        badgeColor: veh.loadPct > 100 ? 'var(--load-coral)' : veh.loadPct >= 85 ? 'var(--load-amber)' : 'var(--load-teal)',
        onSelect: () => {
          setActiveScreen('map');
          setSelectedEntity({ type: 'vehicle', id: veh.vehicle_id, data: veh });
        }
      });
    });

    return items;
  }, [network, activeVehicles, theme, mapViewMode, isPlaying, setActiveScreen, toggleTheme, toggleMapViewMode, togglePlay, startTour, toggleHelp, resetToBaseline, triggerScenario, setSelectedEntity]);

  // Filter items by query
  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems.slice(0, 15);
    const q = query.toLowerCase();
    return allItems.filter(
      item =>
        item.title.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q)) ||
        item.category.toLowerCase().includes(q)
    );
  }, [allItems, query]);

  // Handle keyboard list navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < filteredItems.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : filteredItems.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = filteredItems[selectedIndex];
      if (selected) {
        selected.onSelect();
        setIsCommandPaletteOpen(false);
      }
    }
  };

  if (!isCommandPaletteOpen) return null;

  return (
    <div
      className="palette-backdrop"
      onClick={() => setIsCommandPaletteOpen(false)}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '10vh',
        animation: 'fadeIn 0.15s ease-out'
      }}
    >
      <div
        className="palette-card"
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 620,
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elevation-3)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Search Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '14px 18px',
            borderBottom: '1px solid var(--border-color)',
            gap: 12
          }}
        >
          <Search size={18} style={{ color: 'var(--text-tertiary)' }} />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search screens, routes, stops, vehicles, or actions..."
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: '0.95rem',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-body)'
            }}
          />
          <kbd
            style={{
              padding: '2px 6px',
              fontSize: '0.68rem',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-tertiary)',
              fontFamily: 'var(--font-mono)'
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          style={{
            maxHeight: 380,
            overflowY: 'auto',
            padding: '8px'
          }}
        >
          {filteredItems.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
              No matches found for "{query}".
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.onSelect();
                    setIsCommandPaletteOpen(false);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: isSelected ? 'var(--bg-surface)' : 'transparent',
                    border: isSelected ? '1px solid var(--border-color)' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'background-color 0.1s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div
                      style={{
                        color: isSelected ? 'var(--route-r1)' : 'var(--text-secondary)',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      {item.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {item.title}
                      </div>
                      {item.subtitle && (
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-tertiary)', marginTop: 2 }}>
                          {item.subtitle}
                        </div>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {item.badge && (
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                          padding: '2px 6px',
                          borderRadius: 'var(--radius-xs)',
                          backgroundColor: item.badgeColor ? `${item.badgeColor}22` : 'var(--bg-canvas)',
                          color: item.badgeColor || 'var(--text-secondary)',
                          border: `1px solid ${item.badgeColor ? `${item.badgeColor}44` : 'var(--border-color)'}`
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                    {isSelected && <ArrowRight size={14} style={{ color: 'var(--route-r1)' }} />}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer Navigation Hints */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-surface)',
            fontSize: '0.72rem',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          <div style={{ display: 'flex', gap: 12 }}>
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>esc Close</span>
          </div>
          <div>
            <span>Press ? for Help</span>
          </div>
        </div>
      </div>
    </div>
  );
};
