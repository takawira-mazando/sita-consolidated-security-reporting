import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import type { TenancyTier } from '../../types';

interface DemoAct {
  actNumber: number;
  title: string;
  subtitle: string;
  tier?: TenancyTier;
  targetRole?: string;
  targetPath?: string;
  talkingPoints: string[];
  suggestedAction?: {
    label: string;
    action: () => void;
  };
  secondaryActions?: {
    label: string;
    action: () => void;
  }[];
}

export default function DemoTourGuide() {
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    const saved = localStorage.getItem('sita_demo_guide_open');
    return saved !== null ? saved === 'true' : true;
  });
  const [currentActIndex, setCurrentActIndex] = useState<number>(() => {
    const saved = localStorage.getItem('sita_demo_guide_act');
    return saved !== null ? parseInt(saved, 10) : 0;
  });

  const { user, loginDemo, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem('sita_demo_guide_open', String(isOpen));
  }, [isOpen]);

  useEffect(() => {
    localStorage.setItem('sita_demo_guide_act', String(currentActIndex));
  }, [currentActIndex]);

  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    window.addEventListener('sita_open_demo_guide', handleOpen);
    return () => window.removeEventListener('sita_open_demo_guide', handleOpen);
  }, []);

  const acts: DemoAct[] = [
    {
      actNumber: 1,
      title: 'Act 1: Landing & Public Summary',
      subtitle: 'Zero-Trust Public Portal & Granular RBAC Matrix',
      talkingPoints: [
        'Unauthenticated landing page designed for republic-wide transparency without exposing sensitive telemetry.',
        '14 Roles × 5 Capabilities Matrix visually proves strict boundary segregation (Alerts, Vulns, Access Logs, Compliance, Infra).',
        'Demonstrates OWASP API Security compliance with cryptographically signed headers (CSP, HSTS, X-Frame-Options, COEP/COOP).',
        'Live Public Summary endpoint provides high-level health indices with zero authentication risk.',
      ],
      suggestedAction: {
        label: '🏠 View Public Landing Page',
        action: () => {
          if (user) logout();
          navigate('/');
        },
      },
      secondaryActions: [
        {
          label: '⚡ Open Standalone Showcase',
          action: () => window.open('/standalone_demo.html', '_blank'),
        },
        {
          label: '📑 Open Executive Pitch Deck',
          action: () => window.open('/presentation.html', '_blank'),
        },
        {
          label: '🏛️ Open Architecture Diagram',
          action: () => window.open('/architecture.html', '_blank'),
        },
      ],
    },
    {
      actNumber: 2,
      title: 'Act 2: Multi-Tier Authentication & Tenancy',
      subtitle: '4-Tier Government Hierarchy · 2 Transversal Superadmins · Branch Scoping',
      talkingPoints: [
        'Two Transversal Superadmins govern the Control Plane cascade: SITA Superadmin #1 (admin@, Tier 4) is created by our Developers — the single SITA client contact. National Gov Transversal Superadmin #2 (transversal@, Tier 3) is created by SITA Superadmin #1.',
        'Strict 4-tier delegation: Tier 4 (SITA Command Center) → Tier 3 (National Security Estate) → Tier 2 (Department of Home Affairs) → Tier 1 (DDG Operational Branches).',
        'Admin roles are pure Control Plane — they provision downstream access but hold zero telemetry dashboards. Security cockpits are a separate Data Plane.',
        'National Gov Transversal Superadmin #2 delegates Department Superadmins across all organs of state. Dept Superadmin provisions Branch Admins. Branch Admin provisions operational specialists.',
        'Branch-level scoping: 8 DHA DDG units — Civic Services, Digital, Immigration, Operations, HRMD, CCSS, Finance, Planning. Department roles are cryptographically jailed to their tenancy.',
      ],
      suggestedAction: {
        label: '👑 Login as SITA Superadmin #1 (admin@)',
        action: async () => {
          await loginDemo('admin');
          navigate('/sita/admin');
        },
      },
      secondaryActions: [
        {
          label: '🏛 Login as National Gov Transversal Superadmin #2 (transversal@)',
          action: async () => {
            await loginDemo('transversal-admin');
            navigate('/national/admin');
          },
        },
        {
          label: '📊 Login as National Executive (exec@)',
          action: async () => {
            await loginDemo('exec');
            navigate('/national/exec');
          },
        },
        {
          label: '🏢 Login as DHA SOC Analyst (soc-ha@)',
          action: async () => {
            await loginDemo('soc-ha', { department_id: 'home-affairs-digital', branch_id: null, province_id: null });
            navigate('/dept/soc');
          },
        },
        {
          label: '📍 Scope to DHA Immigration Branch',
          action: async () => {
            await loginDemo('soc-ha', { department_id: 'home-affairs-digital', branch_id: 'dha-immigration', province_id: null });
            navigate('/branch/soc');
          },
        },
      ],
    },
    {
      actNumber: 3,
      title: 'Act 3: Role-Based Security Dashboards',
      subtitle: '6 Purpose-Built Cockpits with Live Telemetry',
      talkingPoints: [
        'Executive Dashboard: Multi-source Fused Risk Score (CVSS × exposure × blast radius) with interactive "Explain This" AI narrative.',
        'SOC Analyst Dashboard: Real-time telemetry feed from AppScan, Imperva WAF, and Thales DAM.',
        'AppSec Dashboard: Vulnerability trends mapped directly to OWASP Top 10 2021/2023 with remediation velocity tracking.',
        'DbSec Dashboard: Database activity monitoring (DAM), Cassandra/PostgreSQL clusters, and sensitive PII inventory.',
        'Compliance & SRE: POPIA, ISO 27001, and Auditor-General audit readiness gauges alongside microservice SLO health.',
      ],
      suggestedAction: {
        label: '📊 Open Executive Dashboard',
        action: async () => {
          if (!user || !user.roles.includes('exec')) {
            await loginDemo('exec');
          }
          navigate('/national/exec');
        },
      },
      secondaryActions: [
        {
          label: '🛡️ SOC Telemetry Dashboard',
          action: () => navigate('/dept/soc'),
        },
        {
          label: '🔍 AppSec OWASP Dashboard',
          action: () => navigate('/dept/appsec'),
        },
        {
          label: '🗄️ DbSec DAM Dashboard',
          action: () => navigate('/dept/dbsec'),
        },
        {
          label: '📜 Compliance & AG Readiness',
          action: () => navigate('/national/compliance'),
        },
      ],
    },
    {
      actNumber: 4,
      title: 'Act 4: AI Intelligence Engine',
      subtitle: 'Deterministic Core & 8 Analytical Capabilities',
      talkingPoints: [
        'Deterministic Baseline: Every analytical route runs joins/aggregates with zero third-party AI exposure by default.',
        '8 Analytical Capabilities: Author Attribution, Campaign Attribution, POPIA Dossier, Risk Causal Attribution, Behaviour Sequences, VAPT Log Interpretation, Capability Manifest, and AI Report Studio.',
        'POPIA Zero-Log Guarantee: No personal identity data or raw database payloads are ever transmitted outbound.',
        'Two-Gate Verification: AI reports undergo automated fact-checking against warehouse telemetry before executive release.',
      ],
      suggestedAction: {
        label: '🧠 Open AI Intel & Alerts Studio',
        action: async () => {
          if (!user) {
            await loginDemo('exec');
          }
          navigate('/national/ai');
        },
      },
      secondaryActions: [
        {
          label: '📑 POPIA Impact Assessment',
          action: () => navigate('/national/ai?tab=popia'),
        },
        {
          label: '🕵️ Threat Campaign Attribution',
          action: () => navigate('/national/ai?tab=campaign'),
        },
        {
          label: '🛡️ VAPT Log Interpretation',
          action: () => navigate('/national/ai?tab=vapt'),
        },
      ],
    },
    {
      actNumber: 5,
      title: 'Act 5: Delegated Admin Cascade — 2 Transversal Superadmins',
      subtitle: 'Control Plane · 4-Tier Provisioning & Authoritative HR Verification',
      talkingPoints: [
        'Two Transversal Superadmins govern the Control Plane: SITA Superadmin #1 (admin@, Tier 4) is created by the Developers — our single SITA client contact. National Gov Transversal Superadmin #2 (transversal@, Tier 3) is created exclusively by SITA Superadmin #1.',
        'SITA Superadmin #1 provisions National Gov Transversal Superadmin #2 and grants national-tier security cockpit roles (Executive, Compliance, SRE) estate-wide.',
        'National Gov Transversal Superadmin #2 provisions Department Superadmins across all organs of state. Each Dept Superadmin then provisions Branch Admins within its tenancy.',
        'Strict Non-Escalation: Every tier can only grant roles at or below its own node — never sideways, never upward.',
        'Authoritative HR Verification: Every new user must bind to a real government Person ID from SITA SAP HCM or National Treasury PERSAL before being activated.',
        'Immutable Audit Log: All provisioning, scoping, and privilege changes are permanently recorded for Auditor-General review.',
      ],
      suggestedAction: {
        label: '👑 Open SITA Superadmin #1 Console (admin@)',
        action: async () => {
          await loginDemo('admin');
          navigate('/sita/admin');
        },
      },
      secondaryActions: [
        {
          label: '🏛 Open National Gov Transversal Superadmin #2 Console (transversal@)',
          action: async () => {
            await loginDemo('transversal-admin');
            navigate('/national/admin');
          },
        },
        {
          label: '🏢 Open DHA Department Admin Console (deptadmin-ha@)',
          action: async () => {
            await loginDemo('deptadmin-ha', { department_id: 'home-affairs-digital', branch_id: null, province_id: null });
            navigate('/dept/admin');
          },
        },
        {
          label: '📍 Open DHA Branch Admin Console (branchadmin-ha@)',
          action: async () => {
            await loginDemo('branchadmin-ha', { department_id: 'home-affairs-digital', branch_id: 'dha-immigration', province_id: null });
            navigate('/branch/admin');
          },
        },
      ],
    },
    {
      actNumber: 6,
      title: 'Act 6: Export & Reporting Engine',
      subtitle: 'Auditor-General Digital Signatures & Multi-Format Exports',
      talkingPoints: [
        'Auditor-General Attestations: Cryptographically signed SHA-256 compliance exports verifying immutable data state.',
        'Multi-Format Deliverables: Executive Word briefs (.docx), styled spreadsheets (.xlsx), and raw telemetry CSVs.',
        'Transversal Benchmarking: Compare DHA risk posture against peer national departments while preserving tenant anonymity.',
        'Single-click generation for executive board packs and parliamentary committee presentations.',
      ],
      suggestedAction: {
        label: '📜 View AG Compliance Attestations',
        action: async () => {
          if (!user) await loginDemo('exec');
          navigate('/national/compliance');
        },
      },
      secondaryActions: [
        {
          label: '📑 Open Executive Pitch Deck',
          action: () => window.open('/presentation.html', '_blank'),
        },
      ],
    },
    {
      actNumber: 7,
      title: 'Act 7: Security & Architecture Deep-Dive',
      subtitle: 'Production Hardening & Verification Artifacts',
      talkingPoints: [
        'Full Microservice Isolation: 6 distinct Docker containers (Backend, Ingestion, Processing, Dispatch, Analytics, Frontend).',
        'Cryptographic Hardening: Null-byte injection prevention, alg:none JWT rejection, and field-level AES-256 PII encryption.',
        'High-Availability Resiliency: Token bucket rate limiters, circuit breakers for third-party inference, and Dead Letter Queues (DLQ).',
        '100% Automated Test Pass: 28 comprehensive test suites verifying tenancy isolation, audit immutability, and OWASP compliance.',
      ],
      suggestedAction: {
        label: '🏛️ Open Architecture Blueprint',
        action: () => window.open('/architecture.html', '_blank'),
      },
      secondaryActions: [
        {
          label: '📋 Handover Presentation',
          action: () => window.open('/handover_presentation.html', '_blank'),
        },
        {
          label: '🏠 Return to Home Act',
          action: () => {
            setCurrentActIndex(0);
            navigate('/');
          },
        },
      ],
    },
  ];

  const currentAct = acts[currentActIndex];

  return (
    <aside 
      className={`demo-tour-guide ${isOpen ? 'open' : 'minimized'}`}
      aria-label="Demo Tour Guide"
    >
      {!isOpen ? (
        <button
          type="button"
          className="demo-tour-pill"
          onClick={() => setIsOpen(true)}
          title="Open SITA PoC Demo Tour Guide"
          aria-expanded="false"
        >
          <span className="pill-pulse" />
          <span className="pill-icon">🎯</span>
          <span className="pill-text">SITA Demo Co-Pilot (Act {currentAct.actNumber}/7)</span>
        </button>
      ) : (
        <div className="demo-tour-card">
          {/* Card Header */}
          <div className="demo-tour-header">
            <div className="demo-tour-title-wrap">
              <span className="demo-tour-badge">SITA PoC Demo Co-Pilot</span>
              <h3 className="demo-tour-title">{currentAct.title}</h3>
              <p className="demo-tour-sub">{currentAct.subtitle}</p>
            </div>
            <div className="demo-tour-controls">
              <button
                type="button"
                className="demo-tour-min-btn"
                onClick={() => setIsOpen(false)}
                title="Minimize guide"
                aria-label="Minimize"
              >
                —
              </button>
            </div>
          </div>

          {/* Act Selector Bar */}
          <div className="demo-tour-stepper">
            {acts.map((act, idx) => (
              <button
                key={act.actNumber}
                type="button"
                className={`stepper-dot ${idx === currentActIndex ? 'active' : ''} ${idx < currentActIndex ? 'completed' : ''}`}
                onClick={() => setCurrentActIndex(idx)}
                title={`Act ${act.actNumber}: ${act.title}`}
              >
                {act.actNumber}
              </button>
            ))}
          </div>

          {/* Talking Points */}
          <div className="demo-tour-body">
            <div className="demo-tour-section-label">📢 Executive Talking Points:</div>
            <ul className="demo-tour-points">
              {currentAct.talkingPoints.map((point, idx) => (
                <li key={idx}>
                  <span className="point-bullet">›</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Action Trigger Buttons */}
          <div className="demo-tour-actions">
            {currentAct.suggestedAction && (
              <button
                type="button"
                className="demo-tour-btn primary"
                onClick={currentAct.suggestedAction.action}
              >
                {currentAct.suggestedAction.label}
              </button>
            )}
            {currentAct.secondaryActions && currentAct.secondaryActions.length > 0 && (
              <div className="demo-tour-secondary-row">
                {currentAct.secondaryActions.map((sec, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="demo-tour-btn secondary"
                    onClick={sec.action}
                  >
                    {sec.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer Navigation */}
          <div className="demo-tour-footer">
            <button
              type="button"
              className="demo-tour-nav-btn"
              disabled={currentActIndex === 0}
              onClick={() => setCurrentActIndex((prev) => Math.max(0, prev - 1))}
            >
              ◀ Previous Act
            </button>
            <span className="demo-tour-progress-text">
              Act {currentAct.actNumber} of {acts.length}
            </span>
            <button
              type="button"
              className="demo-tour-nav-btn"
              disabled={currentActIndex === acts.length - 1}
              onClick={() => setCurrentActIndex((prev) => Math.min(acts.length - 1, prev + 1))}
            >
              Next Act ▶
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
