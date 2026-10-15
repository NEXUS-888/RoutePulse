import React, { useState, useMemo } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { GLOSSARY } from '../../content/glossary';
import {
  X,
  Search,
  BookOpen,
  Sparkles,
  RotateCcw,
  Command,
  HelpCircle,
  FileText,
  User,
  GraduationCap,
  ShieldCheck,
  Zap
} from 'lucide-react';

export const HelpDrawer: React.FC = () => {
  const {
    isHelpOpen,
    setIsHelpOpen,
    startTour,
    resetToBaseline,
    setIsWelcomeOpen
  } = useSimulation();

  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'glossary' | 'recipes' | 'roles' | 'shortcuts'>('glossary');

  // Filter glossary entries by search query
  const filteredGlossary = useMemo(() => {
    const list = Object.values(GLOSSARY);
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      item =>
        item.term.toLowerCase().includes(q) ||
        item.shortDefinition.toLowerCase().includes(q) ||
        item.detailedExplanation.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  if (!isHelpOpen) return null;

  const recipes = [
    {
      title: 'Why is a bus late?',
      steps: [
        'Open the Live Map and click the delayed vehicle or destination stop.',
        'View the horizontal ETA capsule to observe the p10–p90 arrival window.',
        'Hover over the capsule to read the plain-language diagnostic explanation (e.g. corridor congestion or dwell variance).'
      ]
    },
    {
      title: 'Fix an overcrowded route (R3 peak)',
      steps: [
        'Navigate to Recommendations in the navigation rail.',
        'Locate the high-impact card (e.g. Rec-0007: Add trip on R3 using idle reserve bus B5).',
        'Review the Gain vs Cost trade-off and verified H1–H12 constraint checklist.',
        'Click "Accept Recommendation" to update the live schedule with 0 violations.'
      ]
    },
    {
      title: 'Test vehicle breakdown & recovery (S2)',
      steps: [
        'Navigate to Scenario Lab and select scenario S2 (Vehicle Breakdown).',
        'At 08:05, observe Bus B3 turn into a dashed ghost marker on Route R3.',
        'Observe alerts trigger and the rolling optimizer propose a short-turn or vehicle reallocation.',
        'Apply the recommendation to restore network health back to Teal.'
      ]
    },
    {
      title: 'Compare with the Baseline plan',
      steps: [
        'Go to Scenario Lab or Results comparison screen.',
        'Use the interactive Before/After reveal slider to visually inspect Baseline-0 (coral queues) vs RoutePulse (balanced).',
        'Inspect the KPI table displaying mean wait, left-behind, and missed connections with 95% confidence intervals.'
      ]
    }
  ];

  const shortcuts = [
    { key: '?', desc: 'Open / Close Help Centre & Glossary' },
    { key: 'Esc', desc: 'Close any active drawer, modal, or tour step' },
    { key: 'Space', desc: 'Toggle replay simulation Play / Pause' },
    { key: '1 / 2 / 3', desc: 'Switch replay speed: 1x, 10x, 30x' },
    { key: 'Ctrl + K', desc: 'Open Command Palette' }
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(8, 7, 6, 0.5)',
        zIndex: 250,
        display: 'flex',
        justifyContent: 'flex-end'
      }}
      onClick={() => setIsHelpOpen(false)}
    >
      <aside
        style={{
          width: '100%',
          maxWidth: '480px',
          height: '100%',
          background: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border-color)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 260
        }}
        onClick={e => e.stopPropagation()}
        aria-label="Help Centre Drawer"
      >
        {/* Drawer Header */}
        <div className="drawer-header" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <HelpCircle size={18} style={{ color: 'var(--accent)' }} />
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>RoutePulse Help Centre</h2>
          </div>
          <button
            className="btn-icon"
            onClick={() => setIsHelpOpen(false)}
            title="Close Help (Esc)"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Search Bar */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px'
            }}
          >
            <Search size={15} style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              placeholder="Search concepts, recipes, terms..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                width: '100%',
                fontSize: '0.82rem',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-body)'
              }}
            />
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--bg-surface-elevated)',
            padding: '0 12px'
          }}
        >
          {(
            [
              ['glossary', 'Glossary'],
              ['recipes', 'How-To Recipes'],
              ['roles', 'User Paths'],
              ['shortcuts', 'Shortcuts']
            ] as const
          ).map(([tabKey, tabLabel]) => (
            <button
              key={tabKey}
              onClick={() => setActiveTab(tabKey)}
              style={{
                flex: 1,
                padding: '10px 4px',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === tabKey ? '2px solid var(--accent)' : '2px solid transparent',
                color: activeTab === tabKey ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === tabKey ? 700 : 500,
                fontSize: '0.78rem',
                cursor: 'pointer'
              }}
            >
              {tabLabel}
            </button>
          ))}
        </div>

        {/* Drawer Scrollable Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Tab 1: Glossary */}
          {activeTab === 'glossary' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)' }}>
                Official transit terms defined in plain language.
              </p>
              {filteredGlossary.map(item => (
                <div
                  key={item.id}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 12px'
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--text-primary)', marginBottom: 3 }}>
                    {item.term}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                    {item.shortDefinition}
                  </div>
                  {item.detailedExplanation && (
                    <div style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--text-tertiary)', borderTop: '1px solid var(--border-subtle)', paddingTop: 4 }}>
                      {item.detailedExplanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Tab 2: How-To Recipes */}
          {activeTab === 'recipes' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {recipes.map((recipe, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px 14px'
                  }}
                >
                  <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--accent)', marginBottom: 8 }}>
                    {recipe.title}
                  </h4>
                  <ol style={{ paddingLeft: 18, fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6, lineHeight: 1.4 }}>
                    {recipe.steps.map((st, i) => (
                      <li key={i}>{st}</li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          )}

          {/* Tab 3: Roles Paths */}
          {activeTab === 'roles' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ background: 'var(--bg-surface-elevated)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, marginBottom: 4 }}>
                  <User size={15} style={{ color: 'var(--accent)' }} />
                  <span>Operator: Your First 3 Minutes</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  Start on the Command Centre map at 08:00 morning peak. Notice Route R3 turning coral under heavy passenger load. Check Demand & Alerts to view the 62 left-behind riders. Open Recommendations, review Rec-0007, and click Accept to dispatch idle reserve bus B5. Watch Network Health climb back to 90+.
                </p>
              </div>

              <div style={{ background: 'var(--bg-surface-elevated)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, marginBottom: 4 }}>
                  <GraduationCap size={15} style={{ color: 'var(--load-teal)' }} />
                  <span>Student: Your First 3 Minutes</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  Open Student View on mobile (390×844). Choose your origin (e.g. Metro Gateway S13) and destination (Engineering S05). Notice the large arrival window capsule. If the immediate departure is crowded, RoutePulse highlights a later alternative 8 minutes later with 60% capacity. Toggle step-free wheelchair access for ramp-equipped shuttles.
                </p>
              </div>

              <div style={{ background: 'var(--bg-surface-elevated)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, marginBottom: 4 }}>
                  <ShieldCheck size={15} style={{ color: 'var(--load-amber)' }} />
                  <span>Judge / Reviewer: Your First 3 Minutes</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  Go to Scenario Lab. Compare Baseline-0 vs RoutePulse side-by-side. Drag the Before/After reveal slider across the schematic map. Confirm 0 hard-constraint violations across all evaluated runs. Inject a breakdown in S2 to test automated recovery and view paired confidence intervals.
                </p>
              </div>
            </div>
          )}

          {/* Tab 4: Shortcuts */}
          {activeTab === 'shortcuts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {shortcuts.map((sc, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--bg-surface-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.8rem'
                  }}
                >
                  <span style={{ color: 'var(--text-secondary)' }}>{sc.desc}</span>
                  <kbd
                    style={{
                      padding: '3px 7px',
                      borderRadius: 4,
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-strong)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'var(--text-primary)'
                    }}
                  >
                    {sc.key}
                  </kbd>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Drawer Footer Actions */}
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid var(--border-color)',
            background: 'var(--bg-surface-elevated)',
            display: 'flex',
            gap: 10
          }}
        >
          <button
            className="btn btn-primary"
            onClick={() => {
              setIsHelpOpen(false);
              startTour();
            }}
            style={{ flex: 1, gap: 6 }}
          >
            <Sparkles size={14} style={{ color: 'var(--load-amber)' }} />
            <span>Replay 90s Tour</span>
          </button>

          <button
            className="btn btn-outline"
            onClick={() => {
              setIsHelpOpen(false);
              resetToBaseline();
              setIsWelcomeOpen(true);
            }}
            title="Reset onboarding and restore defaults"
            style={{ gap: 5 }}
          >
            <RotateCcw size={13} />
            <span>Reset All</span>
          </button>
        </div>
      </aside>
    </div>
  );
};
