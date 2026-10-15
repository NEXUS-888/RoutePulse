import React, { useState } from 'react';
import { GLOSSARY, GlossaryEntry } from '../../content/glossary';
import { HelpCircle } from 'lucide-react';

interface GlossaryPopoverProps {
  termId: keyof typeof GLOSSARY | string;
  children?: React.ReactNode;
}

export const GlossaryPopover: React.FC<GlossaryPopoverProps> = ({ termId, children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const entry = GLOSSARY[termId];

  if (!entry) {
    return <>{children}</>;
  }

  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 3 }}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      {children ? (
        <span style={{ borderBottom: '1px dotted var(--text-tertiary)', cursor: 'help' }}>
          {children}
        </span>
      ) : (
        <span style={{ borderBottom: '1px dotted var(--text-tertiary)', cursor: 'help' }}>
          {entry.term}
        </span>
      )}

      <button
        type="button"
        onClick={e => {
          e.stopPropagation();
          setIsOpen(prev => !prev);
        }}
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          color: 'var(--text-tertiary)',
          display: 'inline-flex',
          alignItems: 'center'
        }}
        title={`Learn what "${entry.term}" means`}
      >
        <HelpCircle size={12} />
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '260px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 120,
            fontSize: '0.75rem',
            color: 'var(--text-primary)',
            lineHeight: 1.4,
            textAlign: 'left'
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--accent)', marginBottom: 3 }}>
            {entry.term}
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            {entry.shortDefinition}
          </div>
        </div>
      )}
    </span>
  );
};
