import { useState, useEffect } from 'react';

interface AiFlashScreenProps {
  onEnter: () => void;
  autoDismissSeconds?: number;
}

const ROLE_EXPLANATIONS = [
  {
    role: 'Executive & DG',
    icon: '👔',
    badge: 'Strategic & Board Governance',
    accent: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    border: 'rgba(239, 68, 68, 0.35)',
    engineered: 'Displays static risk charts, 69 finding counts & raw breach percentages.',
    ai: 'Translates technical chaos into board-ready ministerial briefs, service delivery impact (e.g. Smart ID uptime), and budget risk trade-offs.',
  },
  {
    role: 'SOC Analyst',
    icon: '🛡️',
    badge: 'Triage & Threat Defense',
    accent: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.12)',
    border: 'rgba(59, 130, 246, 0.35)',
    engineered: 'Dumps thousands of raw WAF blocks and firewall packet logs into tabular grids.',
    ai: 'Correlates fragmented alerts into attacker narratives, prioritizes urgent alerts, and auto-generates Sigma and WAF defensive detection rules.',
  },
  {
    role: 'AppSec Engineer',
    icon: '⚙️',
    badge: 'Secure Code & Architecture',
    accent: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.12)',
    border: 'rgba(245, 158, 11, 0.35)',
    engineered: 'Outputs generic CWE-20/CWE-16 identifiers and static source code line numbers.',
    ai: 'Explains vulnerable code paths in government application contexts and generates drop-in patches that prevent legacy system breakage.',
  },
  {
    role: 'Compliance Officer',
    icon: '⚖️',
    badge: 'Regulatory & Audit Readiness',
    accent: '#8b5cf6',
    bg: 'rgba(139, 92, 246, 0.12)',
    border: 'rgba(139, 92, 246, 0.35)',
    engineered: 'Verifies boolean configuration flags (e.g. "TLS Enabled: True").',
    ai: 'Synthesizes formal POPIA Section 22 breach notification dossiers for the Information Regulator and compiles Auditor-General defense briefs.',
  },
  {
    role: 'DBSec & SRE Teams',
    icon: '🗄️',
    badge: 'Infrastructure & Data Perimeter',
    accent: '#10b981',
    bg: 'rgba(16, 185, 129, 0.12)',
    border: 'rgba(16, 185, 129, 0.35)',
    engineered: 'Plots server CPU spikes, memory utilization, and raw database error logs.',
    ai: 'Analyzes user behavioral sequences to differentiate benign provincial batch jobs from malicious exfiltration of citizen identity data.',
  },
  {
    role: 'Universal Copilot',
    icon: '🧠',
    badge: 'Two-Gate Verified Grounding',
    accent: '#06b6d4',
    bg: 'rgba(6, 182, 212, 0.12)',
    border: 'rgba(6, 182, 212, 0.35)',
    engineered: 'Requires manual SQL querying and custom code updates for every new question.',
    ai: 'Enables conversational Q&A across the entire security posture with a mathematical guarantee of 0% hallucinations.',
  },
];

export default function AiFlashScreen({ onEnter, autoDismissSeconds = 8 }: AiFlashScreenProps) {
  const [countdown, setCountdown] = useState<number>(autoDismissSeconds);
  const [paused, setPaused] = useState<boolean>(false);
  const [selectedRoleIndex, setSelectedRoleIndex] = useState<number>(0);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onEnter();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [paused, onEnter]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'radial-gradient(ellipse at 50% 20%, #151a30 0%, #080c14 70%, #030508 100%)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        color: '#f8fafc',
        fontFamily: "'Inter', system-ui, sans-serif",
        overflowY: 'auto',
        animation: 'aiFlashFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* Background cyber grid & animated glow */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(rgba(99, 102, 241, 0.15) 1px, transparent 1px), radial-gradient(rgba(139, 92, 246, 0.1) 1px, transparent 1px)',
          backgroundSize: '40px 40px, 20px 20px',
          backgroundPosition: '0 0, 20px 20px',
          opacity: 0.4,
          pointerEvents: 'none',
        }}
      />

      {/* Main Flash Screen Card */}
      <div
        style={{
          position: 'relative',
          maxWidth: '1060px',
          width: '100%',
          background: 'rgba(15, 23, 42, 0.82)',
          border: '1px solid rgba(99, 102, 241, 0.35)',
          borderRadius: '24px',
          padding: '36px 40px',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 50px rgba(99, 102, 241, 0.2)',
          backdropFilter: 'blur(16px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        {/* Header Section */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '16px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                background: 'linear-gradient(135deg, #4338ca, #6366f1, #8b5cf6)',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '28px',
                boxShadow: '0 0 25px rgba(99, 102, 241, 0.6)',
              }}
            >
              🧠
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                <span
                  style={{
                    background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: 800,
                    padding: '3px 10px',
                    borderRadius: '20px',
                    letterSpacing: '0.08em',
                  }}
                >
                  SITA CYBER AI INTELLIGENCE &amp; ALERTS
                </span>
                <span
                  style={{
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '6px',
                  }}
                >
                  ZERO-HALLUCINATION VERIFIED
                </span>
              </div>
              <h1
                style={{
                  fontSize: '24px',
                  fontWeight: 800,
                  color: '#f8fafc',
                  margin: 0,
                  letterSpacing: '-0.02em',
                }}
              >
                Autonomous Telemetry Reasoning Across All Government Roles
              </h1>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                Engineered code counts facts and raw logs. The AI layer connects them into human meaning,
                actionable directives, and legal accountability.
              </p>
            </div>
          </div>

          {/* Enter Action with Countdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                {paused ? 'Timer paused (hovering)' : `Auto-launching in ${countdown}s`}
              </div>
              <div
                style={{
                  width: '120px',
                  height: '4px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '2px',
                  overflow: 'hidden',
                  marginTop: '4px',
                }}
              >
                <div
                  style={{
                    width: `${((autoDismissSeconds - countdown) / autoDismissSeconds) * 100}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #6366f1, #10b981)',
                    transition: 'width 1s linear',
                  }}
                />
              </div>
            </div>

            <button
              id="ai-enter-workspace-btn"
              onClick={onEnter}
              style={{
                padding: '12px 24px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                border: 'none',
                color: '#fff',
                fontSize: '14px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 18px rgba(99, 102, 241, 0.4)',
                transition: 'all 0.2s ease',
              }}
            >
              Enter AI Workspace ➔
            </button>
          </div>
        </div>

        {/* Interactive Role Cards Grid */}
        <div>
          <div
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: '#818cf8',
              letterSpacing: '0.08em',
              marginBottom: '12px',
              textTransform: 'uppercase',
            }}
          >
            Select a Role to Preview AI Capabilities:
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '10px',
              marginBottom: '16px',
            }}
          >
            {ROLE_EXPLANATIONS.map((r, idx) => (
              <button
                key={r.role}
                onClick={() => setSelectedRoleIndex(idx)}
                style={{
                  background: selectedRoleIndex === idx ? r.bg : 'rgba(30, 41, 59, 0.5)',
                  border: `1px solid ${selectedRoleIndex === idx ? r.accent : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '12px',
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                  boxShadow: selectedRoleIndex === idx ? `0 4px 14px ${r.accent}33` : 'none',
                }}
              >
                <span style={{ fontSize: '20px' }}>{r.icon}</span>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc' }}>{r.role}</div>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>{r.badge.split('&')[0]}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Selected Role Focus Comparison Banner */}
        {(() => {
          const active = ROLE_EXPLANATIONS[selectedRoleIndex];
          return (
            <div
              style={{
                background: active.bg,
                border: `1px solid ${active.border}`,
                borderRadius: '16px',
                padding: '22px 26px',
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '24px',
                position: 'relative',
              }}
            >
              {/* Engineered Code Column */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12px',
                    fontWeight: 700,
                    color: '#94a3b8',
                    marginBottom: '8px',
                    letterSpacing: '0.04em',
                  }}
                >
                  <span style={{ color: '#ef4444', fontSize: '14px' }}>⚙️</span>
                  WHAT THE ENGINEERED CODE DOES (RAW FACTS)
                </div>
                <div
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    borderRadius: '10px',
                    padding: '14px 16px',
                    fontSize: '13px',
                    lineHeight: '1.6',
                    color: '#cbd5e1',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  {active.engineered}
                </div>
              </div>

              {/* AI Layer Column */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12px',
                    fontWeight: 700,
                    color: active.accent,
                    marginBottom: '8px',
                    letterSpacing: '0.04em',
                  }}
                >
                  <span style={{ fontSize: '16px' }}>✨</span>
                  WHAT THE AI DOES THAT CODE CANNOT (REASONING &amp; NARRATIVE)
                </div>
                <div
                  style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    borderRadius: '10px',
                    padding: '14px 16px',
                    fontSize: '13px',
                    lineHeight: '1.6',
                    color: '#f8fafc',
                    border: `1px solid ${active.accent}55`,
                    boxShadow: `0 4px 16px ${active.accent}22`,
                  }}
                >
                  {active.ai}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Footer Note */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px',
            color: '#64748b',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            paddingTop: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🔒 Strict Tenancy Enforced: All AI outputs are bounded by caller government department scope.</span>
          </div>
          <div>
            <button
              onClick={onEnter}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#818cf8',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Skip intro &amp; go directly to AI Suite
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
