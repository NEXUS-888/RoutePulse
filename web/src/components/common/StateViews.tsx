import React from 'react';
import { AlertCircle, RefreshCw, Layers, ShieldAlert, ArrowRight } from 'lucide-react';

interface SkeletonLoaderProps {
  type?: 'card' | 'table' | 'map' | 'text';
  count?: number;
  className?: string;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({ type = 'card', count = 1, className }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} className={className}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            background: 'var(--bg-surface-elevated)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
            padding: 16,
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              height: type === 'table' ? 32 : type === 'map' ? 240 : 64,
              borderRadius: 'var(--radius-xs)',
              background: 'linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-hover) 50%, var(--bg-surface) 75%)',
              backgroundSize: '200% 100%',
              animation: 'skeleton-wave 1.6s infinite ease-in-out'
            }}
          />
        </div>
      ))}
      <style>{`
        @keyframes skeleton-wave {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
};

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
  icon
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--text-secondary)'
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 'var(--radius-full)',
          background: 'var(--bg-surface-elevated)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-tertiary)',
          marginBottom: 14
        }}
      >
        {icon || <Layers size={24} />}
      </div>
      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
        {title}
      </h3>
      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', maxWidth: 380, marginBottom: actionText ? 16 : 0 }}>
        {description}
      </p>
      {actionText && onAction && (
        <button className="btn btn-primary" onClick={onAction}>
          <span>{actionText}</span>
          <ArrowRight size={14} />
        </button>
      )}
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  message: string;
  recoveryActionText?: string;
  onRecover?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Unavailable',
  message,
  recoveryActionText = 'Switch to Baseline Timetable',
  onRecover
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '36px 20px',
        textAlign: 'center',
        background: 'var(--load-coral-bg)',
        border: '1px solid var(--load-coral-border)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--text-primary)'
      }}
    >
      <ShieldAlert size={36} style={{ color: 'var(--load-coral)', marginBottom: 12 }} />
      <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--load-coral)', marginBottom: 6 }}>
        {title}
      </h3>
      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', maxWidth: 420, marginBottom: 16 }}>
        {message}
      </p>
      {onRecover && (
        <button className="btn" onClick={onRecover} style={{ background: 'var(--bg-surface)', gap: 6, fontWeight: 600 }}>
          <RefreshCw size={14} />
          <span>{recoveryActionText}</span>
        </button>
      )}
    </div>
  );
};
