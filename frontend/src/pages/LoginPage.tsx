import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { LoginScope } from '../api/auth';
import type { DemoAccount } from '../types';

interface LoginPageProps {
  onClose?: () => void;
}

// DHA branches — static list matching backend BRANCHES for the pre-login
// persona selector.
const DHA_BRANCHES: { id: string; name: string }[] = [
  { id: 'dha-civic',       name: 'Civic Services' },
  { id: 'dha-digital',     name: 'Information Services (CIO)' },
  { id: 'dha-immigration', name: 'Immigration Services' },
  { id: 'dha-operations',  name: 'Operations' },
  { id: 'dha-hrmd',        name: 'Human Resource Management and Development' },
  { id: 'dha-ccss',        name: 'Counter Corruption and Security Services' },
  { id: 'dha-finance',     name: 'Finance and Supply Chain Management' },
  { id: 'dha-planning',    name: 'Institutional Planning and Support' },
];

interface RolePlaneMeta {
  plane: 'control' | 'data';
  tierBadge: string;
  shortLabel: string;
  scopeBadge: string;
  desc: string;
}

const ROLE_PLANE_MAP: Record<string, RolePlaneMeta> = {
  // ── Control Plane (Administrative & Provisioning Tiers 5 → 1) ─────────────
  'operator': {
    plane: 'control',
    tierBadge: 'Tier 5',
    shortLabel: 'Platform Creator (Root)',
    scopeBadge: 'Platform Provider Root',
    desc: 'Platform MSP root credentials. Provisions SITA Command Center superuser & peer operators only. Zero live telemetry views.',
  },
  'admin': {
    plane: 'control',
    tierBadge: 'Tier 4',
    shortLabel: 'SITA Platform Superadmin',
    scopeBadge: 'National Command Center',
    desc: 'Estate root administrator. Provisions transversal & departmental tiers across ~173 organs of state. Zero raw telemetry views.',
  },
  'transversal-admin': {
    plane: 'control',
    tierBadge: 'Tier 3',
    shortLabel: 'Transversal Superadmin',
    scopeBadge: 'Assigned Organs of State',
    desc: 'Cross-department governance spanning assigned client departments; provisions Department Superadmins. Administrative control plane only.',
  },
  'deptadmin-ha': {
    plane: 'control',
    tierBadge: 'Tier 2',
    shortLabel: 'DHA Dept Superadmin',
    scopeBadge: 'Department Scope (Home Affairs)',
    desc: 'Home Affairs department control plane. Configures connectors & provisions Branch Admins and operational analysts for DHA.',
  },
  'branchadmin-ha': {
    plane: 'control',
    tierBadge: 'Tier 1',
    shortLabel: 'DHA Branch Admin',
    scopeBadge: 'Branch Subtree (DDG Unit)',
    desc: 'Subtree-locked branch administrator. Provisions operational specialists strictly within its DDG branch (e.g. dha-digital).',
  },

  // ── Data Plane (Security Intelligence & Telemetry Cockpits) ───────────────
  'exec': {
    plane: 'data',
    tierBadge: 'Tier 3',
    shortLabel: 'Executive / National CISO',
    scopeBadge: 'Republic-wide Consolidated',
    desc: 'Executive cockpit. Strategic threat posture, blended risk scores, and AGSA compliance. Low-level CVEs and sinks scrubbed by Layer 4.',
  },
  'compliance': {
    plane: 'data',
    tierBadge: 'Tier 3',
    shortLabel: 'Compliance Officer / AGSA',
    scopeBadge: 'National Assurance Scope',
    desc: 'POPIA s.22 breach window telemetry, ISO 27001 control gaps, and ECDSA NIST P-256 PKI digital signing. App names masked to counts.',
  },
  'sre': {
    plane: 'data',
    tierBadge: 'Tier 3',
    shortLabel: 'Service Reliability Engineer',
    scopeBadge: 'Estate-wide Telemetry',
    desc: 'Platform uptime, connector health, rate-limiting tokens, dead-letter queue operations, and circuit-breaker telemetry.',
  },
  'soc-ha': {
    plane: 'data',
    tierBadge: 'Tier 1',
    shortLabel: 'SOC Security Analyst',
    scopeBadge: 'DHA Operational Scope',
    desc: 'Real-time telemetry, Imperva DAM/WAF alert clusters, MITRE ATT&CK technique tags (T1190), and D3FEND countermeasures.',
  },
  'appsec-ha': {
    plane: 'data',
    tierBadge: 'Tier 1',
    shortLabel: 'AppSec Engineer',
    scopeBadge: 'DHA Operational Scope',
    desc: 'OWASP Top 10 vulnerabilities, CWE traces, AppScan SAST/DAST telemetry, CVE identifiers, and actionable patch diffs.',
  },
  'dbsec-ha': {
    plane: 'data',
    tierBadge: 'Tier 1',
    shortLabel: 'Database Security Specialist',
    scopeBadge: 'DHA Operational Scope',
    desc: 'Database Activity Monitoring (DAM), SQL injection clusters, Cassandra/PostgreSQL audits, and POPIA data breach window estimates.',
  },
};

function getRoleMeta(account: DemoAccount): RolePlaneMeta {
  if (ROLE_PLANE_MAP[account.role]) return ROLE_PLANE_MAP[account.role];
  const role = account.role.toLowerCase();
  const isCtrl =
    role.includes('admin') ||
    role.includes('operator');

  return {
    plane: isCtrl ? 'control' : 'data',
    tierBadge: isCtrl ? 'Admin' : 'Cockpit',
    shortLabel: account.label.replace(' (Home Affairs)', ''),
    scopeBadge: isCtrl ? 'Control Plane Scope' : 'Data Plane Scope',
    desc: isCtrl
      ? 'Delegated administration & user provisioning down the tenancy tree.'
      : 'Live security telemetry & cockpit. Output claims evaluated by Layer 4 RBAC.',
  };
}

export default function LoginPage({ onClose }: LoginPageProps) {
  const { login, loginDemo, demoAccounts } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [branch, setBranch] = useState<string>('');
  const [planeFilter, setPlaneFilter] = useState<'all' | 'control' | 'data'>('all');

  const selectedAccount: DemoAccount | null =
    demoAccounts.find((a) => a.role === selectedRole) ?? null;

  const selectedMeta: RolePlaneMeta | null =
    selectedAccount ? getRoleMeta(selectedAccount) : null;

  const personaScope = (): LoginScope | undefined => {
    if (branch) return { department_id: 'home-affairs-digital', branch_id: branch, province_id: null };
    return undefined;
  };

  const closeOverlay = () => {
    document.body.style.overflow = '';
    if (onClose) onClose();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let result;
      if (selectedAccount) {
        result = await loginDemo(selectedAccount.role, personaScope());
      } else {
        result = await login(email, password);
      }
      if (result.ok) {
        closeOverlay();
      } else {
        setError(result.error || 'Login failed');
      }
    } catch {
      setError('An unexpected error occurred during sign-in.');
    } finally {
      setLoading(false);
    }
  };

  const selectPersona = (account: DemoAccount) => {
    setSelectedRole(account.role);
    setEmail(account.email);
    setPassword(''); // demo login uses loginDemo() — no password needed client-side
    setBranch('');
    setError('');
  };

  // Filter out redundant alias shims (soc@, appsec@, dbsec@, deptadmin@, branchadmin@)
  // when canonical DHA versions exist, giving exactly 11 authoritative personas.
  const canonicalAccounts = demoAccounts.filter((a) => {
    if (['soc', 'appsec', 'dbsec', 'dept-admin', 'branch-admin'].includes(a.role)) {
      return false;
    }
    return true;
  });

  // Segregate demo accounts into Control Plane vs Data Plane
  const controlAccounts = canonicalAccounts.filter((a) => getRoleMeta(a).plane === 'control');
  const dataAccounts = canonicalAccounts.filter((a) => getRoleMeta(a).plane === 'data');

  const nationalDataAccounts = dataAccounts.filter((a) =>
    ['exec', 'compliance', 'sre'].includes(a.role)
  );
  const operationalDataAccounts = dataAccounts.filter(
    (a) => !['exec', 'compliance', 'sre'].includes(a.role)
  );

  return (
    <div
      className={`login-overlay${onClose ? ' as-modal' : ''}`}
      onClick={(e) => {
        if (onClose && e.target === e.currentTarget) onClose();
      }}
    >
      <div className="login-card">
        {onClose && (
          <button type="button" className="overlay-close" onClick={onClose} aria-label="Close">&times;</button>
        )}
        <div className="login-header">
          <div className="login-logo-mark">
            <img className="login-logo-img" src="/sita-logo.gif" alt="SITA" />
          </div>
          <div className="login-title">Unified Security Intelligence Platform</div>
          <div className="login-sub">Sovereign 14-Role Multi-Tenancy · Sign In to Continue</div>
        </div>

        <form className="login-body" onSubmit={handleLogin}>
          <div className="form-field">
            <label className="form-label" htmlFor="loginEmail">Email address</label>
            <input
              type="email"
              className="form-input"
              id="loginEmail"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setSelectedRole(null);
              }}
              autoComplete="email"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="loginPassword">Password</label>
            <input
              type="password"
              className="form-input"
              id="loginPassword"
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setSelectedRole(null);
              }}
              autoComplete="current-password"
            />
          </div>

          <div className="login-hint" style={{ marginTop: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)' }}>
                🔑 Select Authority Plane &amp; Persona:
              </span>
              <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                One-click authenticated access
              </span>
            </div>

            {/* Plane Switcher Filter */}
            <div className="plane-toggle-bar">
              <button
                id="planeToggleAll"
                type="button"
                className={`plane-toggle-btn${planeFilter === 'all' ? ' active' : ''}`}
                onClick={() => setPlaneFilter('all')}
              >
                All Roles ({canonicalAccounts.length})
              </button>
              <button
                id="planeToggleControl"
                type="button"
                className={`plane-toggle-btn control${planeFilter === 'control' ? ' active' : ''}`}
                onClick={() => setPlaneFilter('control')}
              >
                <span>⚙️</span> Control Plane ({controlAccounts.length})
              </button>
              <button
                id="planeToggleData"
                type="button"
                className={`plane-toggle-btn data${planeFilter === 'data' ? ' active' : ''}`}
                onClick={() => setPlaneFilter('data')}
              >
                <span>🛡️</span> Data Plane ({dataAccounts.length})
              </button>
            </div>

            {/* ── CONTROL PLANE SECTION ───────────────────────────────────── */}
            {(planeFilter === 'all' || planeFilter === 'control') && (
              <div className="plane-card-section control-plane">
                <div className="plane-section-header">
                  <div className="plane-section-title control">
                    <span>⚙️</span> Control Plane · Administrative Tiers
                  </div>
                  <span className="plane-section-badge control">
                    Zero Live Telemetry · Sovereign Provisioning
                  </span>
                </div>
                <div className="plane-section-rule">
                  Delegated authority flows strictly downward (Tier 5 → 1). Manages users and tenancy boundaries.
                </div>
                <div className="plane-chips-container">
                  {controlAccounts.map((account) => {
                    const meta = getRoleMeta(account);
                    const isSelected = selectedRole === account.role;
                    return (
                      <button
                        key={account.role}
                        type="button"
                        className={`plane-chip control${isSelected ? ' selected' : ''}`}
                        title={`${account.label} — ${meta.desc}`}
                        onClick={() => selectPersona(account)}
                      >
                        <span className="chip-tier-tag">{meta.tierBadge}</span>
                        <span className="chip-email-tag">{account.email.split('@')[0]}@</span>
                        <span className="chip-label-tag">· {meta.shortLabel}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── DATA PLANE SECTION ───────────────────────────────────────── */}
            {(planeFilter === 'all' || planeFilter === 'data') && (
              <div className="plane-card-section data-plane">
                <div className="plane-section-header">
                  <div className="plane-section-title data">
                    <span>🛡️</span> Data Plane · Security Cockpits
                  </div>
                  <span className="plane-section-badge data">
                    Live OEM Telemetry · Layer 4 AI Claim-Gated
                  </span>
                </div>
                <div className="plane-section-rule">
                  Real-time security telemetry from AppScan, Imperva DAM/WAF &amp; compliance warehouse.
                </div>

                {/* National Strategic Sub-group */}
                <div style={{ marginBottom: '6px' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    🏛️ National Strategic &amp; Assurance (Tier 3)
                  </div>
                  <div className="plane-chips-container">
                    {nationalDataAccounts.map((account) => {
                      const meta = getRoleMeta(account);
                      const isSelected = selectedRole === account.role;
                      return (
                        <button
                          key={account.role}
                          type="button"
                          className={`plane-chip data${isSelected ? ' selected' : ''}`}
                          title={`${account.label} — ${meta.desc}`}
                          onClick={() => selectPersona(account)}
                        >
                          <span className="chip-tier-tag">{meta.tierBadge}</span>
                          <span className="chip-email-tag">{account.email.split('@')[0]}@</span>
                          <span className="chip-label-tag">· {meta.shortLabel}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Specialized Ops Sub-group */}
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    🔬 Specialized Operational Security · Home Affairs Testbed (Tier 1)
                  </div>
                  <div className="plane-chips-container">
                    {operationalDataAccounts.map((account) => {
                      const meta = getRoleMeta(account);
                      const isSelected = selectedRole === account.role;
                      return (
                        <button
                          key={account.role}
                          type="button"
                          className={`plane-chip data${isSelected ? ' selected' : ''}`}
                          title={`${account.label} — ${meta.desc}`}
                          onClick={() => selectPersona(account)}
                        >
                          <span className="chip-tier-tag">{meta.tierBadge}</span>
                          <span className="chip-email-tag">{account.email.split('@')[0]}@</span>
                          <span className="chip-label-tag">· {meta.shortLabel}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Active Selected Persona Callout Banner */}
            {selectedAccount && selectedMeta && (
              <div className={`login-plane-active-callout ${selectedMeta.plane}`}>
                <div className="login-plane-active-callout-header">
                  <span className={`login-plane-active-callout-title ${selectedMeta.plane}`}>
                    <span>{selectedMeta.plane === 'control' ? '⚙️' : '🛡️'}</span>
                    {selectedMeta.plane === 'control' ? 'Control Plane Active' : 'Data Plane Active'} · {selectedMeta.tierBadge}
                  </span>
                  <span style={{ fontSize: '10.5px', fontFamily: 'var(--mono)', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {selectedAccount.email}
                  </span>
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginTop: '2px' }}>
                  {selectedMeta.desc}
                </div>
              </div>
            )}

            {/* Tenancy Scope Selector (DHA Live Testbed) */}
            {selectedAccount && selectedAccount.department_ids?.includes('home-affairs-digital') && (
              <span className="login-scope" style={{ marginTop: '8px' }}>
                <label className="login-scope-label" htmlFor="loginScopeBranch">
                  🏛️ Tenancy Scope: Department of Home Affairs
                  <em className="login-scope-default">
                    (Live Demo Tenant · 8 Active Branches)
                  </em>
                </label>
                <span className="login-scope-row">
                  <select
                    id="loginScopeBranch"
                    className="form-input"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                  >
                    <option value="">Whole department (All 8 DHA branches)</option>
                    {DHA_BRANCHES.map((b) => (
                      <option key={b.id} value={b.id}>
                        Branch: {b.name}
                      </option>
                    ))}
                  </select>
                </span>
                <span className="login-scope-summary">
                  {selectedMeta?.plane === 'control'
                    ? 'Provisions users and administrators strictly within selected branch boundary'
                    : 'Telemetry and findings scoped strictly to selected branch subtree'}
                </span>
              </span>
            )}

            {selectedAccount && (!selectedAccount.department_ids || selectedAccount.department_ids.length === 0) && (
              <div style={{ marginTop: '6px', fontSize: '0.8rem', color: 'var(--accent)', textAlign: 'center' }}>
                🌐 <strong>Estate-wide Scope</strong> — Republic-wide access across all 173 national and provincial organs of state
              </div>
            )}
          </div>

          {error && <div className="login-error" id="loginError">{error}</div>}

          <button
            type="submit"
            className={`login-btn${
              selectedMeta
                ? selectedMeta.plane === 'control'
                  ? ' login-btn-control'
                  : ' login-btn-data'
                : ''
            }`}
            disabled={loading}
          >
            {loading
              ? '⏳ Signing in…'
              : selectedAccount && selectedMeta
              ? selectedMeta.plane === 'control'
                ? `Sign In to Control Plane · ${selectedMeta.shortLabel} (${selectedAccount.email.split('@')[0]}@)`
                : `Sign In to Data Plane · ${selectedMeta.shortLabel} (${selectedAccount.email.split('@')[0]}@)`
              : 'Sign In to Dashboard'}
          </button>

          <span className="login-demo-line" style={{ textAlign: 'center', display: 'block', marginTop: '10px' }}>
            Multi-tenancy enforced at API, DB, and AI layers simultaneously · Click any persona above
          </span>
        </form>
      </div>
    </div>
  );
}