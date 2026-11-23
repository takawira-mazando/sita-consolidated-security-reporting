import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import type { DemoAccount } from '../types';
import { useDemoMode } from '../context/DemoContext';
import PlatformBrand from '../components/layout/PlatformBrand';

interface LoginPageProps {
  onClose?: () => void;
}

interface RolePlaneMeta {
  plane: 'control' | 'data';
  tierBadge: string;
  shortLabel: string;
  scopeBadge: string;
  desc: string;
  targetPath: string;
  cockpitLabel: string;
}

const ROLE_PLANE_MAP: Record<string, RolePlaneMeta> = {
  // ── Administration & Governance ──────────────────────────────────────────
  'operator': {
    plane: 'control',
    tierBadge: 'Root Operator',
    shortLabel: 'Platform Creator (Root)',
    scopeBadge: 'Platform Provider Root',
    desc: 'Platform provider access for creating client organization profiles and managing their lifecycle.',
    targetPath: '/sita/admin',
    cockpitLabel: 'Client profile administration',
  },
  'admin': {
    plane: 'control',
    tierBadge: 'Superadmin',
    shortLabel: 'Client MSSP Superadmin',
    scopeBadge: 'Client workspace',
    desc: 'Client administrator. Configures tenant structures, custom roles, and scoped dashboard assignments for this organization.',
    targetPath: '/national/admin',
    cockpitLabel: 'Tenant administration · Custom structure & dashboard access',
  },
  // ── Security Intelligence & Operations Dashboards ───────────────────────────
  'exec': {
    plane: 'data',
    tierBadge: 'Executive Posture',
    shortLabel: 'Executive CISO / Risk Lead',
    scopeBadge: 'Estate-wide Consolidated Posture',
    desc: 'Executive Dashboard: Strategic threat posture, blended risk scores (CVSS × Exposure × Blast Radius), Application Risk Heatmap, and CISO intelligence.',
    targetPath: '/national/exec',
    cockpitLabel: 'Executive Threat Posture & Blended Risk Dashboard',
  },
  'compliance': {
    plane: 'data',
    tierBadge: 'Assurance Officer',
    shortLabel: 'Compliance & Audit Officer',
    scopeBadge: 'Regulatory Assurance Scope',
    desc: 'Compliance Dashboard: Statutory assurance, POPIA s.22 / GDPR 72h breach window telemetry, ISO 27001 audit readiness, and privacy audit logs.',
    targetPath: '/national/compliance',
    cockpitLabel: 'Statutory Compliance & Regulatory Assurance Dashboard',
  },
  'sre': {
    plane: 'data',
    tierBadge: 'Service Ops Lead',
    shortLabel: 'Service Operations Lead (SRE)',
    scopeBadge: 'Telemetry Pipeline Observability',
    desc: 'Service Ops Dashboard: Universal log ingestion rates (EPS), connector telemetry, dead-letter queues, rate limits, and platform reliability metrics.',
    targetPath: '/sre',
    cockpitLabel: 'Service Reliability & Telemetry Pipeline Dashboard',
  },
};

function getRoleMeta(account: DemoAccount): RolePlaneMeta {
  if (ROLE_PLANE_MAP[account.role]) {
    const meta = ROLE_PLANE_MAP[account.role];
    if (account.role === 'admin') {
      return { ...meta, shortLabel: 'Client MSSP Superadmin' };
    }
    return meta;
  }
  const role = account.role.toLowerCase();
  const isCtrl =
    role.includes('admin') ||
    role.includes('operator');

  return {
    plane: isCtrl ? 'control' : 'data',
    tierBadge: isCtrl ? 'Admin' : 'Dashboard',
    shortLabel: account.label.replace(' (Home Affairs)', '').replace('SITA ', 'Tenant '),
    scopeBadge: isCtrl ? 'Administration Scope' : 'Operations Scope',
    desc: isCtrl
      ? 'Tenant platform administration and IAM provisioning.'
      : 'Role-scoped access to the client dashboards and data assigned to this account.',
    targetPath: isCtrl ? '/national/admin' : '/national/soc',
    cockpitLabel: isCtrl ? 'Administration · Multi-Tenant Node & IAM Provisioning' : 'Security Intelligence Dashboard',
  };
}

export default function LoginPage({ onClose }: LoginPageProps) {
  const navigate = useNavigate();
  const { demoMode } = useDemoMode();
  const showLocalDemos = demoMode
    && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const { login, loginDemo, demoAccounts, refreshDemoAccounts } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [demoAccountsLoading, setDemoAccountsLoading] = useState(showLocalDemos);
  const [demoAccountsError, setDemoAccountsError] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [planeFilter, setPlaneFilter] = useState<'all' | 'control' | 'data'>('all');
  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');

  const loadDemoAccounts = useCallback(async (isActive: () => boolean = () => true) => {
    setDemoAccountsLoading(true);
    setDemoAccountsError('');
    try {
      const accounts = await refreshDemoAccounts();
      if (isActive()) {
        setDemoAccountsError('');
      }
    } catch (error) {
      console.error('Failed to load local demo accounts', error);
      if (isActive()) {
        setDemoAccountsError('Local demo accounts could not be loaded. Confirm the backend is running, then retry.');
      }
    } finally {
      if (isActive()) setDemoAccountsLoading(false);
    }
  }, [refreshDemoAccounts]);

  useEffect(() => {
    if (!showLocalDemos) return;
    let active = true;
    void loadDemoAccounts(() => active);
    return () => {
      active = false;
    };
  }, [showLocalDemos, loadDemoAccounts]);

  const toggleTheme = () => {
    const next = isDark ? 'light' : 'dark';
    document.body.dataset.theme = next;
    localStorage.setItem('platform_theme', next);
    setIsDark(!isDark);
  };

  const selectedAccount: DemoAccount | null =
    showLocalDemos ? demoAccounts.find((a) => a.role === selectedRole) ?? null : null;

  const selectedMeta: RolePlaneMeta | null =
    selectedAccount ? getRoleMeta(selectedAccount) : null;

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
      if (selectedAccount && !selectedAccount.password) {
        result = await loginDemo(selectedAccount.role);
      } else {
        result = await login(email, password);
      }
      if (result.ok) {
        closeOverlay();
        const target = selectedMeta?.targetPath ?? '/';
        navigate(target);
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
    setPassword(account.password ?? '');
    setError('');
  };

  // Keep the development-only role shortcuts separate from client sign-in.
  const canonicalAccounts = (showLocalDemos ? demoAccounts : []).filter((a) => {
    if (['soc', 'appsec', 'dbsec', 'dept-admin', 'branch-admin'].includes(a.role)) {
      return false;
    }
    return true;
  });

  // Group local demo shortcuts by access type.
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
          <button type="button" className="login-theme-toggle" onClick={toggleTheme}>
            {isDark ? '☀ Light' : '🌙 Dark'}
          </button>
          <div className="login-logo-mark">
            <PlatformBrand className="platform-brand-login" />
          </div>
        </div>

        <form className="login-body" onSubmit={handleLogin}>
          <div className="form-field">
            <label className="form-label" htmlFor="loginEmail">Client email address</label>
            <input
              type="email"
              className="form-input"
              id="loginEmail"
              placeholder="you@organization.example"
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

          {showLocalDemos && (demoAccountsLoading || Boolean(demoAccountsError) || canonicalAccounts.length > 0) && (
            <details className="login-demo-access">
              <summary>
                <span>Local demo accounts</span>
                <span className="login-demo-count">
                  {demoAccountsLoading ? 'Loading…' : demoAccountsError ? 'Unavailable' : `${canonicalAccounts.length} available`}
                </span>
              </summary>
              <div className="login-hint">
                {demoAccountsLoading && <div role="status">Loading local demo accounts…</div>}
                {demoAccountsError && (
                  <div role="alert">
                    {demoAccountsError}{' '}
                    <button type="button" onClick={() => void loadDemoAccounts()}>Retry</button>
                  </div>
                )}
                <div hidden={demoAccountsLoading || Boolean(demoAccountsError) || canonicalAccounts.length === 0}>
                  <div className="login-demo-intro">
                    {selectedAccount?.password
                      ? 'Email and password filled in above. Click sign in to continue.'
                      : 'Click an account to fill the sign-in fields. For normal access, use your client credentials above.'}
                  </div>

                  <div className="plane-toggle-bar">
                  <button
                    id="planeToggleAll"
                    type="button"
                    className={`plane-toggle-btn${planeFilter === 'all' ? ' active' : ''}`}
                    onClick={() => setPlaneFilter('all')}
                  >
                    All demo accounts ({canonicalAccounts.length})
                  </button>
                  <button
                    id="planeToggleControl"
                    type="button"
                    className={`plane-toggle-btn control${planeFilter === 'control' ? ' active' : ''}`}
                    onClick={() => setPlaneFilter('control')}
                  >
                    Platform &amp; client admins ({controlAccounts.length})
                  </button>
                  <button
                    id="planeToggleData"
                    type="button"
                    className={`plane-toggle-btn data${planeFilter === 'data' ? ' active' : ''}`}
                    onClick={() => setPlaneFilter('data')}
                  >
                    Client users ({dataAccounts.length})
                  </button>
                  </div>

                  {(planeFilter === 'all' || planeFilter === 'control') && (
                  <div className="plane-card-section control-plane">
                    <div className="plane-section-header">
                      <div className="plane-section-title control">
                        <span>⚙️</span> Platform &amp; client administration
                      </div>
                      <span className="plane-section-badge control">
                        Provider and client administrator previews
                      </span>
                    </div>
                    <div className="plane-section-rule">
                      The platform operator manages client profiles. Each client administrator manages their own organization’s tenant structure and access.
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
                            aria-pressed={isSelected}
                            title={`${account.label} — ${meta.desc}`}
                            onClick={() => selectPersona(account)}
                          >
                            <span className="chip-tier-tag">{meta.tierBadge}</span>
                            <span className="chip-email-tag">{account.email}</span>
                            <span className="chip-label-tag">· {meta.shortLabel}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  )}

                  {(planeFilter === 'all' || planeFilter === 'data') && (
                  <div className="plane-card-section data-plane">
                    <div className="plane-section-header">
                      <div className="plane-section-title data">
                        <span>🛡️</span> MSSP client users
                      </div>
                      <span className="plane-section-badge data">
                        Sample role-scoped client access
                      </span>
                    </div>
                    <div className="plane-section-rule">
                      Client team members sign in to the workspace and dashboards assigned by their organization’s administrator.
                    </div>

                    <div className="login-demo-subgroup">
                      <div className="login-demo-subgroup-title">Leadership &amp; assurance</div>
                      <div className="plane-chips-container">
                        {nationalDataAccounts.map((account) => {
                          const meta = getRoleMeta(account);
                          const isSelected = selectedRole === account.role;
                          return (
                            <button
                              key={account.role}
                              type="button"
                              className={`plane-chip data${isSelected ? ' selected' : ''}`}
                              aria-pressed={isSelected}
                              title={`${account.label} — ${meta.desc}`}
                              onClick={() => selectPersona(account)}
                            >
                              <span className="chip-tier-tag">{meta.tierBadge}</span>
                              <span className="chip-email-tag">{account.email}</span>
                              <span className="chip-label-tag">· {meta.shortLabel}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="login-demo-subgroup">
                      <div className="login-demo-subgroup-title">Client dashboard users</div>
                      <div className="plane-chips-container">
                        {operationalDataAccounts.map((account) => {
                          const meta = getRoleMeta(account);
                          const isSelected = selectedRole === account.role;
                          return (
                            <button
                              key={account.role}
                              type="button"
                              className={`plane-chip data${isSelected ? ' selected' : ''}`}
                              aria-pressed={isSelected}
                              title={`${account.label} — ${meta.desc}`}
                              onClick={() => selectPersona(account)}
                            >
                              <span className="chip-tier-tag">{meta.tierBadge}</span>
                              <span className="chip-email-tag">{account.email}</span>
                              <span className="chip-label-tag">· {meta.shortLabel}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  )}

                  {selectedAccount && selectedMeta && (
                  <div className={`login-plane-active-callout ${selectedMeta.plane}`}>
                    <div className="login-plane-active-callout-header">
                      <span className={`login-plane-active-callout-title ${selectedMeta.plane}`}>
                        <span>{selectedAccount.role === 'operator' ? '⚙️' : '🛡️'}</span>
                        {selectedAccount.role === 'operator' ? 'Platform administrator selected' : 'Client account selected'} · {selectedMeta.tierBadge}
                      </span>
                      <span className="login-demo-selected-email">{selectedAccount.email}</span>
                    </div>
                    <div className="login-demo-selected-description">{selectedMeta.desc}</div>
                    <div className="login-demo-selected-destination">
                      <span>Destination</span>
                      <span>{selectedMeta.cockpitLabel}</span>
                    </div>
                  </div>
                  )}

                  {selectedAccount && selectedAccount.role === 'operator' && (
                  <div className="login-demo-scope">
                    Platform administration for managing client organization profiles.
                  </div>
                  )}
                </div>
              </div>
            </details>
          )}

          {error && <div className="login-error" id="loginError">{error}</div>}

          <button
            type="submit"
            className={`login-btn${selectedMeta
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
                ? `Open ${selectedAccount.role === 'operator' ? 'platform admin' : 'client'} demo`
                : 'Sign in'}
          </button>

          <div style={{
            marginTop: '14px',
            paddingTop: '10px',
            borderTop: '1px solid var(--border-dim)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--text-muted)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                aria-hidden="true"
                style={{
                  width: 16,
                  height: 16,
                  display: 'grid',
                  placeItems: 'center',
                  border: '1px solid var(--sita-copper)',
                  borderRadius: 4,
                  color: 'var(--sita-copper)',
                  fontSize: 10,
                  fontWeight: 700,
                }}
              >
                H
              </span>
              <span>Engineered by <strong>HOSI Technologies</strong></span>
            </div>
            <span style={{ fontFamily: 'var(--mono)', color: '#D67D4A', fontWeight: 600 }}>
              HOSI Brand OS
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
