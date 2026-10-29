import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import type { TenancyTier } from '../../types';

interface DemoDirectorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DemoDirectorModal({ isOpen, onClose }: DemoDirectorModalProps) {
  const { user, loginDemo, switchTenant } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'control' | 'data' | 'guardrails'>('control');
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!isOpen) return null;

  const showFeedback = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 4000);
  };

  const executeControlPlane = async (
    role: string,
    tier: TenancyTier,
    targetPath: string,
    label: string,
    scope?: { department_id: string; branch_id?: string }
  ) => {
    showFeedback(`⚡ Executing Control Plane switch to ${label}…`);
    const s = scope ? { department_id: scope.department_id, branch_id: scope.branch_id || null, province_id: null } : undefined;
    const res = await loginDemo(role, s);
    if (res.ok) {
      navigate(targetPath);
      onClose();
    } else {
      showFeedback(`❌ Failed to switch: ${res.error}`);
    }
  };

  const executeDataPlane = async (
    role: string,
    targetPath: string,
    label: string,
    scope?: { department_id: string; branch_id?: string }
  ) => {
    showFeedback(`⚡ Launching ${label} with live telemetry…`);
    const s = scope ? { department_id: scope.department_id, branch_id: scope.branch_id || null, province_id: null } : undefined;
    const res = await loginDemo(role, s);
    if (res.ok) {
      navigate(targetPath);
      onClose();
    } else {
      showFeedback(`❌ Failed to launch: ${res.error}`);
    }
  };

  const simulateScope = async (tier: TenancyTier) => {
    if (tier === 'sita' || tier === 'national') {
      await switchTenant({ department_id: null, branch_id: null });
      showFeedback(`🌍 Scoped to Transversal Sovereign Estate (Whole of Government)`);
    } else if (tier === 'dept') {
      await switchTenant({ department_id: 'home-affairs-digital', branch_id: null });
      showFeedback(`🏢 Scoped to Department of Home Affairs (Tier 2 Tenant)`);
    } else if (tier === 'branch') {
      await switchTenant({ department_id: 'home-affairs-digital', branch_id: 'dha-civic' });
      showFeedback(`📍 Scoped to DHA Civic Services (Tier 1 Branch)`);
    }
  };

  return (
    <div
      className="login-overlay as-modal"
      style={{ zIndex: 9999, backdropFilter: 'blur(10px)', animation: 'fadeIn .2s ease' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="login-card"
        style={{
          maxWidth: 820,
          width: '95%',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '24px 28px',
          borderRadius: 20,
          border: '1px solid var(--accent)',
          boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 24 }}>🎬</span>
              <h2 style={{ margin: 0, fontSize: 20, fontFamily: 'Space Grotesk, sans-serif' }}>
                Live Demonstration Director &amp; Flow Execution
              </h2>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
              1-click live execution controller for SITA stakeholder demonstrations. Instantly switches personas, validates guardrails, and renders telemetry cockpits.
            </p>
          </div>
          <button
            type="button"
            className="overlay-close"
            onClick={onClose}
            aria-label="Close"
            style={{ fontSize: 22, cursor: 'pointer' }}
          >
            &times;
          </button>
        </div>

        {feedback && (
          <div
            style={{
              background: 'var(--card-bg, #1e293b)',
              border: '1px solid var(--accent)',
              padding: '8px 14px',
              borderRadius: 10,
              fontSize: 13,
              color: 'var(--accent)',
              marginBottom: 16,
              fontWeight: 600,
            }}
          >
            {feedback}
          </div>
        )}

        {/* Tab Controls */}
        <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--border)', paddingBottom: 10, marginBottom: 18 }}>
          <button
            type="button"
            className={`btn ${activeTab === 'control' ? 'btn-flare' : 'btn-outline'}`}
            style={{ fontSize: 12.5, padding: '6px 14px' }}
            onClick={() => setActiveTab('control')}
          >
            🏛️ Control Plane (Tiers 1–5 Provisioning)
          </button>
          <button
            type="button"
            className={`btn ${activeTab === 'data' ? 'btn-flare' : 'btn-outline'}`}
            style={{ fontSize: 12.5, padding: '6px 14px' }}
            onClick={() => setActiveTab('data')}
          >
            📊 Data Plane (6 Security Cockpits)
          </button>
          <button
            type="button"
            className={`btn ${activeTab === 'guardrails' ? 'btn-flare' : 'btn-outline'}`}
            style={{ fontSize: 12.5, padding: '6px 14px' }}
            onClick={() => setActiveTab('guardrails')}
          >
            🛡️ Live Guardrails &amp; Air-Gap Proofs
          </button>
        </div>

        {/* ── TAB 1: CONTROL PLANE ── */}
        {activeTab === 'control' && (
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
              <b>Authority flows strictly downward:</b> Platform Developer → SITA Command Center Superadmin (Tier 4) → National Estate Superadmin (Tier 3) → DHA Department Superadmin (Tier 2) → DHA Branch Admin (Tier 1). Administrative accounts hold <b>zero live telemetry views</b>.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {/* Tier 4 */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--amber)', fontFamily: 'JetBrains Mono, monospace' }}>TIER 4 · SITA COMMAND CENTER</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>admin@</span>
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>SITA Superadmin #1 (Transversal ICT Provider)</h4>
                <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Mandated transversal provider. Provisions National Gov Superadmin (#2) and national data plane cockpits across ~173 departments.
                </p>
                <button
                  type="button"
                  className="btn btn-flare"
                  style={{ width: '100%', fontSize: 12, padding: '7px 12px' }}
                  onClick={() => executeControlPlane('admin', 'sita', '/sita/admin', 'SITA Superadmin #1')}
                >
                  ⚡ Execute SITA Superadmin Console (/sita/admin)
                </button>
              </div>

              {/* Tier 3 */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', fontFamily: 'JetBrains Mono, monospace' }}>TIER 3 · NATIONAL ESTATE</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>transversal@</span>
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>National Gov Transversal Superadmin #2</h4>
                <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Sovereign governance across organs of state. Provisions Department Superadmins (DHA, SAPS, DOH, Treasury).
                </p>
                <button
                  type="button"
                  className="btn btn-flare"
                  style={{ width: '100%', fontSize: 12, padding: '7px 12px' }}
                  onClick={() => executeControlPlane('transversal-admin', 'national', '/national/admin', 'National Gov Superadmin #2')}
                >
                  ⚡ Execute National Estate Console (/national/admin)
                </button>
              </div>

              {/* Tier 2 */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--green)', fontFamily: 'JetBrains Mono, monospace' }}>TIER 2 · DEPARTMENT</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>deptadmin-ha@</span>
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>Department Superadmin (Home Affairs)</h4>
                <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Jailed to DHA tenancy. Provisions DHA Branch Admins and operational security specialists (SOC, AppSec, DBSec).
                </p>
                <button
                  type="button"
                  className="btn btn-flare"
                  style={{ width: '100%', fontSize: 12, padding: '7px 12px' }}
                  onClick={() => executeControlPlane('deptadmin-ha', 'dept', '/dept/admin', 'DHA Department Superadmin', { department_id: 'home-affairs-digital' })}
                >
                  ⚡ Execute DHA Dept Console (/dept/admin)
                </button>
              </div>

              {/* Tier 1 */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--cyan, #06b6d4)', fontFamily: 'JetBrains Mono, monospace' }}>TIER 1 · BRANCH</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>branchadmin-ha@</span>
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>Branch Admin (DHA Civic Services)</h4>
                <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Jailed to DDG Civic Services. Provisions branch-level AppSec engineers and local SOC analysts.
                </p>
                <button
                  type="button"
                  className="btn btn-flare"
                  style={{ width: '100%', fontSize: 12, padding: '7px 12px' }}
                  onClick={() => executeControlPlane('branchadmin-ha', 'branch', '/branch/admin', 'DHA Branch Admin', { department_id: 'home-affairs-digital', branch_id: 'dha-civic' })}
                >
                  ⚡ Execute DHA Branch Console (/branch/admin)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: DATA PLANE COCKPITS ── */}
        {activeTab === 'data' && (
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
              <b>Telemetry flows strictly into role-tailored cockpits:</b> Multi-OEM normalization across HCL AppScan, Imperva WAF, Imperva &amp; Thales DAM, and SIEM connectors. Cockpits hold <b>zero user provisioning authority</b>.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
              {/* Exec */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid var(--red)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--red)', fontFamily: 'JetBrains Mono' }}>EXEC COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>Executive &amp; CISO</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>Multi-OEM risk fusion &amp; AGSA readiness</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('exec', '/national/exec', 'Executive Cockpit')}
                >
                  ⚡ Launch Exec (/national/exec)
                </button>
              </div>

              {/* SOC */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid var(--blue)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', fontFamily: 'JetBrains Mono' }}>SOC COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>SOC Security Analyst</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>Imperva WAF, DDoS &amp; live SIEM triage</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('soc-ha', '/dept/soc', 'SOC Cockpit', { department_id: 'home-affairs-digital' })}
                >
                  ⚡ Launch SOC (/dept/soc)
                </button>
              </div>

              {/* AppSec */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid var(--amber)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--amber)', fontFamily: 'JetBrains Mono' }}>APPSEC COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>AppSec Engineer</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>HCL AppScan DAST/SAST &amp; OWASP Top 10</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('appsec-ha', '/dept/appsec', 'AppSec Cockpit', { department_id: 'home-affairs-digital' })}
                >
                  ⚡ Launch AppSec (/dept/appsec)
                </button>
              </div>

              {/* DbSec */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid var(--green)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--green)', fontFamily: 'JetBrains Mono' }}>DBSEC COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>DB Security Specialist</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>Imperva &amp; Thales DAM, privileged query audit</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('dbsec-ha', '/dept/dbsec', 'DbSec Cockpit', { department_id: 'home-affairs-digital' })}
                >
                  ⚡ Launch DbSec (/dept/dbsec)
                </button>
              </div>

              {/* Compliance */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid var(--violet)', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--violet)', fontFamily: 'JetBrains Mono' }}>COMPLIANCE COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>Compliance &amp; AGSA Officer</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>POPIA Chapter 3, ISO 27001 &amp; AGSA packs</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('compliance', '/national/compliance', 'Compliance Cockpit')}
                >
                  ⚡ Launch Compliance (/national/compliance)
                </button>
              </div>

              {/* SRE */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderTop: '3px solid #0d9488', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#0d9488', fontFamily: 'JetBrains Mono' }}>SRE COCKPIT</div>
                <h5 style={{ margin: '4px 0', fontSize: 13 }}>Service Reliability Engineer</h5>
                <p style={{ margin: '0 0 8px', fontSize: 11, color: 'var(--text-muted)' }}>42.8k EPS pipeline health &amp; 99.95% SLA</p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                  onClick={() => executeDataPlane('sre', '/national/sre', 'SRE Cockpit')}
                >
                  ⚡ Launch SRE (/national/sre)
                </button>
              </div>
            </div>

            {/* Tenancy Horizon Switcher */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                Simulate Tenancy Horizon (Watch live dashboard subtitles adapt):
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-outline" style={{ fontSize: 12, padding: '5px 10px' }} onClick={() => simulateScope('sita')}>
                  🇿🇦 Tier 4: SITA Command Center
                </button>
                <button type="button" className="btn btn-outline" style={{ fontSize: 12, padding: '5px 10px' }} onClick={() => simulateScope('national')}>
                  🏛 Tier 3: National Security Estate
                </button>
                <button type="button" className="btn btn-outline" style={{ fontSize: 12, padding: '5px 10px' }} onClick={() => simulateScope('dept')}>
                  🏢 Tier 2: Department (Home Affairs)
                </button>
                <button type="button" className="btn btn-outline" style={{ fontSize: 12, padding: '5px 10px' }} onClick={() => simulateScope('branch')}>
                  📍 Tier 1: Branch (Civic Services)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 3: GUARDRAILS & AIR-GAP PROOF ── */}
        {activeTab === 'guardrails' && (
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
              Demonstrate the platform's statutory compliance safeguards live to auditors and evaluators:
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>🛡️ 1. Air-Gap of Telemetry</h4>
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Log in as SITA Superadmin or Department Superadmin. Observe that the navigation bar contains <b>ONLY</b> the Admin provisioning tab. Administrative roles are cryptographically barred from viewing raw telemetry or CVE findings.
                </p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 12, padding: '6px 12px' }}
                  onClick={() => executeControlPlane('admin', 'sita', '/sita/admin', 'SITA Superadmin (Air-Gap Test)')}
                >
                  ⚡ Verify Admin Has Zero Telemetry Tabs
                </button>
              </div>

              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>🔒 2. Tenancy Isolation &amp; Jailing</h4>
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Log in as DHA Department Admin. Notice the tenant scope badge is permanently locked to DHA with 🔒. Cross-tenant queries are blocked at the backend with 403 Forbidden.
                </p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 12, padding: '6px 12px' }}
                  onClick={() => executeControlPlane('deptadmin-ha', 'dept', '/dept/admin', 'DHA Dept Superadmin (Jailing Test)', { department_id: 'home-affairs-digital' })}
                >
                  ⚡ Verify DHA Tenancy Lock
                </button>
              </div>

              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>🆔 3. SITA SAP HCM &amp; PERSAL Verification</h4>
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Every new user created in the Control Plane must pass live authoritative identity check against SITA SAP HCM (for SITA employees) or National Treasury PERSAL (for public servants).
                </p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 12, padding: '6px 12px' }}
                  onClick={() => {
                    executeControlPlane('deptadmin-ha', 'dept', '/dept/admin', 'DHA Admin (HR Lookup Demo)', { department_id: 'home-affairs-digital' });
                  }}
                >
                  ⚡ Open User Provisioner to Test PERSAL Lookup
                </button>
              </div>

              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
                <h4 style={{ margin: '0 0 6px', fontSize: 14 }}>🚫 4. Non-Escalation Enforcement</h4>
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  A Department Superadmin (Tier 2) attempting to provision a SITA Superadmin (Tier 4) or National Estate Superadmin (Tier 3) is rejected by client-side filters and backend cryptographic checks.
                </p>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: 12, padding: '6px 12px' }}
                  onClick={() => {
                    executeControlPlane('deptadmin-ha', 'dept', '/dept/admin', 'DHA Admin (Non-Escalation Test)', { department_id: 'home-affairs-digital' });
                  }}
                >
                  ⚡ Test Tier 2 Admin Non-Escalation
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Signed in as: <b style={{ color: 'var(--text)' }}>{user?.email || 'Unauthenticated'}</b>
          </span>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              type="button"
              className="btn btn-outline"
              style={{ fontSize: 12, padding: '6px 12px' }}
              onClick={() => window.open('/presentation.html', '_blank')}
            >
              📑 Open Pitch Deck
            </button>
            <button
              type="button"
              className="btn btn-flare"
              style={{ fontSize: 12, padding: '6px 12px' }}
              onClick={onClose}
            >
              Done / Return to Platform
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
