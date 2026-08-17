import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ALL_ROLES } from '../../context/AuthContext';
import {
  fetchTenancy,
  filterTenancy,
  entitlementFromUser,
  TenancyResponse,
} from '../../api/auth';

interface RoleTab {
  role: string;
  label: string;
  color: string;
  pulse?: boolean;
}

const ROLE_TABS: RoleTab[] = [
  { role: 'exec', label: 'Executive', color: 'var(--red)', pulse: true },
  { role: 'soc', label: 'SOC Analyst', color: 'var(--blue)' },
  { role: 'appsec', label: 'AppSec', color: 'var(--amber)' },
  { role: 'dbsec', label: 'DB Security', color: 'var(--green)' },
  { role: 'compliance', label: 'Compliance', color: 'var(--violet)' },
  { role: 'sre', label: 'Service Ops', color: 'var(--text-muted)' },
];

const ACCOUNT_DEFAULT = '__account_default__';

export default function RoleNav() {
  const { user, logout, switchTenant } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [switchOpen, setSwitchOpen] = useState(false);
  const [switchError, setSwitchError] = useState('');
  const [tenancy, setTenancy] = useState<TenancyResponse | null>(null);
  const [province, setProvince] = useState<string>(ACCOUNT_DEFAULT);
  const [dept, setDept] = useState<string>(ACCOUNT_DEFAULT);
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

  const entitlement = useMemo(() => (user ? entitlementFromUser(user) : null), [user]);
  const filteredTenancy = useMemo(
    () => (tenancy && entitlement ? filterTenancy(tenancy, entitlement) : null),
    [tenancy, entitlement]
  );
  const pickableDepartments = filteredTenancy?.departments ?? [];
  const isProvinceScoped = province !== ACCOUNT_DEFAULT;
  const selectedDept = pickableDepartments.find((d) => d.id === dept) ?? null;

  const baseRoles = user?.roles || [];
  const allowedRoles = baseRoles.includes('admin') ? ALL_ROLES : baseRoles;
  const canManageUsers = allowedRoles.some((r) => ['operator', 'sre', 'dept-admin', 'branch-admin', 'transversal-admin'].includes(r));
  const activeRole = location.pathname.replace('/', '') || allowedRoles[0] || '';
  const isDark = document.body.dataset.theme !== 'light';

  const toggleTheme = () => {
    const next = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    document.body.dataset.theme = next;
    localStorage.setItem('sita_theme', next);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const userName = user?.email?.split('@')[0] || 'user';

  const deptIds = user?.department_ids || [];
  const provinceStr = user?.province_name ? `${user.province_name} » ` : '';
  const branchStr = user?.branch_names?.length ? ` » ${user.branch_names[0]}${user.branch_names.length > 1 ? ' (+' + (user.branch_names.length - 1) + ')' : ''}` : '';
  
  const scopeLabel = deptIds.length
    ? `${provinceStr}${user?.department_name || deptIds[0]}${branchStr}`
    : user?.province_ids?.length
    ? `${provinceStr}${filteredTenancy?.departments.length || 0} departments`
    : 'National Estate';
    
  const scopeTitle = deptIds.length
    ? `Tenant scope: ${deptIds.length} department(s)${(user?.branch_names || []).length ? ` · ${(user?.branch_names || []).join(', ')}` : ''}`
    : 'Tenant scope: national (all departments)';
  const extraDepts = deptIds.length > 1 ? `+${deptIds.length - 1}` : null;

  const doSwitch = async (scopeOverride?: { department_id: string | null; branch_id: string | null; province_id?: string | null }) => {
    setSwitchError('');
    const scope =
      scopeOverride ??
      (province !== ACCOUNT_DEFAULT
        ? { department_id: null, branch_id: null, province_id: province }
        : dept !== ACCOUNT_DEFAULT
        ? { department_id: dept, branch_id: branch || null, province_id: null }
        : { department_id: null, branch_id: null });
    const result = await switchTenant(scope);
    if (result.ok) {
      setSwitchOpen(false);
    } else {
      setSwitchError(result.error || 'Switch failed');
    }
  };

  return (
    <nav className="role-nav">
      <div className="nav-brand">
        <img className="nav-logo-img" src="/sita-logo.gif" alt="SITA" />
      </div>
      <div className="nav-div" />
      {ROLE_TABS.filter((t) => allowedRoles.includes(t.role)).map((t) => (
        <button
          key={t.role}
          className={`role-tab ${activeRole === t.role ? 'active' : ''}`}
          onClick={() => navigate(`/${t.role}`)}
        >
          <span className={`tab-orb ${t.pulse ? 'pulse' : ''}`} style={{ background: t.color }} />
          {t.label}
        </button>
      ))}
      {canManageUsers && (
        <button
          className={`role-tab ${activeRole === 'users' ? 'active' : ''}`}
          onClick={() => navigate('/users')}
        >
          <span className="tab-orb" style={{ background: 'var(--violet)' }} />
          Users
        </button>
      )}
      <div className="nav-right">
        <button className="theme-toggle" onClick={toggleTheme}>
          {isDark ? '☀ Light' : '🌙 Dark'}
        </button>
        <div className="nav-dept-wrap">
          <button className="nav-dept" title={`${scopeTitle} — click to switch tenant`} onClick={() => setSwitchOpen((o) => !o)}>
            {scopeLabel}
            {extraDepts && <span className="nav-dept-more" style={{ marginLeft: 4 }}>{extraDepts}</span>}
          </button>
          {switchOpen && (
            <div className="tenant-switcher">
              <div className="tenant-switcher-t">
                Switch tenancy scope
                <button type="button" className="tenant-switcher-x" onClick={() => setSwitchOpen(false)} aria-label="Close">&times;</button>
              </div>
              {tenancy && filteredTenancy ? (
                <div className="tenant-switcher-body">
                  <select
                    className="form-input"
                    value={province}
                    disabled={(filteredTenancy.provinces.length || 0) === 0}
                    onChange={(e) => {
                      setProvince(e.target.value);
                      if (e.target.value !== ACCOUNT_DEFAULT) {
                        setDept(ACCOUNT_DEFAULT);
                        setBranch('');
                      }
                    }}
                  >
                    <option value={ACCOUNT_DEFAULT}>
                      {filteredTenancy.provinces.length === 0 ? 'National (no province scope)' : 'Account default'}
                    </option>
                    {filteredTenancy.provinces.map((p) => (
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
                      {entitlement?.isNationwide ? 'National — all departments' : 'Account default'}
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
                  <div className="tenant-switcher-row">
                    <button type="button" className="btn btn-flare tenant-switcher-go" onClick={() => doSwitch()}>
                      Switch
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline tenant-switcher-reset"
                      onClick={() => doSwitch({ department_id: null, branch_id: null })}
                    >
                      Reset to default
                    </button>
                  </div>
                  {switchError && <div className="tenant-switcher-err">{switchError}</div>}
                </div>
              ) : (
                <div className="tenant-switcher-body">Loading tenancy…</div>
              )}
            </div>
          )}
        </div>
        <span className="nav-user">{userName}</span>
        <button className="logout-btn" onClick={handleLogout}>Sign Out</button>
      </div>
    </nav>
  );
}