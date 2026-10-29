import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { getTierAccess } from '../../context/AuthContext';
import type { TenancyTier } from '../../types';
import {
  fetchTenancy,
  filterTenancy,
  entitlementFromUser,
  TenancyResponse,
} from '../../api/auth';
import { useDemoMode } from '../../context/DemoContext';
import DemoDirectorModal from './DemoDirectorModal';

interface RoleTab {
  role: string;
  label: string;
  color: string;
  pulse?: boolean;
}

const ROLE_TABS: RoleTab[] = [
  { role: 'exec',       label: 'Executive',   color: 'var(--red)',        pulse: true },
  { role: 'soc',        label: 'SOC Analyst', color: 'var(--blue)' },
  { role: 'appsec',     label: 'AppSec',      color: 'var(--amber)' },
  { role: 'dbsec',      label: 'DB Security', color: 'var(--green)' },
  { role: 'compliance', label: 'Compliance',  color: 'var(--violet)' },
  { role: 'sre',        label: 'Service Ops', color: 'var(--text-muted)' },
  { role: 'ai',         label: 'AI Intel & Alerts', color: '#8b5cf6' },
];

const TIER_META: Record<TenancyTier, { label: string; icon: string; hint: string }> = {
  sita:     { label: 'SITA Command Center (Tier 4)', icon: '🇿🇦', hint: 'Tier 4 Control Plane · SITA Superadmin #1 (admin@) — Mandated transversal infrastructure provider across 173 National & Provincial Departments. Provisions Transversal Superadmin #2 & National Data Plane Cockpits.' },
  national: { label: 'National Estate (Tier 3)',      icon: '🏛',  hint: 'Tier 3 Control Plane · National Gov Transversal Superadmin #2 (transversal@) — Sovereign oversight across National & Provincial Departments. Provisions Department Superadmins (Tier 2).' },
  dept:     { label: 'Department (Tier 2)',          icon: '🏢',  hint: 'Tier 2 Control Plane · Department Superadmin — Home Affairs PFMA Accounting Entity. Provisions Branch Admins (Tier 1) & Department Security Specialists.' },
  branch:   { label: 'Branch (Tier 1)',              icon: '📍',  hint: 'Tier 1 Control Plane · Branch Admin — DDG Operational Branch (DHA Immigration). Provisions branch-scoped AppSec, SOC & DBSec specialists.' },
};

const ACCOUNT_DEFAULT = '__account_default__';
const TIER_STORAGE_KEY = 'sita_active_tier';

export default function RoleNav() {
  const { user, logout, switchTenant } = useAuth();
  const { demoMode, toggleDemoMode } = useDemoMode();
  const navigate = useNavigate();
  const location = useLocation();

  const [aiMenuOpen, setAiMenuOpen] = useState(false);
  const [directorOpen, setDirectorOpen] = useState(false);
  const [switchOpen, setSwitchOpen] = useState(false);
  const [switchError, setSwitchError] = useState('');
  const [tenancy, setTenancy] = useState<TenancyResponse | null>(null);
  const [province, setProvince] = useState<string>(ACCOUNT_DEFAULT);
  const [dept, setDept] = useState<string>(ACCOUNT_DEFAULT);
  const [branch, setBranch] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    fetchTenancy()
      .then((t) => { if (!cancelled) setTenancy(t); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const entitlement = useMemo(() => (user ? entitlementFromUser(user) : null), [user]);
  const filteredTenancy = useMemo(
    () => (tenancy && entitlement ? filterTenancy(tenancy, entitlement) : null),
    [tenancy, entitlement],
  );
  const pickableDepartments = filteredTenancy?.departments ?? [];
  const isProvinceScoped = province !== ACCOUNT_DEFAULT;
  const selectedDept = pickableDepartments.find((d) => d.id === dept) ?? null;

  // --- Tier & access computation -------------------------------------------
  const baseRoles = user?.roles || [];
  const access = getTierAccess(baseRoles);

  // Only transversal-scoped roles may switch tenant scope.
  // Department-scoped personas are locked to their own scope — the backend
  // also enforces this on POST /auth/switch-tenant.
  const TRANSVERSAL_ROLES = new Set(['admin', 'transversal-admin', 'operator']);
  const canSwitchTenant = baseRoles.some((r) => TRANSVERSAL_ROLES.has(r));

  const availableTiers = useMemo(
    () => (['sita', 'national', 'dept', 'branch'] as TenancyTier[]).filter((t) => (access[t]?.length > 0) || access.adminTiers.includes(t)),
    [access],
  );

  // Derive active tier from URL path: /national/exec → 'national'
  const urlTier = location.pathname.split('/')[1] as TenancyTier | undefined;
  const isValidTier = urlTier && availableTiers.includes(urlTier);

  const [activeTier, setActiveTier] = useState<TenancyTier>(() => {
    if (isValidTier) return urlTier;
    const stored = localStorage.getItem(TIER_STORAGE_KEY) as TenancyTier | null;
    if (stored && availableTiers.includes(stored)) return stored;
    return availableTiers[0] ?? 'national';
  });

  // Sync activeTier with URL
  useEffect(() => {
    if (isValidTier && urlTier !== activeTier) {
      setActiveTier(urlTier);
    }
  }, [urlTier]);

  const activeDashboards = access[activeTier] ?? [];
  const canAdminThisTier = access.adminTiers.includes(activeTier);
  const activeRole = location.pathname.split('/')[2] || '';

  const switchTierTo = (tier: TenancyTier) => {
    setActiveTier(tier);
    localStorage.setItem(TIER_STORAGE_KEY, tier);
    // Admin-only tiers land on /admin; operational tiers land on first dashboard tab
    const tierDashes = access[tier];
    const isAdminOnly = tierDashes.length === 0 && access.adminTiers.includes(tier);
    const target = isAdminOnly ? 'admin' : (tierDashes[0] ?? (access.adminTiers.includes(tier) ? 'admin' : null));
    if (target) navigate(`/${tier}/${target}`);
  };

  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');
  const toggleTheme = () => {
    const next = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    document.body.dataset.theme = next;
    localStorage.setItem('sita_theme', next);
    setIsDark(next === 'dark');
  };

  const handleLogout = () => { logout(); navigate('/'); };

  const userName = user?.email?.split('@')[0] || 'user';
  const deptIds = user?.department_ids || [];
  const branchStr = user?.branch_names?.length
    ? ` » ${user.branch_names[0]}${user.branch_names.length > 1 ? ' (+' + (user.branch_names.length - 1) + ')' : ''}`
    : '';

  // Strict 4-Tier SITA Tenancy Scoping:
  // Tier 4: SITA Command Center, Tier 3: National Security Estate, Tier 2: Department (DHA Testbed), Tier 1: Branch
  let scopeLabel = 'National Security Estate';
  if (deptIds.length) {
    const dName = user?.department_name || (deptIds[0] === 'home-affairs-digital' ? 'Department of Home Affairs' : deptIds[0]);
    scopeLabel = `${dName}${branchStr}`;
  } else if (user?.roles?.some((r) => ['admin', 'operator'].includes(r))) {
    scopeLabel = 'SITA National Security Command Center';
  } else if (user?.roles?.includes('transversal-admin')) {
    scopeLabel = 'National Security Estate (Transversal)';
  } else {
    scopeLabel = 'National Security Estate';
  }

  const scopeTitle = deptIds.length
    ? `Tenant scope: ${scopeLabel}`
    : 'Tenant scope: SITA Whole-of-Government Estate';
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
    if (result.ok) { setSwitchOpen(false); }
    else { setSwitchError(result.error || 'Switch failed'); }
  };

  return (
    <nav className="role-nav">
      {/* Brand */}
      <div className="nav-brand">
        <img className="nav-logo-img" src="/sita-logo.gif" alt="SITA" />
      </div>
      <div className="nav-div" />

      {/* ── Tier Pill Selector ── */}
      {availableTiers.length > 1 && (
        <div className="tier-pills" role="group" aria-label="Tenancy tier">
          {availableTiers.map((tier) => (
            <button
              key={tier}
              id={`tier-pill-${tier}`}
              className={`tier-pill ${activeTier === tier ? 'active' : ''}`}
              title={TIER_META[tier].hint}
              onClick={() => switchTierTo(tier)}
            >
              <span className="tier-pill-icon">{TIER_META[tier].icon}</span>
              {TIER_META[tier].label}
            </button>
          ))}
        </div>
      )}
      <div className="nav-div" />

      {/* ── Role Dashboard Tabs (scoped to active tier) ── */}
      {ROLE_TABS.filter((t) => activeDashboards.includes(t.role)).map((t) => {
        if (t.role === 'ai') {
          return (
            <div
              key={t.role}
              style={{ position: 'relative', display: 'inline-flex' }}
              onMouseEnter={() => setAiMenuOpen(true)}
              onMouseLeave={() => setAiMenuOpen(false)}
            >
              <button
                id={`dash-tab-${activeTier}-${t.role}`}
                className={`role-tab ${activeRole === t.role ? 'active' : ''}`}
                onClick={() => {
                  navigate(`/${activeTier}/${t.role}`);
                  setAiMenuOpen(false);
                }}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <span className={`tab-orb ${t.pulse ? 'pulse' : ''}`} style={{ background: t.color }} />
                {t.label}
                <span style={{ fontSize: 9, opacity: 0.75 }}>▾</span>
              </button>

              {aiMenuOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    zIndex: 1000,
                    marginTop: 4,
                    minWidth: 260,
                    background: 'var(--ai-card-bg)',
                    border: '1px solid var(--ai-card-border)',
                    borderRadius: 12,
                    padding: '8px 0',
                    boxShadow: 'var(--ai-card-shadow)',
                    backdropFilter: 'blur(16px)',
                    animation: 'aiFlashFadeIn 0.2s ease',
                  }}
                >
                  <div
                    style={{
                      padding: '6px 14px 8px',
                      fontSize: 10,
                      fontWeight: 800,
                      color: '#818cf8',
                      letterSpacing: '0.08em',
                      borderBottom: '1px solid var(--ai-subcard-border)',
                      marginBottom: 4,
                    }}
                  >
                    AI INTELLIGENCE &amp; ALERTS SUITE
                  </div>

                  {[
                    { key: 'aimi-vapt', icon: '🛡️', label: 'AIMI VAPT Alert & Log Interpreter' },
                    { key: 'g2-report', icon: '🧠', label: 'G2 Report Studio & Copilot' },
                    { key: 'avp-2', icon: '🎯', label: 'Author Alert Rule (AVP-2)' },
                    { key: 'avp-3', icon: '🔍', label: 'Threat Campaign Attribution (AVP-3)' },
                    { key: 'avp-5', icon: '⚖️', label: 'POPIA s.22 Breach Dossier' },
                    { key: 'all', icon: '🌟', label: 'Unified View (All Engines)' },
                  ].map((item) => (
                    <button
                      key={item.key}
                      onClick={() => {
                        navigate(`/${activeTier}/ai?view=${item.key}`);
                        setAiMenuOpen(false);
                      }}
                      style={{
                        width: '100%',
                        padding: '7px 14px',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-primary)',
                        fontSize: 12,
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span>{item.icon}</span>
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        }

        return (
          <button
            key={t.role}
            id={`dash-tab-${activeTier}-${t.role}`}
            className={`role-tab ${activeRole === t.role ? 'active' : ''}`}
            onClick={() => navigate(`/${activeTier}/${t.role}`)}
          >
            <span className={`tab-orb ${t.pulse ? 'pulse' : ''}`} style={{ background: t.color }} />
            {t.label}
          </button>
        );
      })}

      {/* ── Admin Tab (tier-scoped) ── */}
      {canAdminThisTier && (
        <button
          id={`dash-tab-${activeTier}-admin`}
          className={`role-tab admin-tab ${activeRole === 'admin' ? 'active' : ''}`}
          onClick={() => navigate(`/${activeTier}/admin`)}
        >
          <span className="tab-orb" style={{ background: 'var(--violet)' }} />
          {TIER_META[activeTier].label} Admin
        </button>
      )}

      {/* ── Right-side controls ── */}
      <div className="nav-right">
        <button className="theme-toggle" onClick={toggleTheme}>
          {isDark ? '☀ Light' : '🌙 Dark'}
        </button>
        <button
          className={`demo-toggle ${demoMode ? 'active' : ''}`}
          onClick={toggleDemoMode}
          title={demoMode ? 'Exit Demo Mode (uses test data)' : 'Enter Demo Mode (uses test data)'}
        >
          {demoMode ? '🧪 Demo: ON' : '🧪 Demo'}
        </button>
        <button
          id="btn-demo-director"
          className="demo-toggle"
          style={{ background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)', color: '#fff', border: 'none', fontWeight: 700 }}
          onClick={() => setDirectorOpen(true)}
          title="Open Live Demonstration Director"
        >
          ⚡ Execute Demo
        </button>
        {demoMode && (
          <span className="demo-badge" title="Running in demo mode with seeded test data">DEMO</span>
        )}

        {/* Tenant scope — transversal roles get a switchable button; all others get a locked badge */}
        <div className="nav-dept-wrap">
          {canSwitchTenant ? (
            <button
              className="nav-dept"
              title={`${scopeTitle} — click to switch tenant scope`}
              onClick={() => setSwitchOpen((o) => !o)}
            >
              {scopeLabel}
              {extraDepts && <span className="nav-dept-more" style={{ marginLeft: 4 }}>{extraDepts}</span>}
            </button>
          ) : (
            <span
              className="nav-dept nav-dept--locked"
              title={`${scopeTitle} · Scope is fixed for your role`}
              aria-label="Your tenant scope is fixed and cannot be changed"
            >
              {scopeLabel}
              {extraDepts && <span className="nav-dept-more" style={{ marginLeft: 4 }}>{extraDepts}</span>}
              <span className="nav-dept-lock" aria-hidden="true">🔒</span>
            </span>
          )}
          {canSwitchTenant && switchOpen && (
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
                      if (e.target.value !== ACCOUNT_DEFAULT) { setDept(ACCOUNT_DEFAULT); setBranch(''); }
                    }}
                  >
                    <option value={ACCOUNT_DEFAULT}>
                      {filteredTenancy.provinces.length === 0 ? 'National (no province scope)' : 'Account default'}
                    </option>
                    {filteredTenancy.provinces.map((p) => (
                      <option key={p.id} value={p.id}>{p.name} ({p.department_count} depts)</option>
                    ))}
                  </select>
                  <select
                    className="form-input"
                    value={dept}
                    disabled={isProvinceScoped}
                    onChange={(e) => { setDept(e.target.value); setBranch(''); }}
                  >
                    <option value={ACCOUNT_DEFAULT}>
                      {entitlement?.isNationwide ? 'National — all departments' : 'Account default'}
                    </option>
                    {pickableDepartments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name} ({d.branch_count} branches)</option>
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
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                  <div className="tenant-switcher-row">
                    <button type="button" className="btn btn-flare tenant-switcher-go" onClick={() => doSwitch()}>Switch</button>
                    <button
                      type="button"
                      className="btn btn-outline tenant-switcher-reset"
                      onClick={() => doSwitch({ department_id: null, branch_id: null })}
                    >Reset to default</button>
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

      <DemoDirectorModal isOpen={directorOpen} onClose={() => setDirectorOpen(false)} />
    </nav>
  );
}