import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { PulseLine } from '../shell/PulseLine';
import {
  Sparkles,
  Play,
  Compass,
  User,
  GraduationCap,
  ShieldCheck,
  Check
} from 'lucide-react';
import type { UserRole } from '../../types';

export const WelcomeModal: React.FC = () => {
  const {
    isWelcomeOpen,
    setIsWelcomeOpen,
    startTour,
    startAutoDemo,
    userRole,
    setUserRole,
    setActiveScreen
  } = useSimulation();

  if (!isWelcomeOpen) return null;

  const handleExploreOnMyOwn = () => {
    setIsWelcomeOpen(false);
    localStorage.setItem('rp_onboarded_v1', 'true');
  };

  const handleRoleSelect = (role: UserRole) => {
    setUserRole(role);
    if (role === 'student') {
      setActiveScreen('student');
    } else if (role === 'operator') {
      setActiveScreen('map');
    } else {
      setActiveScreen('scenarios');
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(8, 7, 6, 0.88)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          padding: '32px 36px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          position: 'relative'
        }}
      >
        {/* Animated Signature Pulse Line */}
        <div style={{ marginBottom: 12 }}>
          <PulseLine width={160} height={36} />
        </div>

        {/* Logo Lockup */}
        <h1
          className="font-display"
          style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: 4 }}
        >
          RoutePulse
        </h1>
        <p
          style={{
            fontSize: '0.92rem',
            color: 'var(--text-secondary)',
            fontWeight: 500,
            marginBottom: 20
          }}
        >
          Plan the campus. Don't just watch it.
        </p>

        {/* Role Selector Tabs */}
        <div style={{ width: '100%', marginBottom: 24 }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
            Select Your Role
          </span>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              background: 'var(--bg-surface-elevated)',
              padding: 4,
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)'
            }}
          >
            {[
              { id: 'operator' as UserRole, label: 'Operator', icon: <User size={14} /> },
              { id: 'student' as UserRole, label: 'Student', icon: <GraduationCap size={14} /> },
              { id: 'reviewer' as UserRole, label: 'Judge / Reviewer', icon: <ShieldCheck size={14} /> }
            ].map(r => (
              <button
                key={r.id}
                onClick={() => handleRoleSelect(r.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '7px 8px',
                  borderRadius: 'var(--radius-xs)',
                  border: 'none',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: userRole === r.id ? 'var(--accent)' : 'transparent',
                  color: userRole === r.id ? 'var(--accent-contrast)' : 'var(--text-secondary)',
                  transition: 'var(--transition-fast)'
                }}
              >
                {r.icon}
                <span>{r.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Three Big Choices (No long text) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
          {/* Choice 1: 90s Guided Tour */}
          <button
            className="btn btn-primary"
            onClick={startTour}
            style={{
              padding: '12px 18px',
              fontSize: '0.92rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <Sparkles size={18} style={{ color: 'var(--load-amber)' }} />
            <span>Take the 90-second tour</span>
          </button>

          {/* Choice 2: Watch Auto-Demo */}
          <button
            className="btn"
            onClick={startAutoDemo}
            style={{
              padding: '11px 18px',
              fontSize: '0.88rem',
              fontWeight: 600,
              background: 'var(--bg-surface-elevated)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <Play size={16} />
            <span>Watch the hands-free auto-demo</span>
          </button>

          {/* Choice 3: Explore on my own */}
          <button
            className="btn btn-outline"
            onClick={handleExploreOnMyOwn}
            style={{
              padding: '9px 18px',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              border: '1px solid transparent'
            }}
          >
            <span>Explore on my own</span>
          </button>
        </div>

        <div style={{ marginTop: 18, fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
          Tip: Press <kbd style={{ padding: '2px 5px', borderRadius: 3, background: 'var(--bg-hover)', border: '1px solid var(--border-color)', fontFamily: 'var(--font-mono)' }}>?</kbd> anytime to open the Help Centre & Glossary.
        </div>
      </div>
    </div>
  );
};
