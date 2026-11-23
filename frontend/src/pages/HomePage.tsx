import React, { useEffect, useMemo, useState } from 'react';
import LoginPage from './LoginPage';
import { useDemoMode } from '../context/DemoContext';
import '../styles/home.css';

const SCORE_SOURCES = [
  { name: 'HCL AppScan', detail: 'AppSec · SAST/DAST' },
  { name: 'Imperva DAM', detail: 'Database activity' },
  { name: 'Imperva WAF', detail: 'Web application firewall' },
  { name: 'API Security', detail: 'Shadow API discovery' },
  { name: 'POPIA', detail: 'Compliance control data' },
  { name: 'ISO 27001', detail: 'Compliance control data' },
];

const COCKPIT_ACCESS_PROFILES = [
  {
    category: 'Threat Detection & Incident Response',
    categoryClass: 't2',
    roles: [
      {
        role: 'SOC & Threat Analyst',
        tag: 'threat-ops',
        scope: 'Assigned tenant node & incident telemetry stream',
        ldap: 'CN=Threat-Ops,OU=SecOps',
        alerts: true, vulns: true, logs: false, compliance: false, infra: false,
      },
      {
        role: 'Network & Perimeter Security',
        tag: 'perimeter-sec',
        scope: 'Firewall, WAF & ingress network feeds',
        ldap: 'CN=Perimeter-Sec,OU=SecOps',
        alerts: true, vulns: false, logs: false, compliance: false, infra: false,
      },
    ],
  },
  {
    category: 'Application & Datastore Security',
    categoryClass: 't3',
    roles: [
      {
        role: 'Application Security Engineer',
        tag: 'appsec',
        scope: 'Assigned application repos & SAST/DAST targets',
        ldap: 'CN=AppSec-Team,OU=DevSecOps',
        alerts: false, vulns: true, logs: false, compliance: false, infra: false,
      },
      {
        role: 'Database & Datastore Activity (DAM)',
        tag: 'datastore-sec',
        scope: 'Assigned databases & privileged query audit stream',
        ldap: 'CN=Database-Audit,OU=Datastores',
        alerts: true, vulns: true, logs: true, compliance: false, infra: false,
      },
    ],
  },
  {
    category: 'Governance, Compliance & Executive Posture',
    categoryClass: 't4',
    roles: [
      {
        role: 'Executive Posture & Risk Lead',
        tag: 'exec-oversight',
        scope: 'Estate-wide risk score, exposure & trend summaries',
        ldap: 'CN=Executive-Governance,OU=Leadership',
        alerts: true, vulns: true, logs: false, compliance: true, infra: false,
      },
      {
        role: 'Compliance & Regulatory Auditor',
        tag: 'compliance-audit',
        scope: 'Statutory compliance standing (POPIA / GDPR / ISO 27001)',
        ldap: 'CN=Compliance-Audit,OU=Governance',
        alerts: false, vulns: false, logs: false, compliance: true, infra: false,
      },
      {
        role: 'Service Operations Lead (SRE)',
        tag: 'service-ops',
        scope: 'Telemetry ingestion pipelines & platform health observability',
        ldap: 'CN=Service-Ops,OU=Engineering',
        alerts: true, vulns: false, logs: false, compliance: false, infra: true,
      },
    ],
  },
  {
    category: 'Delegated Tenant Administration',
    categoryClass: 't1',
    roles: [
      {
        role: 'Delegated Tenant Administrator',
        tag: 'tenant-admin',
        scope: 'Assigned tenant node subtree (user & directory governance)',
        ldap: 'CN=Tenant-Admins,OU=Administration',
        alerts: false, vulns: false, logs: false, compliance: false, infra: false,
      },
      {
        role: 'Central Platform Superadministrator',
        tag: 'platform-superadmin',
        scope: 'Central Command Center administration & tenant tree architecture',
        ldap: 'CN=Platform-CommandCenter,OU=Superadmins',
        alerts: false, vulns: false, logs: false, compliance: false, infra: true,
      },
    ],
  },
];

export default function HomePage() {
  const { demoMode } = useDemoMode();
  const [modalOpen, setModalOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');
  const [activeSection, setActiveSection] = useState<string>('');

  const navSections = useMemo<{ id: string; label: string }[]>(() => [
    { id: 'capabilities', label: 'Outcomes' },
    { id: 'adapters', label: 'Universal Ingestion' },
    { id: 'ai-layer', label: 'AI Threat Intelligence' },
  ], []);

  const toggleTheme = () => {
    const next = isDark ? 'light' : 'dark';
    document.body.dataset.theme = next;
    localStorage.setItem('platform_theme', next);
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
      for (const { id } of navSections) {
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
  }, [navSections]);

  const openModal = () => {
    setModalOpen(true);
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setModalOpen(false);
    document.body.style.overflow = '';
  };

  return (
    <div className="home-page">
      <header className="site">
        <div className="container">
          <a href="#" className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <div className="brand-text">
              <span className="brand-title">Unified Data Security Platform</span>
            </div>
          </a>
          <nav className="primary" aria-label="Section navigation">
            {navSections.map(({ id, label }) => (
              <a
                key={id}
                href={`#${id}`}
                className={activeSection === id ? 'is-active' : undefined}
                aria-current={activeSection === id ? 'true' : undefined}
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="home-actions">
            <button className="theme-toggle" onClick={toggleTheme}>
              {isDark ? '☀️ Light' : '🌙 Dark'}
            </button>
            <button className="btn btn-outline" onClick={openModal}>Sign In</button>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="container hero-grid">
          <div>
            <h1>One unified security picture across the entire enterprise estate.<br /><span className="gradient-text">Intelligence that drives action.</span></h1>
            <p className="lede">
              The <strong>Unified Data Security Platform</strong> is a multi-tenant cybersecurity command center that unifies application security, database activity monitoring, perimeter threat defense, universal log ingestion, and regulatory compliance across any organizational structure. Explainable AI connects evidence across telemetry streams, clarifies exposure, and prioritizes remediation—empowering leadership with comprehensive estate governance and operational teams with role-scoped security dashboards.
            </p>
            <div style={{ display: 'flex', gap: '12px', marginTop: '28px', flexWrap: 'wrap' }}>
              <a
                href="#adapters"
                className="btn btn-outline"
                style={{
                  padding: '12px 20px',
                  fontSize: '14px',
                  fontWeight: 600,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>📡</span> Universal Log Ingestion ↓
              </a>

            </div>
          </div>
        </div>
      </section>

      <section className="problem-section" id="capabilities">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Operational outcomes</div>
            <h2>Turn fragmented security data into coordinated action.</h2>
          </div>
          <div className="problem-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
            <div className="problem-card" style={{ borderTop: '3px solid #1082ff' }}>
              <div className="problem-n">See risk in context</div>
              <p>Connect application findings, network and database exposure, API risk, and compliance gaps. Understand how issues relate across the assets that matter.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #009bd4' }}>
              <div className="problem-n">Focus effort where it counts</div>
              <p>Use a transparent, explainable risk view to identify the applications and assets that need investigation or remediation first.</p>
            </div>
            <div className="problem-card" style={{ borderTop: '3px solid #a78bfa' }}>
              <div className="problem-n">Close the loop</div>
              <p>Route high-priority alerts with ownership context, record acknowledgement and resolution, and give leaders a clear view of outstanding exposure.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Default scoring sources and broad ingestion support */}
      <section className="preview-section" id="adapters" style={{ borderTop: '1px solid var(--line)', background: 'rgba(16, 130, 255, 0.02)' }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot" style={{ background: '#009bd4' }} />Sources Feeding Score</div>
            <h2>Default sources behind the unified risk view.</h2>
            <p>
              These are the default sources feeding the score. The platform architecture is designed to ingest and normalize logs and data from a wide range of other sources across your environment; this list is not a limit.
            </p>
          </div>

          <ul className="score-sources-grid" aria-label="Default sources feeding the score">
            {SCORE_SOURCES.map((source) => (
              <li key={source.name} className="score-source-card">
                <strong className="score-source-name">{source.name}</strong>
                <span className="score-source-detail">{source.detail}</span>
              </li>
            ))}
          </ul>

          <div className="isolation-guarantee-banner" style={{ marginTop: '24px' }}>
            <span className="isolation-icon">⚖️</span>
            <div className="isolation-text">
              <strong>Dynamic Multi-Signal Risk Fusion:</strong> Signals are normalized and correlated to produce role-scoped risk scores and dashboard insights.
            </div>
          </div>
        </div>
      </section>


      {/* Universal Multi-Tier RBAC & Scope Partitioning Section — Rendered strictly during Live Demo Mode */}
      {demoMode && (
        <section className="matrix-section" id="matrix">
          <div className="container" style={{ width: '99%', maxWidth: '99%', padding: '0 0.5%', margin: '0 auto' }}>
            <div className="section-head section-head-fullwidth" style={{ maxWidth: 'none', width: '100%' }}>
              <div className="eyebrow"><span className="dot" />Live Demonstration · Insight-Driven Security Dashboards &amp; Operational Access</div>
              <h2 style={{ maxWidth: 'none', width: '100%' }}>Role-Appropriate Security Dashboards. Tailored to Each Tenant.</h2>
              <p style={{ maxWidth: 'none', width: '100%' }}>
                The platform dynamically provisions tenant hierarchies and assigns operational roles based strictly on required telemetry insights and governance responsibilities—routing users directly to dedicated dashboards across the 6 purpose-built Security Dashboards (Executive, SOC Analyst, AppSec Engineer, DbSec Specialist, Compliance, and Service Ops / SRE) with fail-closed data boundaries enforced cryptographically at their assigned scope.
              </p>
            </div>

            <div className="matrix-wrap">
              <table className="matrix">
                <thead>
                  <tr>
                    <th colSpan={3} style={{ textAlign: 'left', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--line)' }}>
                      Identity &amp; Tenant Provisioning
                    </th>
                    <th colSpan={5} style={{ textAlign: 'center', background: 'rgba(16, 130, 255, 0.08)', color: 'var(--flare-1)', borderBottom: '1px solid var(--line)' }}>
                      Security Dashboard Telemetry Access
                    </th>
                  </tr>
                  <tr>
                    <th style={{ textAlign: 'left', minWidth: '220px' }}>Operational Role &amp; Insight Profile</th>
                    <th style={{ textAlign: 'left', minWidth: '220px' }}>Provisioned Scope Boundary</th>
                    <th style={{ textAlign: 'left', minWidth: '180px' }}>Tenant Directory / LDAP Mapping</th>
                    <th title="Alerts Dashboard: Real-time threat detection & incident triage">Alerts Dashboard</th>
                    <th title="Vulnerabilities Dashboard: SAST/DAST findings &amp; patch prioritization">Vulns Dashboard</th>
                    <th title="Access Logs Dashboard: Privileged datastore query audit & logs">Access Logs Dashboard</th>
                    <th title="Compliance Dashboard: Regulatory framework & POPIA/GDPR assurance">Compliance Dashboard</th>
                    <th title="Platform Health Dashboard: Telemetry pipelines & connector health">Health Dashboard</th>
                  </tr>
                </thead>
                <tbody>
                  {COCKPIT_ACCESS_PROFILES.map((group) => (
                    <React.Fragment key={group.category}>
                      <tr className={`matrix-tier-header ${group.categoryClass || ''}`}>
                        <td colSpan={8}>{group.category}</td>
                      </tr>
                      {group.roles.map((r) => (
                        <tr key={r.tag} className="matrix-row">
                          <td className="rolecell">
                            {r.role} <span>{r.tag}</span>
                          </td>
                          <td className="matrix-scope">{r.scope}</td>
                          <td style={{ textAlign: 'left' }}>
                            <span className="brole-ldap" style={{ fontSize: '11px' }}>{r.ldap}</span>
                          </td>
                          <td><span className={r.alerts ? 'dot-on' : 'dot-off'} /></td>
                          <td><span className={r.vulns ? 'dot-on' : 'dot-off'} /></td>
                          <td><span className={r.logs ? 'dot-on' : 'dot-off'} /></td>
                          <td><span className={r.compliance ? 'dot-on' : 'dot-off'} /></td>
                          <td><span className={r.infra ? 'dot-on' : 'dot-off'} /></td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="usecase-grid-cards">
              {/* Card 01: 6 Purpose-Built Security Dashboards */}
              <div className="ai-graphic-card">
                <div className="ai-card-bg-wrap">
                  <div className="ai-card-bg-img" aria-hidden="true" />
                  <div className="ai-card-scrim"></div>
                </div>
                <div className="ai-card-inscription">
                  <span className="ai-card-inscription-tag">
                    <span className="ai-card-inscription-pulse" style={{ background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }}></span>
                    ROUTING · 6_SECURITY_COCKPITS
                  </span>
                  <span className="ai-card-inscription-id">DASHBOARD-01</span>
                </div>
                <div className="ai-card-body">
                  <div>
                    <div className="ai-card-top-meta">
                      <span className="ai-card-num">🎯 01</span>
                      <span className="ai-card-phase">Role-Bounded Dashboards</span>
                    </div>
                    <h3 className="ai-card-title">6 Purpose-Built Security Dashboards</h3>
                    <p className="ai-card-desc">
                      Every operational persona is routed directly to their designated Security Dashboard—Executive, SOC Analyst, AppSec Engineer, DbSec Specialist, Compliance, or Service Ops (SRE)—strictly bounded to their assigned scope.
                    </p>
                  </div>
                  <div className="ai-card-telemetry">
                    <span className="ai-card-chip">Executive</span>
                    <span className="ai-card-chip">SOC Analyst</span>
                    <span className="ai-card-chip">AppSec</span>
                    <span className="ai-card-chip">DbSec</span>
                    <span className="ai-card-chip">Compliance</span>
                    <span className="ai-card-chip">SRE</span>
                  </div>
                </div>
              </div>

              {/* Card 02: Zero-Code Directory Sync */}
              <div className="ai-graphic-card">
                <div className="ai-card-bg-wrap">
                  <div className="ai-card-bg-img" aria-hidden="true" />
                  <div className="ai-card-scrim"></div>
                </div>
                <div className="ai-card-inscription">
                  <span className="ai-card-inscription-tag">
                    <span className="ai-card-inscription-pulse" style={{ background: '#34d399', boxShadow: '0 0 8px #34d399' }}></span>
                    FEDERATION · ZERO_CODE_IAM
                  </span>
                  <span className="ai-card-inscription-id">DIR-02</span>
                </div>
                <div className="ai-card-body">
                  <div>
                    <div className="ai-card-top-meta">
                      <span className="ai-card-num">📁 02</span>
                      <span className="ai-card-phase">Enterprise IAM Alignment</span>
                    </div>
                    <h3 className="ai-card-title">Zero-Code Directory Sync</h3>
                    <p className="ai-card-desc">
                      Any role provisioned binds directly to the tenant's existing enterprise directory groups (Active Directory, Azure AD / Entra ID, OpenLDAP, or Okta).
                    </p>
                  </div>
                  <div className="ai-card-telemetry">
                    <span className="ai-card-chip">Azure AD / Entra</span>
                    <span className="ai-card-chip">Active Directory</span>
                    <span className="ai-card-chip">OpenLDAP</span>
                    <span className="ai-card-chip">Okta SSO</span>
                  </div>
                </div>
              </div>

              {/* Card 03: Dynamic Scope Partitioning */}
              <div className="ai-graphic-card">
                <div className="ai-card-bg-wrap">
                  <div className="ai-card-bg-img" aria-hidden="true" />
                  <div className="ai-card-scrim"></div>
                </div>
                <div className="ai-card-inscription">
                  <span className="ai-card-inscription-tag">
                    <span className="ai-card-inscription-pulse" style={{ background: '#ED9A5E', boxShadow: '0 0 8px #ED9A5E' }}></span>
                    TOPOLOGY · DYNAMIC_SCOPING
                  </span>
                  <span className="ai-card-inscription-id">SCOPE-03</span>
                </div>
                <div className="ai-card-body">
                  <div>
                    <div className="ai-card-top-meta">
                      <span className="ai-card-num">🎛️ 03</span>
                      <span className="ai-card-phase">Arbitrary Estate Hierarchy</span>
                    </div>
                    <h3 className="ai-card-title">Dynamic Scope Partitioning</h3>
                    <p className="ai-card-desc">
                      Visibility is bounded strictly by assigned operational scope (estate-wide, division, branch, or datastore)—never granting cross-boundary access.
                    </p>
                  </div>
                  <div className="ai-card-telemetry">
                    <span className="ai-card-chip">Estate Topologies</span>
                    <span className="ai-card-chip">Division Scopes</span>
                    <span className="ai-card-chip">Datastores</span>
                    <span className="ai-card-chip">Anti-Elevation</span>
                  </div>
                </div>
              </div>

              {/* Card 04: Zero Cross-Tenant Leakage */}
              <div className="ai-graphic-card">
                <div className="ai-card-bg-wrap">
                  <div className="ai-card-bg-img" aria-hidden="true" />
                  <div className="ai-card-scrim"></div>
                </div>
                <div className="ai-card-inscription">
                  <span className="ai-card-inscription-tag">
                    <span className="ai-card-inscription-pulse" style={{ background: '#a78bfa', boxShadow: '0 0 8px #a78bfa' }}></span>
                    ISOLATION · FAIL_CLOSED_SQL
                  </span>
                  <span className="ai-card-inscription-id">ISOL-04</span>
                </div>
                <div className="ai-card-body">
                  <div>
                    <div className="ai-card-top-meta">
                      <span className="ai-card-num">🔒 04</span>
                      <span className="ai-card-phase">Deterministic Boundaries</span>
                    </div>
                    <h3 className="ai-card-title">Zero Cross-Tenant Leakage</h3>
                    <p className="ai-card-desc">
                      All roles and queries compile to deterministic SQL isolation filters (WHERE tenant_id IN (...)) verified cryptographically via JWT claims.
                    </p>
                  </div>
                  <div className="ai-card-telemetry">
                    <span className="ai-card-chip">WHERE tenant_id</span>
                    <span className="ai-card-chip">Fail-Closed SQL</span>
                    <span className="ai-card-chip">JWT Claims</span>
                    <span className="ai-card-chip">84 Test Classes</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="matrix-footer-row" style={{ marginTop: '20px' }}>
              <p className="matrix-note">
                <strong>Insight-Driven Operational Roles:</strong> Roles are defined by the insights and security dashboards they provide access to, not by rigid hierarchical templates. The Command Center defines the tenant structure dynamically and binds roles to any scope node—granting exact security dashboard visibility without rigid assumptions.
              </p>
              <div className="matrix-customize-badge">
                <span className="customize-icon">⚡</span>
                <span>Zero Cross-Tenant Leakage — Tested against 84 automated isolation test classes.</span>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="features" id="ai-layer" style={{ borderTop: '1px solid var(--line)' }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot" style={{ background: '#a78bfa' }}></span>Cognitive Cyber Defense · AI Value Proposition</div>
            <h2>Accelerate Detection, Investigation &amp; Remediation with Purpose-Built AI.</h2>
            <p>Security teams lose critical hours stitching together logs, verifying alerts, and drafting reports. The AI engine correlates cross-domain signals in real time—delivering immediate threat attribution, automated executive narratives, and risk-ranked remediation playbooks backed by 100% deterministic numeral grounding.</p>
          </div>
          <div className="ai-graphic-grid">
            {/* Tile 01: Automated Threat Attribution */}
            <div className="ai-graphic-card">
              <div className="ai-card-bg-wrap">
                <div className="ai-card-bg-img" aria-hidden="true" />
                <div className="ai-card-scrim"></div>
              </div>
              <div className="ai-card-inscription">
                <span className="ai-card-inscription-tag">
                  <span className="ai-card-inscription-pulse"></span>
                  ATTRIBUTION · MITRE_ATT&amp;CK
                </span>
                <span className="ai-card-inscription-id">ENG-01</span>
              </div>
              <div className="ai-card-body">
                <div>
                  <div className="ai-card-top-meta">
                    <span className="ai-card-num">01</span>
                    <span className="ai-card-phase">Cross-Domain Kill-Chain</span>
                  </div>
                  <h3 className="ai-card-title">Automated Threat Attribution</h3>
                  <p className="ai-card-desc">
                    Correlates isolated WAF anomalies, AppScan vulnerabilities, and database query spikes across the attack kill-chain. Identifies campaign tactics, affected assets, and blast radius in seconds.
                  </p>
                </div>
                <div className="ai-card-telemetry">
                  <span className="ai-card-chip">WAF Ingress</span>
                  <span className="ai-card-chip">AppScan SAST/DAST</span>
                  <span className="ai-card-chip">DAM Anomalies</span>
                  <span className="ai-card-chip">MITRE TTPs</span>
                </div>
              </div>
            </div>

            {/* Tile 02: Instant Executive & Technical Briefings */}
            <div className="ai-graphic-card">
              <div className="ai-card-bg-wrap">
                <div className="ai-card-bg-img" aria-hidden="true" />
                <div className="ai-card-scrim"></div>
              </div>
              <div className="ai-card-inscription">
                <span className="ai-card-inscription-tag">
                  <span className="ai-card-inscription-pulse" style={{ background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }}></span>
                  SYNTHESIS · MULTI_PERSONA
                </span>
                <span className="ai-card-inscription-id">DOS-02</span>
              </div>
              <div className="ai-card-body">
                <div>
                  <div className="ai-card-top-meta">
                    <span className="ai-card-num">02</span>
                    <span className="ai-card-phase">Role-Dedicated Dashboards</span>
                  </div>
                  <h3 className="ai-card-title">Instant Executive &amp; Technical Briefings</h3>
                  <p className="ai-card-desc">
                    Transforms millions of telemetry events into clear, role-specific intelligence dossiers for CISOs, compliance auditors, and engineers—eliminating manual reporting overhead.
                  </p>
                </div>
                <div className="ai-card-telemetry">
                  <span className="ai-card-chip">CISO Briefings</span>
                  <span className="ai-card-chip">Audit Timelines</span>
                  <span className="ai-card-chip">POPIA Standing</span>
                  <span className="ai-card-chip">Zero Overhead</span>
                </div>
              </div>
            </div>

            {/* Tile 03: Risk-Prioritized Remediation */}
            <div className="ai-graphic-card">
              <div className="ai-card-bg-wrap">
                <div className="ai-card-bg-img" aria-hidden="true" />
                <div className="ai-card-scrim"></div>
              </div>
              <div className="ai-card-inscription">
                <span className="ai-card-inscription-tag">
                  <span className="ai-card-inscription-pulse" style={{ background: '#ED9A5E', boxShadow: '0 0 8px #ED9A5E' }}></span>
                  ROADMAP · SLA_RANKED
                </span>
                <span className="ai-card-inscription-id">OPT-03</span>
              </div>
              <div className="ai-card-body">
                <div>
                  <div className="ai-card-top-meta">
                    <span className="ai-card-num">03</span>
                    <span className="ai-card-phase">Exploit-Aware Scoring</span>
                  </div>
                  <h3 className="ai-card-title">Risk-Prioritized Remediation</h3>
                  <p className="ai-card-desc">
                    Replaces overwhelming vulnerability lists with actionable, exploit-aware patch plans ranked by business impact, helping teams resolve high-exposure flaws first.
                  </p>
                </div>
                <div className="ai-card-telemetry">
                  <span className="ai-card-chip">CVSS × Exposure</span>
                  <span className="ai-card-chip">Threat Feeds</span>
                  <span className="ai-card-chip">SLA Enforcer</span>
                  <span className="ai-card-chip">Actionable Fixes</span>
                </div>
              </div>
            </div>

            {/* Tile 04: Hallucination-Free Fact Verification */}
            <div className="ai-graphic-card">
              <div className="ai-card-bg-wrap">
                <div className="ai-card-bg-img" aria-hidden="true" />
                <div className="ai-card-scrim"></div>
              </div>
              <div className="ai-card-inscription">
                <span className="ai-card-inscription-tag">
                  <span className="ai-card-inscription-pulse" style={{ background: '#a78bfa', boxShadow: '0 0 8px #a78bfa' }}></span>
                  GOVERNANCE · DETERMINISTIC
                </span>
                <span className="ai-card-inscription-id">VER-04</span>
              </div>
              <div className="ai-card-body">
                <div>
                  <div className="ai-card-top-meta">
                    <span className="ai-card-num">04</span>
                    <span className="ai-card-phase">PII Redaction &amp; Fidelity</span>
                  </div>
                  <h3 className="ai-card-title">Hallucination-Free Fact Verification</h3>
                  <p className="ai-card-desc">
                    Powered by deterministic numeral fidelity gates and automated PII redaction. Produces verified, audit-ready security intelligence without leaking sensitive data or hallucinating metrics.
                  </p>
                </div>
                <div className="ai-card-telemetry">
                  <span className="ai-card-chip">Numeral Gates</span>
                  <span className="ai-card-chip">PII Masking</span>
                  <span className="ai-card-chip">Fail-Closed Boundary</span>
                  <span className="ai-card-chip">Audit-Proof</span>
                </div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: '20px', color: 'var(--dim)', fontSize: '13px' }}>
            <a href="/architecture.html" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--link)', fontWeight: 600 }}>Explore the technical architecture</a>
          </div>
        </div>
      </section>

      <footer className="platform-footer">
        <div className="container">
          {/* Top Branding & Partner Lockup */}
          <div className="footer-top-brand">
            <div className="footer-brand-left">
              <div className="footer-logo-wrap" aria-hidden="true">
                <span className="footer-hosi-mark">H</span>
              </div>
              <div className="footer-brand-divider" />
              <div className="footer-brand-text">
                <div className="footer-brand-name">HOSI Technologies</div>
                <div className="footer-brand-tagline">Trusted Data. Confident Decisions.</div>
              </div>
            </div>

            <div className="footer-partner-badge">
              <div className="partner-chip">
                <span>🛡️ Multi-Tenant Cyber Command Center</span>
              </div>
            </div>
          </div>

          {/* Quick Links & Platform References */}
          <div className="footer-nav-row">
            <div className="footer-nav-links">
              <a href="/architecture.html" target="_blank" rel="noopener noreferrer">Technical Architecture ↗</a>
              <span className="footer-sep">•</span>
              <a href="/platform_showcase.html" target="_blank" rel="noopener noreferrer">Unified Platform Showcase &amp; Deck ↗</a>
            </div>

            <div className="footer-integrations-compact">
              <span className="int-chip">SAST / DAST Ingestion</span>
              <span className="int-chip">DAM &amp; Query Audit</span>
              <span className="int-chip">Multi-Tenant LDAP</span>
              <span className="int-chip">Universal Ingestion</span>
              <span className="int-chip">POPIA / GDPR</span>
              <span className="int-chip">ISO 27001</span>
            </div>
          </div>

          {/* Bottom Legal & Attribution Strip */}
          <div className="footer-bottom-bar">
            <div className="footer-copy">
              <span>© 2026 <strong>HOSI Technologies (Pty) Ltd</strong>. All rights reserved.</span>
              <span className="footer-bullet">•</span>
              <span>Unified Data Security Platform</span>
            </div>
            <div className="footer-status-pill">
              <span className="status-indicator live" />
              <span>Platform Online · All Systems Operational</span>
            </div>
          </div>
        </div>
      </footer>

      {modalOpen && <LoginPage onClose={closeModal} />}
    </div>
  );
}
