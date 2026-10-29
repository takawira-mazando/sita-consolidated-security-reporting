import React, { useEffect, useRef, useState } from 'react';
import LoginPage from './LoginPage';
import { useAuth } from '../hooks/useAuth';
import { useDemoMode } from '../context/DemoContext';
import { fetchSummary, PublicSummary } from '../api/auth';
import DemoDirectorModal from '../components/layout/DemoDirectorModal';
import '../styles/home.css';

export interface MatrixRow {
  role: string;
  tag: string;
  loginRole?: string;
  scope: string;
  alerts: boolean;
  vulns: boolean;
  logs: boolean;
  compliance: boolean;
  infra: boolean;
}

const MATRIX_COLUMNS = [
  { key: 'alerts', label: 'Alerts' },
  { key: 'vulns', label: 'Vulns' },
  { key: 'logs', label: 'Access Logs' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'infra', label: 'Infra' },
] as const;

const MATRIX_ROWS: MatrixRow[] = [
  // ── National Strategic Roles ──────────────────────────────────────────────
  {
    role: 'Executive',
    tag: 'exec@',
    loginRole: 'exec',
    scope: 'National · whole estate',
    // auth.py: risks, compliance, alerts, alerts_read, alerts_write, findings, dashboard
    alerts: true, vulns: true, logs: false, compliance: true, infra: false,
  },
  {
    role: 'Compliance',
    tag: 'compliance@',
    loginRole: 'compliance',
    scope: 'National · whole estate',
    // auth.py: compliance, dashboard
    alerts: false, vulns: false, logs: false, compliance: true, infra: false,
  },
  {
    role: 'Service Ops (SRE)',
    tag: 'sre@',
    loginRole: 'sre',
    scope: 'National · whole estate',
    // auth.py: admin_read, admin_write, alerts_read, dashboard
    alerts: true, vulns: false, logs: false, compliance: false, infra: true,
  },
  // ── Specialized Security Operations ──────────────────────────────────────
  {
    role: 'SOC Analyst',
    tag: 'soc@',
    loginRole: 'soc-ha',
    scope: 'Assigned departments/branches',
    // auth.py: findings, alerts_read, alerts_write, dashboard
    alerts: true, vulns: true, logs: false, compliance: false, infra: false,
  },
  {
    role: 'AppSec Engineer',
    tag: 'appsec@',
    loginRole: 'appsec-ha',
    scope: 'Assigned departments/branches',
    // auth.py: risks, findings, dashboard
    alerts: false, vulns: true, logs: false, compliance: false, infra: false,
  },
  {
    role: 'DB Security (DbSec)',
    tag: 'dbsec@',
    loginRole: 'dbsec-ha',
    scope: 'Assigned departments/branches',
    // auth.py: risks, findings, alerts_read, dashboard
    alerts: true, vulns: true, logs: true, compliance: false, infra: false,
  },
  {
    role: 'Local AppSec',
    tag: 'localappsec@',
    loginRole: 'local-appsec',
    scope: 'Branch (province dept)',
    // auth.py: risks, findings, dashboard
    alerts: false, vulns: true, logs: false, compliance: false, infra: false,
  },
  // ── Provincial Cybersecurity ──────────────────────────────────────────────
  {
    role: 'Provincial SOC Lead',
    tag: 'provincesoc@',
    loginRole: 'province-soc-lead',
    scope: 'One province · peer-blinded',
    // auth.py: findings, alerts_read, alerts_write, dashboard
    alerts: true, vulns: true, logs: false, compliance: false, infra: false,
  },
  {
    role: 'Provincial Dept Admin',
    tag: 'provdeptadmin@',
    loginRole: 'province-dept-admin',
    scope: 'Provincial Department (Tier 2 Control Plane)',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
  // ── Administrative Tiers (Pure Control Plane — Delegated Provisioning) ──
  {
    role: 'Branch Admin',
    tag: 'branchadmin@',
    loginRole: 'branchadmin-ha',
    scope: 'Tier 1 · DDG operational branch (DHA)',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
  {
    role: 'Department Superadmin',
    tag: 'deptadmin@',
    loginRole: 'deptadmin-ha',
    scope: 'Tier 2 · Department of Home Affairs (DHA)',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
  {
    role: 'National Gov Transversal Superadmin #2',
    tag: 'transversal@',
    loginRole: 'transversal-admin',
    scope: 'Tier 3 · Sovereign multi-department estate',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
  {
    role: 'SITA Superadmin #1',
    tag: 'admin@',
    loginRole: 'admin',
    scope: 'Tier 4 · SITA Command Center (primary contact)',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
  {
    role: 'Platform Provider / Developer',
    tag: 'operator@',
    loginRole: 'operator',
    scope: 'Tier 5 · Platform root developer / creator',
    alerts: false, vulns: false, logs: false, compliance: false, infra: false,
  },
];

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

const FEATURES = [
  {
    icon: '◈',
    title: 'One fused risk score',
    body: 'AppScan, Imperva DAM, Imperva WAF, API exposure, and compliance controls are blended into a single transparent 0–100 score per application — no more reconciling four OEM consoles before a meeting.',
  },
  {
    icon: '🧠',
    title: 'Grounded AI Intelligence (AIMI)',
    body: 'A 4-layer AI control model sits above the warehouse. Layers 1, 2 & 4 are deterministic — only Layer 3 (AIMI provider) runs inference, and only for campaign attribution (AVP-3) and risk causality (AVP-8). Zero raw logs reach the model.',
  },
  {
    icon: '▤',
    title: 'Action-level accountability',
    body: 'Every acknowledge, resolve, and dead-letter reprocess is recorded with who and when — giving compliance a verifiable trail without a ticket.',
  },
  {
    icon: '◔',
    title: 'Dual-axis RBAC + Tenancy',
    body: '14 platform roles enforced across a 5-tier government hierarchy. Tenancy controls which department a user may access; RBAC controls which claim classes the AI may surface within that department — enforced at Layer 1, 2, and 4.',
  },
  {
    icon: '⚙',
    title: 'Config-driven, not code-driven',
    body: 'New sources and detection rules are added through YAML field mappers and alert rules — onboarding a connector never requires a redeploy.',
  },
  {
    icon: '⇄',
    title: 'Built to never miss a signal',
    body: 'Circuit breakers, token-bucket rate limiting, retry with backoff, and a dead-letter queue with one-click reprocess keep the pipeline resilient.',
  },
  {
    icon: '↯',
    title: 'Dispatch where your team works',
    body: 'High and critical alerts route automatically to email, Microsoft Teams, and PagerDuty — enriched with app owner, team, and priority.',
  },
  {
    icon: '🔒',
    title: 'POPIA NFR-AI-11 Enforced',
    body: 'Citizen ID numbers, source IPs, employee logins, and raw SQL queries are structurally barred from leaving the platform. redaction.py scrubs all outbound AI payloads. Only public CVE/MITRE identifiers cross the boundary.',
  },
];

const PIPELINE_STAGES = [
  { n: '01', title: 'Ingest', body: 'OEM connectors poll AppScan, Imperva DAM, Imperva WAF, API Security, and compliance sources — with rate limiting and circuit breakers.' },
  { n: '02', title: 'Normalise', body: 'Vendor-speak becomes one schema: canonical severity, UTC timestamps, typed fields, and de-duplication across every source.' },
  { n: '03', title: 'Correlate', body: 'YAML rules fire on records and aggregates — critical spikes, shadow APIs, compliance drops, and 3-sigma anomalies.' },
  { n: '04', title: 'Score', body: 'A weighted 0–100 fused risk score per application, bucketed safe / monitored / critical, recomputed every 5 minutes.' },
  { n: '05', title: 'Dispatch', body: 'Severity-gated routing to email, Teams, and PagerDuty — each alert enriched with app ownership and priority.' },
];

/** Display order and colour per fusion signal. The percentages are NOT here —
 *  they come from `/api/v1/public/summary`, which serves
 *  `risk_engine.DEFAULT_WEIGHTS` directly. A literal copy of these numbers is
 *  the drift this project has already paid for once: the dashboard narrative
 *  asserted 40/30/20/10 while the engine was 35/25/20/20, and nothing failed.
 */
const FUSION_SIGNALS = [
  { key: 'appscan', label: 'AppScan findings', color: 'var(--flare-1)' },
  { key: 'imperva', label: 'Imperva violations', color: 'var(--flare-2)' },
  { key: 'exposure', label: 'API exposure', color: 'var(--link)' },
  { key: 'compliance', label: 'Compliance penalty', color: 'var(--ok)' },
] as const;

/** Last-resort fallback so the section still renders if the endpoint is older
 *  than this build. Never preferred over the served value. */
const FALLBACK_WEIGHTS: Record<string, number> = {
  appscan: 0.35,
  imperva: 0.25,
  exposure: 0.2,
  compliance: 0.2,
};

const SOURCES = [
  { name: 'HCL AppScan', kind: 'AppSec · SAST/DAST' },
  { name: 'Imperva DAM', kind: 'Database activity' },
  { name: 'Imperva WAF', kind: 'Web application firewall' },
  { name: 'API Security', kind: 'Shadow API discovery' },
  { name: 'POPIA', kind: 'Compliance control data' },
  { name: 'ISO 27001', kind: 'Compliance control data' },
];

const PREVIEW_APPS = [
  { app: 'payments-api', score: 82, bucket: 'critical' },
  { app: 'customer-portal', score: 57, bucket: 'monitored' },
  { app: 'identity-svc', score: 44, bucket: 'monitored' },
  { app: 'retail-web', score: 19, bucket: 'safe' },
];

const PREVIEW_TREND = [34, 41, 38, 52, 48, 61, 58, 66, 62, 71, 68, 74];

function PreviewTrend({ values }: { values: number[] }) {
  const max = Math.max(...values);
  return (
    <div className="preview-chart">
      {values.map((v, i) => (
        <div key={i} className="preview-bar" style={{ height: `${(v / max) * 100}%`, background: i === values.length - 1 ? 'var(--flare-1)' : 'var(--line)' }} />
      ))}
    </div>
  );
}

const NAV_SECTIONS = [
  { id: 'capabilities', label: 'Capabilities' },
  { id: 'preview', label: 'Risk Scoring' },
  { id: 'tenancy', label: 'Multi-Tenancy' },
  { id: 'pipeline', label: 'Data Pipeline' },
  { id: 'ai-layer', label: 'AI Layer' },
  { id: 'matrix', label: '14-Role Matrix' },
] as const;

const RESOURCE_LINKS = [
  { href: '/standalone_demo.html', label: 'Standalone Showcase', icon: '⚡', accent: 'amber' },
  { href: '/presentation.html', label: 'Executive Deck', icon: '📊', accent: 'amber' },
  { href: '/handover_presentation.html', label: 'Handover Deck', icon: '🤝', accent: 'emerald' },
  { href: '/architecture.html', label: 'Architecture', icon: '🏛️', accent: 'blue' },
] as const;

interface RolePerspective {
  roleId: string;
  roleTag: string;
  roleTitle: string;
  category: string;
  tenantScope: string;
  tenantBadgeColor: string;
  insightsDelivered: string;
  allowedClaims: string[];
  blockedClaims: string[];
}

const ROLE_PERSPECTIVES: RolePerspective[] = [
  {
    roleId: 'exec',
    roleTag: 'exec@',
    roleTitle: 'Executive / Director-General / CISO',
    category: 'National Strategic',
    tenantScope: 'National · Whole Estate (All Organs of State)',
    tenantBadgeColor: '#1082ff',
    insightsDelivered: 'AI continuously synthesizes estate posture into a single 0–100 executive risk index, forecasts 14-day exposure trends, and evaluates POPIA Section 22 compliance. Layer 4 automatically scrubs low-level technical CVEs and code sinks before executive delivery.',
    allowedClaims: ['headline_metrics (0–100 fused index)', 'risk_buckets (safe/monitored/critical)', 'popia_conditions (statutory standing)'],
    blockedClaims: ['cve_ids & cwe_ids (technical flaw noise)', 'raw_evidence (stack traces & sinks)', 'remediation_steps (developer diffs)'],
  },
  {
    roleId: 'soc',
    roleTag: 'soc@',
    roleTitle: 'SOC Analyst',
    category: 'Specialized SecOps',
    tenantScope: 'Department of Home Affairs (Tier 2 Tenant)',
    tenantBadgeColor: '#009bd4',
    insightsDelivered: 'AI correlates real-time Imperva DAM database telemetry with WAF perimeter alerts, clusters attacks by MITRE ATT&CK technique (e.g. T1190), analyzes threat causality, and formulates automated D3FEND countermeasure recommendations scoped to assigned assets.',
    allowedClaims: ['headline_metrics', 'risk_buckets', 'cve_ids & MITRE technique tags', 'app_names (assigned tenant)', 'remediation_steps (D3FEND rules)'],
    blockedClaims: ['raw_evidence (PII & citizen payloads)', 'popia_legal_penalties (statutory liabilities)'],
  },
  {
    roleId: 'compliance',
    roleTag: 'compliance@',
    roleTitle: 'Compliance Officer / AGSA Liaison',
    category: 'Assurance & Audit',
    tenantScope: 'National · Whole Estate (Audit Scoped)',
    tenantBadgeColor: '#10b981',
    insightsDelivered: 'AI evaluates statutory compliance posture, cross-references ISO 27001 control gaps with POPIA Section 22 notification windows, and generates tamper-evident Auditor-General (AGSA) readiness briefings with asymmetric ECDSA NIST P-256 PKI digital signing for air-gapped verification.',
    allowedClaims: ['headline_metrics', 'risk_buckets', 'popia_conditions (statutory windows)', 'audit_attestations (ECDSA P-256 signatures)'],
    blockedClaims: ['cve_ids & cwe_ids (masked from audit views)', 'raw_evidence (sensitive query strings)', 'developer_diffs'],
  },
  {
    roleId: 'appsec',
    roleTag: 'appsec@',
    roleTitle: 'AppSec Engineer',
    category: 'Specialized SecOps',
    tenantScope: 'Assigned Department & Branch Subtrees',
    tenantBadgeColor: '#a78bfa',
    insightsDelivered: 'AI correlates AppScan SAST/DAST vulnerabilities with live Imperva WAF triggers, maps flaws to OWASP Top 10 and CWE traces, performs root-cause sink analysis, and formulates actionable Git patch remediation diffs for branch software engineering teams.',
    allowedClaims: ['cve_ids & cwe_ids', 'raw_evidence (code sinks & call graphs)', 'remediation_steps (patch diffs)', 'app_names'],
    blockedClaims: ['executive_financial_impact', 'cross_tenant_telemetry (other departments)'],
  },
];

export default function HomePage() {
  const { loginDemo, demoAccounts } = useAuth();
  const { demoMode, toggleDemoMode } = useDemoMode();
  const [modalOpen, setModalOpen] = useState(false);
  const [directorOpen, setDirectorOpen] = useState(false);
  const [aiMatrixOpen, setAiMatrixOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');
  const [summary, setSummary] = useState<PublicSummary | null>(null);
  const [demoLoginLoading, setDemoLoginLoading] = useState(false);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('');
  const [selectedPerspective, setSelectedPerspective] = useState<string>('exec');
  const resourcesRef = useRef<HTMLDivElement | null>(null);

  const openDemoCoPilot = () => {
    setDirectorOpen(true);
    window.dispatchEvent(new CustomEvent('sita_open_demo_guide'));
  };

  const activePerspective = ROLE_PERSPECTIVES.find((p) => p.roleId === selectedPerspective) ?? ROLE_PERSPECTIVES[0];

  // Fusion weights, resolved once. Served by the API from the risk engine;
  // the fallback exists only so the section renders against an older backend.
  const servedWeights = summary?.risk.weights;
  const FUSION_ROWS = FUSION_SIGNALS.map((sig) => ({
    key: sig.key,
    label: sig.label,
    color: sig.color,
    pct: Math.round((servedWeights?.[sig.key] ?? FALLBACK_WEIGHTS[sig.key] ?? 0) * 100),
  }));
  const fusionSummary = servedWeights
    ? `${FUSION_ROWS.map((r) => `${r.label} ${r.pct}%`).join(', ')}. ` +
      'Every component is visible and exportable — nothing black-boxed.'
    : 'Every component is visible and exportable — nothing black-boxed.';

  const loginAsDemo = async () => {
    setDemoLoginLoading(true);
    try {
      // SOC Analyst is scoped to home-affairs-digital (Department of Home Affairs)
      const result = await loginDemo('soc');
      if (result.ok) {
        window.location.href = '/soc'; // Navigate to SOC dashboard
      }
    } catch (err) {
      console.error('Demo login failed:', err);
    } finally {
      setDemoLoginLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    fetchSummary()
      .then((s) => {
        if (!cancelled) setSummary(s);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleTheme = () => {
    const next = isDark ? 'light' : 'dark';
    document.body.dataset.theme = next;
    localStorage.setItem('sita_theme', next);
    setIsDark(!isDark);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeModal();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, []);

  // Highlight the nav link for the section currently in view.
  useEffect(() => {
    const onScroll = () => {
      const probe = window.innerHeight * 0.3;
      let current = '';
      for (const { id } of NAV_SECTIONS) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= probe) current = id;
      }
      setActiveSection(current);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  // Close the Resources menu on outside click or Escape.
  useEffect(() => {
    if (!resourcesOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (resourcesRef.current && !resourcesRef.current.contains(e.target as Node)) {
        setResourcesOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setResourcesOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [resourcesOpen]);

  const openModal = () => {
    setModalOpen(true);
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setModalOpen(false);
    document.body.style.overflow = '';
  };

  const loginAsRole = async (role: string) => {
    document.body.style.overflow = '';
    const effectiveRole = role === 'transversal' ? 'transversal-admin' : role;
    const res = await loginDemo(effectiveRole);
    if (res.ok) {
      const routeMap: Record<string, string> = {
        'exec': '/national/exec',
        'compliance': '/national/compliance',
        'sre': '/national/sre',
        'soc': '/dept/soc',
        'soc-ha': '/dept/soc',
        'appsec': '/dept/appsec',
        'appsec-ha': '/dept/appsec',
        'dbsec': '/dept/dbsec',
        'dbsec-ha': '/dept/dbsec',
        'local-appsec': '/branch/appsec',
        'province-soc-lead': '/dept/soc',
        'province-dept-admin': '/dept/admin',
        'branchadmin-ha': '/branch/admin',
        'deptadmin-ha': '/dept/admin',
        'transversal-admin': '/national/admin',
        'admin': '/sita/admin',
        'operator': '/sita/admin',
      };
      const target = routeMap[effectiveRole] || '/national/exec';
      window.location.href = target;
    }
  };

  return (
    <div className="home-page">
      <header className="site">
        <div className="container">
          <a href="#" className="logo">
            <img className="home-logo-img" src="/sita-logo.gif" alt="SITA" />
          </a>
          <nav className="primary" aria-label="Section navigation">
            {NAV_SECTIONS.map(({ id, label }) => (
              <a
                key={id}
                href={`#${id}`}
                className={activeSection === id ? 'is-active' : undefined}
                aria-current={activeSection === id ? 'true' : undefined}
              >
                {label}
              </a>
            ))}
            <div className="nav-resources" ref={resourcesRef}>
              <button
                type="button"
                className={`nav-resources-trigger${resourcesOpen ? ' is-open' : ''}`}
                aria-expanded={resourcesOpen}
                aria-haspopup="true"
                onClick={() => setResourcesOpen((v) => !v)}
              >
                Resources
                <span className="caret" aria-hidden="true" />
              </button>
              {resourcesOpen && (
                <div className="nav-resources-menu" role="menu">
                  {RESOURCE_LINKS.map(({ href, label, icon, accent }) => (
                    <a
                      key={href}
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      role="menuitem"
                      className={`nav-resource-item accent-${accent}`}
                    >
                      <span className="nav-resource-icon" aria-hidden="true">{icon}</span>
                      <span className="nav-resource-text">
                        <span className="nav-resource-label">{label}</span>
                        <span className="nav-resource-hint">Opens in new tab</span>
                      </span>
                      <span className="nav-resource-arrow" aria-hidden="true">↗</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </nav>
          <div className="home-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              className="btn btn-flare"
              style={{
                background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
                color: '#fff',
                border: 'none',
                fontWeight: 700,
                fontSize: '12.5px',
                padding: '7px 16px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 4px 14px rgba(124, 58, 237, 0.35)',
              }}
              onClick={openDemoCoPilot}
              title="Open SITA PoC Demo Co-Pilot & Flow Director"
            >
              <span>⚡</span> SITA PoC Demo Co-Pilot
            </button>
            <button className="theme-toggle" onClick={toggleTheme}>
              {isDark ? '☀ Light' : '🌙 Dark'}
            </button>
            <button className="btn btn-outline" onClick={openModal}>Sign In</button>
          </div>
        </div>
      </header>

      {demoMode && (
        <div className="demo-banner" onClick={() => toggleDemoMode()}>
          <span>🧪 <strong>DEMO MODE ACTIVE</strong> — Showing seeded test data from AppScan, Imperva WAF & API Security connectors. Click to dismiss.</span>
          <button className="demo-banner-dismiss" onClick={(e) => { e.stopPropagation(); toggleDemoMode(); }} aria-label="Dismiss demo banner">✕</button>
        </div>
      )}

      <section className="hero">
        <div className="container hero-grid">
          <div>
            <h1>Unified Security Intelligence.<br />Governed by <span className="gradient-text">14-Role Government Tenancy.</span></h1>
            <p className="lede">
              This solution fuses AppScan, Imperva DAM &amp; WAF, and compliance telemetry into an auditable 0–100 risk score — delivering role-tailored security intelligence while deterministically enforcing POPIA and claim-level RBAC across all 5 government tiers.
            </p>
            <div className="cta-row" style={{ flexWrap: 'wrap', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button
                className="btn btn-flare"
                style={{
                  background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '13.5px',
                  padding: '11px 22px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 16px rgba(124, 58, 237, 0.4)',
                }}
                onClick={openDemoCoPilot}
              >
                <span>⚡</span> SITA PoC Demo Co-Pilot
              </button>
              <button className="btn btn-outline" onClick={openModal}>Sign In to Explore</button>
            </div>
          </div>

          <div className="hero-preview" aria-hidden="false">
            <div className="preview-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', borderBottom: '1px solid var(--line)', paddingBottom: '10px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--flare-1)', fontWeight: 700 }}>
                    <span className="dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--ok)' }} />
                    AI-Powered Role Intelligence
                  </div>
                  <div style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--hi)', marginTop: '2px' }}>
                    {activePerspective.roleTitle}
                  </div>
                </div>
                <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '4px', background: `${activePerspective.tenantBadgeColor}20`, color: activePerspective.tenantBadgeColor, fontWeight: 700 }}>
                  {activePerspective.roleTag}
                </span>
              </div>

              {/* Role selector buttons */}
              <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', flexWrap: 'wrap' }}>
                {ROLE_PERSPECTIVES.map((p) => (
                  <button
                    key={p.roleId}
                    type="button"
                    onClick={() => setSelectedPerspective(p.roleId)}
                    style={{
                      background: selectedPerspective === p.roleId ? 'var(--flare-1)' : 'var(--panel-2)',
                      color: selectedPerspective === p.roleId ? '#fff' : 'var(--mid)',
                      border: '1px solid var(--line)',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '11.5px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {p.roleTag}
                  </button>
                ))}
              </div>

              {/* Tenancy Scope Box */}
              <div style={{ background: 'var(--panel-2)', border: '1px solid var(--line)', borderRadius: '8px', padding: '9px 12px', marginBottom: '10px' }}>
                <div style={{ fontSize: '10px', color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>Authorized Tenant Scope</div>
                <div style={{ fontSize: '12px', color: 'var(--hi)', fontWeight: 600, marginTop: '2px' }}>
                  {activePerspective.tenantScope}
                </div>
              </div>

              {/* What AI Delivers Scope Box */}
              <div style={{ background: 'rgba(0, 155, 212, 0.08)', border: '1px solid rgba(0, 155, 212, 0.3)', borderRadius: '10px', padding: '12px', marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#009bd4', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>🧠</span> What AI Delivers for this Role
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--dim)', fontStyle: 'italic' }}>Layer 4 Verified &amp; Grounded</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--hi)', lineHeight: 1.55, margin: 0 }}>
                  {activePerspective.insightsDelivered}
                </p>
              </div>

              {/* Layer 4 Claim Enforcement Status */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px', fontSize: '11px' }}>
                <div style={{ background: 'rgba(0, 175, 102, 0.08)', border: '1px solid rgba(0, 175, 102, 0.25)', borderRadius: '6px', padding: '8px' }}>
                  <div style={{ color: '#00af66', fontWeight: 700, marginBottom: '4px' }}>✅ AI Claim Classes Permitted</div>
                  {activePerspective.allowedClaims.map((c) => (
                    <div key={c} style={{ color: 'var(--mid)', fontSize: '10.5px', lineHeight: 1.4 }}>• {c}</div>
                  ))}
                </div>
                <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '6px', padding: '8px' }}>
                  <div style={{ color: '#ef4444', fontWeight: 700, marginBottom: '4px' }}>❌ Blocked by AI Layer 4</div>
                  {activePerspective.blockedClaims.map((c) => (
                    <div key={c} style={{ color: 'var(--mid)', fontSize: '10.5px', lineHeight: 1.4 }}>• {c}</div>
                  ))}
                </div>
              </div>

              {/* Zero Telemetry Leak Warning Banner */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', background: 'rgba(167, 139, 250, 0.08)', border: '1px solid rgba(167, 139, 250, 0.25)', borderRadius: '6px', fontSize: '11px', color: 'var(--mid)' }}>
                <span style={{ fontSize: '14px', flexShrink: 0 }}>🔒</span>
                <span><strong>POPIA &amp; Tenancy Enforced:</strong> Zero raw logs leave the platform (POPIA NFR-AI-11). The 4-layer AI control model evaluates all outputs deterministically before display.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="problem-section" id="capabilities">
        <div className="container">
          <div className="section-head" style={{ maxWidth: '800px' }}>
            <div className="eyebrow"><span className="dot"></span>Platform capabilities</div>
            <h2>One platform. Six security domains. Zero manual reconciliation.</h2>
          </div>
          <div className="problem-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
            <div className="problem-card" style={{ borderTop: '3px solid #1082ff' }}>
              <div className="problem-n">◈ &nbsp;Fused 0–100 Risk Score</div>
              <p>AppScan SAST/DAST, Imperva DAM, Imperva WAF, API exposure, and compliance controls are weighted and blended into a single score per application — recomputed every 5 minutes. No black boxes: every weight is visible and exportable.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #009bd4' }}>
              <div className="problem-n">🧠 &nbsp;Grounded AI Intelligence (AIMI)</div>
              <p>A 4-layer control model generates role-specific security briefings. Only Layer 3 runs an external model — for campaign attribution and risk-delta causality. Layers 1, 2 &amp; 4 are deterministic. Zero raw logs leave the platform (POPIA NFR-AI-11).</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #a78bfa' }}>
              <div className="problem-n">🎯 &nbsp;14-Role RBAC + Dual-Axis Tenancy</div>
              <p>14 platform roles across a 5-tier government hierarchy, enforced at API, database, and AI layers simultaneously. Tenancy controls <em>which department</em> you see. RBAC controls <em>which claim classes</em> the AI may surface within that department.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #00af66' }}>
              <div className="problem-n">⚡ &nbsp;Real-Time Alert Dispatch</div>
              <p>Severity-gated routing to email, Microsoft Teams, and PagerDuty — each alert enriched with app owner, team, department, and priority. Circuit breakers, token-bucket rate limiting, retry backoff, and a dead-letter queue with one-click reprocess.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #f59e0b' }}>
              <div className="problem-n">📜 &nbsp;POPIA, ISO 27001 &amp; AGSA Compliance</div>
              <p>POPIA Section 22 breach exposure analysis, ISO 27001 gap tracking, and Auditor-General (AGSA) readiness reports with asymmetric ECDSA NIST P-256 PKI digital signing (SECP256R1) providing mathematical non-repudiation and offline, air-gapped OpenSSL verification. Compliance Officers get dedicated briefings auto-generated per quarter.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #10b981' }}>
              <div className="problem-n">🔄 &nbsp;Config-Driven Connector Onboarding</div>
              <p>New OEM sources are added through YAML field mappers — no redeploy required. Every finding carries <code>department_id</code> and <code>branch_id</code> at write time, eliminating cross-tenant leaks at the database level. The pipeline scales as an independently deployable service.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="preview-section" id="preview">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Risk scoring · live from the warehouse</div>
            <h2>Four sources. One score. Every weight visible.</h2>
          </div>
          <div className="fusion-wrap">
            <div className="fusion-main">
              <div className="fusion-score-head">
                <span>How the score is built</span>
                <span className="preview-mono">weighted · 0–100</span>
              </div>
              {FUSION_ROWS.map((row) => (
                  <div key={row.key} className="fusion-row">
                    <span className="fusion-label">{row.label}</span>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${row.pct}%`, background: row.color }} /></div>
                    <span className="fusion-pct">{row.pct}%</span>
                  </div>
                ))}
              <p className="fusion-note">
                {fusionSummary}
              </p>
            </div>
            <div className="fusion-side">
              <div className="fusion-side-t">Score buckets</div>
              <div className="fusion-bucket"><span className="b-chip b-critical">Critical</span><span>needs attention now</span></div>
              <div className="fusion-bucket"><span className="b-chip b-monitored">Monitored</span><span>elevated but being watched</span></div>
              <div className="fusion-bucket"><span className="b-chip b-safe">Safe</span><span>within acceptable posture</span></div>
              <div style={{ marginTop: '16px', padding: '10px 12px', background: 'rgba(16, 130, 255, 0.06)', border: '1px solid rgba(16, 130, 255, 0.2)', borderRadius: '8px', fontSize: '11.5px', color: 'var(--mid)', lineHeight: 1.5 }}>
                <div style={{ fontWeight: 700, color: 'var(--hi)', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span>⏱️</span> Dynamic 5-Min Recalculation
                </div>
                Scores are blended from warehouse OEM telemetry — zero black-box heuristics.
              </div>
            </div>
          </div>

          {/* Sources Feeding Score: Horizontal Flowing Marquee (Right-to-Left) */}
          <div className="sources-marquee-container">
            <div className="sources-marquee-label">
              <span className="live-dot" />
              <span>Sources Feeding Score</span>
            </div>
            <div className="sources-marquee-viewport">
              <div className="sources-marquee-track">
                {[...SOURCES, ...SOURCES].map((s, idx) => (
                  <div key={`${s.name}-${idx}`} className="sources-marquee-chip">
                    <span className="chip-dot" />
                    <span className="chip-name">{s.name}</span>
                    <span className="chip-kind">{s.kind}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="tenancy-graphic-section" id="tenancy">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Government Multi-Tenancy · ~173 National &amp; Provincial Departments</div>
            <h2>Security Intelligence Across All Organs of State</h2>
          </div>

          <div className="tenancy-diagram-box">
            {/* Tier 5 & 4: SITA Platform Operator & National Estate */}
            <div className="tenancy-tier-row tier-root">
              <div className="tier-badge-label">Tier 5 & 4 · SITA Platform Provider & National Superadmin</div>
              <div className="tenancy-node-card root-node">
                <div className="node-icon">🇿🇦</div>
                <div className="node-info">
                  <div className="node-title">SITA National Security Command Center</div>
                  <div className="node-desc">State Information Technology Agency (SITA) Platform Provider & National Superadmin</div>
                  <div className="node-tags">
                    <span className="n-tag t-admin">admin@</span>
                    <span className="n-tag t-op">operator@</span>
                    <span className="n-tag t-exec">exec@</span>
                    <span className="n-tag t-comp">compliance@</span>
                    <span className="n-tag t-sre">sre@</span>
                  </div>
                </div>
                <div className="node-metrics">
                  <div className="n-metric"><strong>100%</strong><span>National Estate Visibility</span></div>
                  <div className="n-metric"><strong>ECDSA P-256</strong><span>AG Audit Signed</span></div>
                </div>
              </div>
            </div>

            <div className="tenancy-connector-line">
              <div className="line-down"></div>
              <div className="line-split"></div>
            </div>

            {/* Tier 3 & 2: National & Provincial Departments */}
            <div className="tenancy-tier-split">
              {/* National Branch */}
              <div className="tenancy-branch-col">
                <div className="col-header">
                  <span className="col-icon">🏛️</span>
                  <div>
                    <h4>~45 National Departments</h4>
                    <p>National Organs of State (DHA, Treasury, SAPS, Health, DPSA, DOJ...)</p>
                  </div>
                </div>

                <div className="tenancy-node-card dept-node active-dha">
                  <div className="node-badge-top">Live Demo Case · DHA</div>
                  <div className="node-head">
                    <span className="node-flag">🏛️</span>
                    <div>
                      <div className="node-title">Department of Home Affairs (DHA)</div>
                      <div className="node-sub">slug: <code>home-affairs-digital</code></div>
                    </div>
                  </div>
                  <p className="node-body-text">Manages civic registers, border control, identity gateways, and immigration platforms across South Africa.</p>
                  <div className="node-tags">
                    <span className="n-tag t-soc">soc-ha@</span>
                    <span className="n-tag t-app">appsec-ha@</span>
                    <span className="n-tag t-db">dbsec-ha@</span>
                    <span className="n-tag t-dept">deptadmin-ha@</span>
                  </div>
                </div>

                <div className="tenancy-node-card dept-node">
                  <div className="node-head">
                    <span className="node-flag">💳</span>
                    <div>
                      <div className="node-title">National Treasury</div>
                      <div className="node-sub">slug: <code>treasury</code></div>
                    </div>
                  </div>
                  <p className="node-body-text">Oversees national financial systems, revenue, budget allocations, and inter-governmental grants.</p>
                  <div className="node-tags">
                    <span className="n-tag t-dept">treasury.admin@</span>
                    <span className="n-tag t-app">appsec@</span>
                  </div>
                </div>
              </div>

              {/* Provincial Branch */}
              <div className="tenancy-branch-col">
                <div className="col-header">
                  <span className="col-icon">📍</span>
                  <div>
                    <h4>~128 Provincial Departments (across 9 Provinces)</h4>
                    <p>Gauteng, Western Cape, KZN, Eastern Cape, Limpopo, Mpumalanga...</p>
                  </div>
                </div>

                <div className="tenancy-node-card province-node">
                  <div className="node-badge-top">Peer Blinding Engine</div>
                  <div className="node-head">
                    <span className="node-flag">📍</span>
                    <div>
                      <div className="node-title">Gauteng Provincial SOC Lead</div>
                      <div className="node-sub">province_id: <code>gp</code> · 12 Departments</div>
                    </div>
                  </div>
                  <p className="node-body-text">Monitors Gauteng provincial departments with <strong>Anonymized Peer Benchmarking</strong> — comparing posture against peer provinces without seeing their raw findings or PII.</p>
                  <div className="node-tags">
                    <span className="n-tag t-prov">provincesoc@</span>
                    <span className="n-tag t-dept">provdeptadmin@</span>
                  </div>
                </div>

                <div className="tenancy-node-card province-node anonymized">
                  <div className="node-head">
                    <span className="node-flag">🙈</span>
                    <div>
                      <div className="node-title">Peer Provinces (Western Cape, KZN, etc.)</div>
                      <div className="node-sub">Anonymized Benchmark Peers</div>
                    </div>
                  </div>
                  <p className="node-body-text">Exposes aggregated fused risk scores only. Raw vulnerability logs, app names, and PII are strictly blinded by platform security policy.</p>
                </div>
              </div>
            </div>

            <div className="tenancy-connector-line">
              <div className="line-down"></div>
            </div>

            {/* Tier 1: Departmental Branches */}
            <div className="tenancy-tier-row tier-branches">
              <div className="tier-badge-label">Tier 1 · 347 Operational Department Branches (DDG Units)</div>
              <div className="branch-nodes-grid">
                <div className="branch-mini-card">
                  <div className="b-icon">🆔</div>
                  <div>
                    <div className="b-title">DHA Civic Services</div>
                    <div className="b-sub">branch_id: <code>dha-civic</code></div>
                  </div>
                </div>

                <div className="branch-mini-card active-b">
                  <div className="b-icon">💻</div>
                  <div>
                    <div className="b-title">DHA Digital Transformation</div>
                    <div className="b-sub">branch_id: <code>dha-digital</code></div>
                  </div>
                </div>

                <div className="branch-mini-card">
                  <div className="b-icon">🛂</div>
                  <div>
                    <div className="b-title">DHA Immigration Services</div>
                    <div className="b-sub">branch_id: <code>dha-immigration</code></div>
                  </div>
                </div>

                <div className="branch-mini-card">
                  <div className="b-icon">💰</div>
                  <div>
                    <div className="b-title">Treasury Budget Branch</div>
                    <div className="b-sub">branch_id: <code>treasury-budget</code></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4 Pillars of Governance */}
          <div className="tenancy-pillars-grid">
            <div className="pillar-card">
              <div className="p-icon">🛡️</div>
              <h4>Write-Time Denormalization</h4>
              <p>Every finding carries <code>department_id</code> and <code>branch_id</code> at write time, eliminating cross-tenant query leaks at the database level.</p>
            </div>
            <div className="pillar-card">
              <div className="p-icon">🔒</div>
              <h4>Strict Downstream Delegation</h4>
              <p>SITA Superadmin (<code>admin</code>) → Department Admin (<code>dept-admin</code>) → Branch Admin (<code>branch-admin</code>). Authority can never escalate above its subtree node.</p>
            </div>
            <div className="pillar-card">
              <div className="p-icon">🙈</div>
              <h4>Provincial Peer Blinding</h4>
              <p>Provincial SOC Leads compare risk posture against peer provinces with anonymized hashes—never exposing peer findings or PII.</p>
            </div>
            <div className="pillar-card">
              <div className="p-icon">📜</div>
              <h4>AG Audit Attestation</h4>
              <p>Generates Auditor-General compliance exports with asymmetric ECDSA NIST P-256 PKI digital signatures, enabling air-gapped OpenSSL verification without connecting to or trusting SITA infrastructure.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="pipeline-section" id="pipeline">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Event-driven data pipeline · 5 stages</div>
            <h2>From raw OEM signal to actionable decision — automatically</h2>
          </div>
          <div className="pipeline-grid">
            {PIPELINE_STAGES.map((stage) => (
              <div className="pipeline-card" key={stage.n}>
                <div className="pipeline-n">{stage.n}</div>
                <h3>{stage.title}</h3>
                <p>{stage.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>



      {/* ── AI Intelligence Layer Section ───────────────────────────────── */}
      <section className="features" id="ai-layer" style={{ borderTop: '1px solid var(--line)' }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot" style={{ background: '#a78bfa' }}></span>Grounded AI Intelligence Layer</div>
            <h2>The 4-Layer AI Control Model: Only Layer 3 Holds a Model</h2>
          </div>
          <div className="feat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="feat-card" style={{ borderTop: '3px solid #1082ff' }}>
              <div className="fico">🔐</div>
              <h3>Layer 1 · Scope & RBAC Gate</h3>
              <p>Default-deny via <code>tenant_filter()</code> <strong>and</strong> <code>can_access_report()</code>. Freezes <code>scope_hash</code>. The model structurally cannot receive cross-department data or unauthorized report types.</p>
            </div>
            <div className="feat-card" style={{ borderTop: '3px solid #009bd4' }}>
              <div className="fico">📦</div>
              <h3>Layer 2 · Fact Assembly</h3>
              <p>Pure SQL extraction into typed canonical fact packs. Labels every fact as <code>TENANT_SCOPED</code>, <code>ESTATE_WIDE</code>, or <code>DERIVED</code>. No free-text citizen data enters the prompt.</p>
            </div>
            <div className="feat-card" style={{ borderTop: '3px solid #a78bfa' }}>
              <div className="fico">🧠</div>
              <h3>Layer 3 · AIMI Provider (Only AI Layer)</h3>
              <p>External campaign attribution (AVP-3) and risk-delta causal explanation (AVP-8). Receives public CVE/MITRE IDs only. No DB handle, no query tools, no citizen data.</p>
            </div>
            <div className="feat-card" style={{ borderTop: '3px solid #00af66' }}>
              <div className="fico">✅</div>
              <h3>Layer 4 · Deterministic Verification</h3>
              <p>100% numeral fidelity check against the fact pack. Evaluates output against the <strong>14-role claim class matrix</strong>. Strips unauthorized claims. Requires human sign-off before publication.</p>
              <button
                onClick={() => setAiMatrixOpen(true)}
                style={{ marginTop: '12px', background: 'rgba(167,139,250,0.15)', border: '1px solid rgba(167,139,250,0.4)', color: '#a78bfa', borderRadius: '8px', padding: '7px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', width: '100%' }}
              >
                🎯 View 14-Role Claim Matrix
              </button>
            </div>
          </div>
          <div style={{ marginTop: '20px', padding: '14px 20px', background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '10px', fontSize: '13px', color: 'var(--mid)', lineHeight: 1.65 }}>
            <strong style={{ color: 'var(--hi)' }}>Zero Raw Logs to AI (POPIA NFR-AI-11):</strong> South African citizen IDs, employee logins, source IPs, and raw SQL query strings are structurally blocked from egress by <code>redaction.py</code>. If the AIMI provider is offline, a circuit breaker automatically serves the authoritative deterministic report — zero downtime.
            <span style={{ marginLeft: '16px' }}>
              <a href="/architecture.html" target="_blank" rel="noopener noreferrer" style={{ color: '#a78bfa', fontWeight: 600 }}>View full AI architecture ↗</a>
            </span>
          </div>
        </div>
      </section>

      <section className="matrix-section" id="matrix">
        <div className="container">
          <div className="section-head" style={{ maxWidth: '820px' }}>
            <div className="eyebrow"><span className="dot"></span>14-Role RBAC · grounded in auth.py</div>
            <h2>Every role sees a different slice of the same truth</h2>
            <p>Click any row to demo that role's live dashboard. Sourced directly from <code>backend/app/api/auth.py</code> — not a marketing chart.</p>
          </div>
          <div className="matrix-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Role</th>
                  <th style={{ textAlign: 'left' }}>Tenant scope</th>
                  {MATRIX_COLUMNS.map((col) => (
                    <th key={col.key}>{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* ── National Strategic ── */}
                <tr className="matrix-tier-header t4">
                  <td colSpan={7}>🏛️ &nbsp;National Strategic &amp; Assurance Roles (3)</td>
                </tr>
                {MATRIX_ROWS.filter(r => ['exec','compliance','sre'].includes(r.loginRole ?? '')).map((row) => (
                  <tr
                    key={row.tag}
                    className="matrix-row"
                    onClick={() => row.loginRole && loginAsRole(row.loginRole)}
                    title={`Click to preview ${row.role} dashboard`}
                  >
                    <td className="rolecell">{row.role}<span>{row.tag}</span></td>
                    <td className="matrix-scope">{row.scope}</td>
                    {MATRIX_COLUMNS.map((col) => (
                      <td key={col.key}><span className={row[col.key] ? 'dot-on' : 'dot-off'} title={`${col.label}: ${row[col.key] ? 'Cleared' : 'Restricted'}`}></span></td>
                    ))}
                  </tr>
                ))}
                {/* ── Specialized Security Operations ── */}
                <tr className="matrix-tier-header t3">
                  <td colSpan={7}>🛡️ &nbsp;Specialized Security Operations Roles (4)</td>
                </tr>
                {MATRIX_ROWS.filter(r => ['soc','appsec','dbsec','local-appsec'].includes(r.loginRole ?? '')).map((row) => (
                  <tr
                    key={row.tag}
                    className="matrix-row"
                    onClick={() => row.loginRole && loginAsRole(row.loginRole)}
                    title={`Click to preview ${row.role} dashboard`}
                  >
                    <td className="rolecell">{row.role}<span>{row.tag}</span></td>
                    <td className="matrix-scope">{row.scope}</td>
                    {MATRIX_COLUMNS.map((col) => (
                      <td key={col.key}><span className={row[col.key] ? 'dot-on' : 'dot-off'} title={`${col.label}: ${row[col.key] ? 'Cleared' : 'Restricted'}`}></span></td>
                    ))}
                  </tr>
                ))}
                {/* ── Provincial ── */}
                <tr className="matrix-tier-header t2">
                  <td colSpan={7}>📍 &nbsp;Provincial Cybersecurity Roles (2)</td>
                </tr>
                {MATRIX_ROWS.filter(r => ['province-soc-lead','province-dept-admin'].includes(r.loginRole ?? '')).map((row) => (
                  <tr
                    key={row.tag}
                    className="matrix-row"
                    onClick={() => row.loginRole && loginAsRole(row.loginRole)}
                    title={`Click to preview ${row.role} dashboard`}
                  >
                    <td className="rolecell">{row.role}<span>{row.tag}</span></td>
                    <td className="matrix-scope">{row.scope}</td>
                    {MATRIX_COLUMNS.map((col) => (
                      <td key={col.key}><span className={row[col.key] ? 'dot-on' : 'dot-off'} title={`${col.label}: ${row[col.key] ? 'Cleared' : 'Restricted'}`}></span></td>
                    ))}
                  </tr>
                ))}
                {/* ── Administrative ── */}
                <tr className="matrix-tier-header t1">
                  <td colSpan={7}>⚙️ &nbsp;Administrative Tiers (5) · delegated one-way down the tenancy tree</td>
                </tr>
                {MATRIX_ROWS.filter(r => ['branch-admin','dept-admin','transversal-admin','admin','operator'].includes(r.loginRole ?? '')).map((row) => (
                  <tr
                    key={row.tag}
                    className="matrix-row"
                    onClick={() => row.loginRole && loginAsRole(row.loginRole)}
                    title={`Click to preview ${row.role} dashboard`}
                  >
                    <td className="rolecell">{row.role}<span>{row.tag}</span></td>
                    <td className="matrix-scope">{row.scope}</td>
                    {MATRIX_COLUMNS.map((col) => (
                      <td key={col.key}><span className={row[col.key] ? 'dot-on' : 'dot-off'} title={`${col.label}: ${row[col.key] ? 'Cleared' : 'Restricted'}`}></span></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="matrix-note">
            14 platform roles · 4 functional groups · 5 administrative tiers. <strong style={{ color: 'var(--hi)' }}>Click any row</strong> to demo that role's live dashboard. <code>admin</code> and <code>operator</code> see every column. All others see exactly and only their row — enforced at the API, database query (<code>tenant_filter()</code>), and AI layers simultaneously.
            <button onClick={() => setAiMatrixOpen(true)} style={{ marginLeft: '14px', background: 'rgba(167,139,250,0.12)', border: '1px solid rgba(167,139,250,0.35)', color: '#a78bfa', borderRadius: '6px', padding: '4px 12px', fontSize: '11.5px', fontWeight: 700, cursor: 'pointer' }}>🎯 View AI Claim Class Matrix →</button>
          </p>
        </div>
      </section>



      <footer>
        <div className="container">
          <span>© 2026 SITA · Security</span>
          <span className="status"><span className="dot"></span>All systems operational</span>
        </div>
      </footer>

      {modalOpen && <LoginPage onClose={closeModal} />}

      <DemoDirectorModal isOpen={directorOpen} onClose={() => setDirectorOpen(false)} />

      {/* ── 14-Role AI Claim Class Matrix Modal ──────────────────────────── */}
      {aiMatrixOpen && (
        <div
          onClick={(e) => e.target === e.currentTarget && setAiMatrixOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.78)', zIndex: 9000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}
        >
          <div style={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '16px', maxWidth: '1100px', width: '100%', maxHeight: '88vh', overflowY: 'auto', padding: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#a78bfa', marginBottom: '6px' }}>Layer 4 · Deterministic Verification Gate</div>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 800, lineHeight: 1.15 }}>🎯 The 14-Role AI Claim Class Matrix</h2>
                <p style={{ color: 'var(--mid)', fontSize: '0.9rem', marginTop: '8px', maxWidth: '700px' }}>The AI Layer 4 verifier evaluates every generated sentence against this matrix. If a caller's role does not hold that claim class, the sentence is discarded before the report reaches a human. This is enforced deterministically — not by the model.</p>
              </div>
              <button onClick={() => setAiMatrixOpen(false)} style={{ background: 'var(--panel-2)', border: '1px solid var(--line)', borderRadius: '8px', color: 'var(--hi)', fontSize: '18px', cursor: 'pointer', padding: '6px 12px', flexShrink: 0 }}>✕</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px', marginBottom: '24px' }}>
              {[
                { group: '🏛️ Tier 5 & 4 · SITA Command Center', color: '#ef4444', roles: [
                  { role: 'operator', tier: 'Tier 5', label: 'Platform MSP Operator', scope: 'Platform Provider Root', desc: 'Bootstrap operator — creates SITA superuser and peer operator accounts only. Zero application data access.' },
                  { role: 'admin', tier: 'Tier 4', label: 'SITA Platform Superadmin', scope: 'National Estate Root', desc: 'Full estate authority — provisions transversal & departmental tiers, manages national deployments across ~173 organs of state.' },
                ]},
                { group: '🌐 Tier 3 · National Security Estate', color: '#1082ff', roles: [
                  { role: 'transversal-admin', tier: 'Tier 3', label: 'Transversal Superadmin', scope: 'Cross-Department Scope', desc: 'Cross-department governance across assigned client organs of state; provisions Department Superadmins.' },
                  { role: 'exec', tier: 'Tier 3', label: 'Executive / DG / CISO', scope: 'National Whole Estate', desc: 'Strategic risk posture, risk scores, compliance summary, alert overview, findings summary (sinks & CVEs scrubbed).' },
                  { role: 'compliance', tier: 'Tier 3', label: 'Compliance & AGSA Liaison', scope: 'National Whole Estate', desc: 'POPIA s.22 breach analysis, ISO 27001 control gaps, MIOS scores, AGSA ECDSA NIST P-256 PKI signatures.' },
                  { role: 'sre', tier: 'Tier 3', label: 'Site Reliability Engineer', scope: 'National Whole Estate', desc: 'Platform uptime, API connector health, token-bucket rate limits, dead-letter queue status.' },
                ]},
                { group: '🏢 Tier 2 · Department & Provincial', color: '#009bd4', roles: [
                  { role: 'dept-admin', tier: 'Tier 2', label: 'Department Superadmin', scope: 'Department Scope (e.g. DHA)', desc: 'Department control plane, connector config, user provisioning for assigned department & branches.' },
                  { role: 'province-dept-admin', tier: 'Tier 2', label: 'Provincial Dept Admin', scope: 'Provincial Scope (e.g. GP)', desc: 'Provincial department administration & localized user provisioning (no security intelligence reports).' },
                  { role: 'province-soc-lead', tier: 'Tier 2', label: 'Provincial SOC Lead', scope: 'Provincial Scope', desc: 'Provincial posture monitoring, anonymized national peer benchmark (no peer PII or raw findings).' },
                ]},
                { group: '📍 Tier 1 · Operational Branch Tier', color: '#00af66', roles: [
                  { role: 'branch-admin', tier: 'Tier 1', label: 'Branch Superadmin', scope: 'Branch Subtree (DDG Unit)', desc: 'Branch admin panel, user provisioning, strictly subtree-locked (e.g. dha-digital only).' },
                  { role: 'local-appsec', tier: 'Tier 1', label: 'Branch AppSec Specialist', scope: 'Branch Scope', desc: 'Branch-scoped vulnerability posture, CWE traces, localized remediation diffs.' },
                  { role: 'soc', tier: 'Tier 1', label: 'SOC Security Analyst', scope: 'Branch / Dept Scope', desc: 'DAM alert clusters, MITRE ATT&CK technique tags (T1190), intrusion timestamps, D3FEND countermeasures.' },
                  { role: 'appsec', tier: 'Tier 1', label: 'AppSec Engineer', scope: 'Branch / Dept Scope', desc: 'OWASP Top 10, CWE sink traces, AppScan SAST/DAST telemetry, CVE IDs, remediation diffs.' },
                  { role: 'dbsec', tier: 'Tier 1', label: 'Database Security Specialist', scope: 'Branch / Dept Scope', desc: 'SQL injection clusters, Cassandra/PostgreSQL DAM alerts, POPIA breach window estimates.' },
                ]},
              ].map(({ group, color, roles }) => (
                <div key={group} style={{ background: 'var(--panel-2)', border: `1px solid ${color}33`, borderTop: `3px solid ${color}`, borderRadius: '12px', padding: '16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>{group}</div>
                  {roles.map(r => (
                    <div key={r.role} style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid var(--line)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', marginBottom: '2px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--hi)' }}>
                          <code style={{ color, fontSize: '11px' }}>{r.role}</code> · {r.label}
                        </div>
                        <span style={{ fontSize: '9.5px', fontWeight: 700, padding: '1px 5px', borderRadius: '4px', background: `${color}20`, color, fontFamily: 'JetBrains Mono, monospace', flexShrink: 0 }}>
                          {r.tier}
                        </span>
                      </div>
                      <div style={{ fontSize: '10.5px', color: 'var(--dim)', marginBottom: '2px' }}>
                        <span style={{ color: 'var(--mid)', fontWeight: 600 }}>Scope:</span> {r.scope}
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--mid)', lineHeight: 1.45 }}>{r.desc}</div>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div style={{ background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.25)', borderRadius: '10px', padding: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>AI Claim Classes Verified by Layer 4</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--mid)', fontWeight: 600 }}>Claim Class</th>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--mid)', fontWeight: 600 }}>Description</th>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--mid)', fontWeight: 600 }}>Allowed Roles</th>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--mid)', fontWeight: 600 }}>Blocked Roles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { cls: 'headline_metrics', desc: 'Overall risk numbers (e.g. 78.4/100)', allowed: 'All 14 roles', blocked: 'None' },
                      { cls: 'risk_buckets', desc: 'Safe / Monitored / Critical distribution', allowed: 'All 14 roles', blocked: 'None' },
                      { cls: 'app_names', desc: 'Which specific government systems are named', allowed: 'exec, soc, appsec, admin', blocked: 'compliance (sees counts only)' },
                      { cls: 'cve_ids / cwe_ids', desc: 'Technical flaw IDs (e.g. CVE-2024-21413)', allowed: 'appsec, soc, local-appsec, dbsec', blocked: 'exec, compliance (masked)' },
                      { cls: 'raw_evidence', desc: 'Code sinks, query strings, stack traces', allowed: 'appsec, dbsec', blocked: 'exec, compliance, branch-admin' },
                      { cls: 'popia_conditions', desc: 's.22 breach windows & privacy penalties', allowed: 'compliance, exec, admin', blocked: 'appsec, soc' },
                      { cls: 'remediation_steps', desc: 'Actionable fix diffs and D3FEND rules', allowed: 'appsec, dbsec, soc', blocked: 'exec, compliance' },
                    ].map(row => (
                      <tr key={row.cls} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '7px 10px' }}><code style={{ color: '#a78bfa', fontSize: '11px' }}>{row.cls}</code></td>
                        <td style={{ padding: '7px 10px', color: 'var(--mid)' }}>{row.desc}</td>
                        <td style={{ padding: '7px 10px', color: '#00af66', fontSize: '11px' }}>{row.allowed}</td>
                        <td style={{ padding: '7px 10px', color: '#ef4444', fontSize: '11px' }}>{row.blocked}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--mid)', fontStyle: 'italic' }}>
                💡 "Even if the AI model tries to get overly technical in an Executive summary, Layer 4 checks the caller's specific role and automatically scrubs low-level CVE or code-sink claims before the document is ever displayed."
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}