import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { fetchTenancy, TenancyResponse, LoginScope } from '../api/auth';
import type { DemoAccount } from '../types';

interface LoginPageProps {
  onClose?: () => void;
}

export default function LoginPage({ onClose }: LoginPageProps) {
  const { login, loginDemo, demoAccounts } = useAuth();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tenancy, setTenancy] = useState<TenancyResponse | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [branch, setBranch] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    fetchTenancy()
      .then((t) => {
        if (!cancelled) setTenancy(t);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedAccount: DemoAccount | null =
    demoAccounts.find((a) => a.role === selectedRole) ?? null;

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
    setPassword('demo123');
    setBranch('');
    setError('');
  };

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
          <div className="login-title">Unified Intelligence Platform</div>
          <div className="login-sub">Consolidated RBAC security reporting — sign in to continue</div>
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

          <div className="login-hint">
            <strong style={{ color: 'var(--text-secondary)' }}>🏛️ Department of Home Affairs Demo Personas:</strong>
            <div className="login-demo-chips" style={{ justifyContent: 'center', marginTop: '6px' }}>
              {demoAccounts.map((account) => (
                <button
                  key={account.role}
                  type="button"
                  className={`login-demo-chip${selectedRole === account.role ? ' selected' : ''}`}
                  title={`${account.label} (${account.email})`}
                  onClick={() => selectPersona(account)}
                >
                  <span style={{ fontWeight: 600 }}>{account.email.split('@')[0]}@</span>
                  <span style={{ opacity: 0.8, marginLeft: '4px' }}>· {account.label.replace(' (Home Affairs)', '')}</span>
                </button>
              ))}
            </div>

            {selectedAccount && (
              <span className="login-scope">
                <label className="login-scope-label" htmlFor="loginScopeBranch">
                  🏛️ Tenancy Scope: Department of Home Affairs
                  <em className="login-scope-default">
                    (Live Demo Tenant)
                  </em>
                </label>
                {tenancy ? (
                  <span className="login-scope-row">
                    <select
                      id="loginScopeBranch"
                      className="form-input"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                    >
                      <option value="">Whole department (All 8 DHA branches)</option>
                      {tenancy.departments.find((d) => d.id === 'home-affairs-digital')?.branches.map((b) => (
                        <option key={b.id} value={b.id}>
                          Branch: {b.name}
                        </option>
                      ))}
                    </select>
                  </span>
                ) : (
                  <span className="login-scope-summary">
                    Home Affairs scope active (seeded AppScan & Imperva feeds).
                  </span>
                )}
                <span className="login-scope-summary">
                  Department of Home Affairs · 8 active branches (Civic, Digital, Immigration, Operations, HRMD, CCSS, Finance, Planning)
                </span>
              </span>
            )}
          </div>

          {error && <div className="login-error" id="loginError">{error}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading
              ? '⏳ Signing in…'
              : selectedAccount
              ? `Sign In as ${selectedAccount.label} (${selectedAccount.email.split('@')[0]}@)`
              : 'Sign In to Dashboard'}
          </button>

          <span className="login-demo-line" style={{ textAlign: 'center', display: 'block', marginTop: '10px' }}>
            <code>admin@example.com / admin123</code> unlocks all dashboards · pick a persona above to switch
          </span>
        </form>
      </div>
    </div>
  );
}