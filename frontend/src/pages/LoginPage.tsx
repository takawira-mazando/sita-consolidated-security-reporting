import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { fetchTenancy, TenancyResponse, LoginScope, filterTenancy, TenancyEntitlement } from '../api/auth';
import type { DemoAccount } from '../types';

interface LoginPageProps {
  onClose?: () => void;
}

const ACCOUNT_DEFAULT = '__account_default__';

const ADMIN_ROLES = ['dept-admin', 'branch-admin', 'transversal-admin', 'admin', 'operator'];
const PROVINCIAL_ROLES = ['province-soc-lead', 'province-dept-admin', 'local-appsec'];

const PERSONA_GROUPS = ['National', 'Provincial', 'Administration'] as const;

function personaGroup(role: string): string {
  if (PROVINCIAL_ROLES.includes(role)) return 'Provincial';
  if (ADMIN_ROLES.includes(role)) return 'Administration';
  return 'National';
}

export default function LoginPage({ onClose }: LoginPageProps) {
  const { login, loginDemo, demoAccounts } = useAuth();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [tenancy, setTenancy] = useState<TenancyResponse | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [province, setProvince] = useState<string>(ACCOUNT_DEFAULT);
  const [dept, setDept] = useState<string>(ACCOUNT_DEFAULT);
  const [branch, setBranch] = useState<string>('');
  const [search, setSearch] = useState('');

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

  const entitlement: TenancyEntitlement | null = selectedAccount
    ? {
        isNationwide: !!selectedAccount.is_nationwide,
        provinceIds: selectedAccount.province_ids || [],
        departmentIds: selectedAccount.department_ids || [],
      }
    : null;

  const filteredTenancy = useMemo(
    () => (tenancy && entitlement ? filterTenancy(tenancy, entitlement) : null),
    [tenancy, entitlement]
  );

  const pickableProvinces = filteredTenancy?.provinces ?? [];
  const pickableDepartments = useMemo(() => {
    const depts = filteredTenancy?.departments ?? [];
    if (!search.trim()) return depts;
    const q = search.trim().toLowerCase();
    return depts.filter((d) => d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q));
  }, [filteredTenancy, search]);

  const defaultLabel = selectedAccount
    ? selectedAccount.is_nationwide
      ? 'whole estate'
      : selectedAccount.province_name
      ? selectedAccount.province_name
      : selectedAccount.department_name || 'account default'
    : '';

  const isProvinceScoped = province !== ACCOUNT_DEFAULT;
  const selectedDept = pickableDepartments.find((d) => d.id === dept) ?? null;

  const personaScope = (): LoginScope | undefined => {
    if (province !== ACCOUNT_DEFAULT) return { department_id: null, branch_id: null, province_id: province };
    if (dept !== ACCOUNT_DEFAULT) return { department_id: dept, branch_id: branch || null, province_id: null };
    return undefined;
  };

  const closeOverlay = () => {
    document.body.style.overflow = '';
    if (onClose) onClose();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const result = await login(email, password);
    if (result.ok) {
      closeOverlay();
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const selectPersona = (account: DemoAccount) => {
    setSelectedRole(account.role);
    setProvince(ACCOUNT_DEFAULT);
    setDept(ACCOUNT_DEFAULT);
    setBranch('');
    setSearch('');
  };

  const signInAsPersona = async (account: DemoAccount) => {
    setError('');
    const result = await loginDemo(account.role, personaScope());
    if (result.ok) {
      closeOverlay();
    } else {
      setError(result.error || 'Sign in failed');
    }
  };

  const groupedAccounts = PERSONA_GROUPS.map((group) => ({
    group,
    accounts: demoAccounts.filter((a) => personaGroup(a.role) === group),
  })).filter((g) => g.accounts.length > 0);

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
            <strong style={{ color: 'var(--text-secondary)' }}>Demo personas — pick one, then sign in:</strong>
            <div className="login-demo-groups">
              {groupedAccounts.map(({ group, accounts }) => (
                <div key={group} className="login-demo-group">
                  <div className="login-demo-group-t">{group}</div>
                  <div className="login-demo-chips">
                    {accounts.map((account) => (
                      <button
                        key={account.role}
                        type="button"
                        className={`login-demo-chip${selectedRole === account.role ? ' selected' : ''}`}
                        title={account.label}
                        onClick={() => selectPersona(account)}
                      >
                        {account.email.split('@')[0]}@
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {selectedAccount && (
              <span className="login-scope">
                <label className="login-scope-label" htmlFor="loginScopeProvince">
                  Tenancy scope
                  {!isProvinceScoped && dept === ACCOUNT_DEFAULT ? (
                    <em className="login-scope-default">
                      (account default — {defaultLabel || 'as assigned'})
                    </em>
                  ) : null}
                </label>
                {tenancy ? (
                  <span className="login-scope-row">
                    <select
                      id="loginScopeProvince"
                      className="form-input"
                      value={province}
                      disabled={pickableProvinces.length === 0}
                      onChange={(e) => {
                        setProvince(e.target.value);
                        if (e.target.value !== ACCOUNT_DEFAULT) {
                          setDept(ACCOUNT_DEFAULT);
                          setBranch('');
                        }
                      }}
                    >
                      <option value={ACCOUNT_DEFAULT}>
                        {pickableProvinces.length === 0 && !selectedAccount?.is_nationwide
                          ? 'National (department-scoped)'
                          : 'Account default — whole estate'}
                      </option>
                      {pickableProvinces.map((p) => (
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
                      <option value={ACCOUNT_DEFAULT}>
                        {selectedAccount?.is_nationwide
                          ? 'National — all departments'
                          : 'Account default — as assigned'}
                      </option>
                      {pickableDepartments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.branch_count} branches)
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
                ) : (
                  <span className="login-scope-summary">
                    Tenancy picker unavailable — will use the account's assigned scope.
                  </span>
                )}
                {filteredTenancy && filteredTenancy.departments.length > 4 && !isProvinceScoped && (
                  <input
                    type="search"
                    className="form-input login-scope-search"
                    placeholder="Search departments…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                )}
                <span className="login-scope-summary">
                  {tenancy
                    ? `${filteredTenancy?.departments.length ?? 0} reachable departments · ${
                        pickableProvinces.length ? `${pickableProvinces.length} provinces · ` : ''
                      }${tenancy.counts.branches} branches across the SITA estate`
                    : ''}
                </span>
                <button type="button" className="login-btn login-btn-persona" onClick={() => signInAsPersona(selectedAccount)}>
                  Sign in as {selectedAccount.email.split('@')[0]}@ {selectedAccount.label}
                </button>
              </span>
            )}
            <span className="login-demo-line">
              <code>admin@example.com / admin123</code> unlocks all dashboards · pick a persona above to scope sign-in
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}