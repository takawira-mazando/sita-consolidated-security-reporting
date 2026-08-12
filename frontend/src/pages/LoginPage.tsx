import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { fetchTenancy, TenancyResponse, LoginScope } from '../api/auth';

interface LoginPageProps {
  onClose?: () => void;
}

const ACCOUNT_DEFAULT = '__account_default__';

export default function LoginPage({ onClose }: LoginPageProps) {
  const { login, loginDemo, demoAccounts } = useAuth();
  const [email, setEmail] = useState('exec@example.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [tenancy, setTenancy] = useState<TenancyResponse | null>(null);
  const [dept, setDept] = useState<string>(ACCOUNT_DEFAULT);
  const [branch, setBranch] = useState<string>('');
  const [province, setProvince] = useState<string>(ACCOUNT_DEFAULT);

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

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await login(email, password);
    if (result.ok) {
      document.body.style.overflow = '';
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const loginAs = async (role: string) => {
    setError('');
    let scope: LoginScope | undefined;
    if (province !== ACCOUNT_DEFAULT) {
      scope = { department_id: null, branch_id: null, province_id: province };
    } else if (dept !== ACCOUNT_DEFAULT) {
      scope = { department_id: dept, branch_id: branch || null, province_id: null };
    }
    const result = await loginDemo(role, scope);
    if (result.ok) {
      document.body.style.overflow = '';
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const selectedDept = tenancy?.departments.find((d) => d.id === dept) ?? null;
  const isProvinceScoped = province !== ACCOUNT_DEFAULT;

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
              onChange={(e) => setEmail(e.target.value)}
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
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="login-btn">Sign In to Dashboard</button>
          <div className="login-error" id="loginError">{error}</div>
          <div className="login-hint">
            <strong style={{ color: 'var(--text-secondary)' }}>Demo accounts — one-click:</strong>
            <span className="login-demo-chips">
              {demoAccounts.map((account) => (
                <button
                  key={account.role}
                  type="button"
                  className="login-demo-chip"
                  title={`Sign in as ${account.label}`}
                  onClick={() => loginAs(account.role)}
                >
                  {account.email.split('@')[0]}@
                </button>
              ))}
            </span>
            {tenancy && (
              <span className="login-scope">
                <label className="login-scope-label" htmlFor="loginScopeProvince">
                  Tenancy scope
                  {!isProvinceScoped && !selectedDept ? (
                    <em className="login-scope-default">(account default)</em>
                  ) : null}
                </label>
                <span className="login-scope-row">
                  <select
                    id="loginScopeProvince"
                    className="form-input"
                    value={province}
                    onChange={(e) => {
                      setProvince(e.target.value);
                      if (e.target.value !== ACCOUNT_DEFAULT) {
                        setDept(ACCOUNT_DEFAULT);
                        setBranch('');
                      }
                    }}
                  >
                    <option value={ACCOUNT_DEFAULT}>
                      Account default — whole estate
                    </option>
                    {tenancy.provinces.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.department_count} depts)
                      </option>
                    ))}
                  </select>
                  <select
                    className="form-input"
                    value={dept}
                    disabled={isProvinceScoped}
                    onChange={(e) => {
                      setDept(e.target.value);
                      setBranch('');
                    }}
                  >
                    <option value={ACCOUNT_DEFAULT}>National — all departments</option>
                    {tenancy.departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.branch_count})
                      </option>
                    ))}
                  </select>
                  <select
                    className="form-input"
                    value={branch}
                    disabled={!selectedDept || isProvinceScoped}
                    onChange={(e) => setBranch(e.target.value)}
                  >
                    <option value="">Whole department</option>
                    {selectedDept?.branches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </span>
                <span className="login-scope-summary">
                  {tenancy.counts.departments} national + {tenancy.counts.provincial_departments} provincial departments ·{' '}
                  {tenancy.counts.provinces} provinces · {tenancy.counts.branches} branches across the SITA estate
                </span>
              </span>
            )}
            <span className="login-demo-line">
              <code>admin@example.com / admin123</code> unlocks all dashboards
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
