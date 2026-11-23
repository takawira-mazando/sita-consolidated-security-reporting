import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import {
  getTierAccess,
  rolesForTenantWorkspace,
  TENANT_WORKSPACE_STORAGE_KEY,
} from '../../context/AuthContext';
import type { TenancyTier } from '../../types';
import { useDemoMode } from '../../context/DemoContext';
import PlatformBrand from './PlatformBrand';

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
  platform: { label: 'Platform Administration', icon: '⚡', hint: 'Manage client profiles and platform access.' },
  workspace: { label: 'Tenant Workspace', icon: '🛡️', hint: 'Review security posture for the selected tenant workspace.' },
};

const TIER_STORAGE_KEY = 'platform_active_tier';

export default function RoleNav() {
  const { user, logout } = useAuth();
  const { demoMode } = useDemoMode();
  const navigate = useNavigate();
  const location = useLocation();
  const isProviderAdmin = location.pathname.startsWith('/platform/admin');
  const tenantWorkspaces = user?.tenant_workspace_access ?? [];
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(
    () => localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY) || user?.active_tenant_workspace_id || '',
  );
  const baseRoles = user ? rolesForTenantWorkspace(user, activeWorkspaceId) : [];
  const activeWorkspace = tenantWorkspaces.find(
    (workspace) => workspace.workspace_id === activeWorkspaceId,
  );
  const [aiMenuOpen, setAiMenuOpen] = useState(false);

  useEffect(() => {
    if (!tenantWorkspaces.length) return;
    if (!tenantWorkspaces.some((workspace) => workspace.workspace_id === activeWorkspaceId)) {
      const firstWorkspaceId = tenantWorkspaces[0].workspace_id;
      setActiveWorkspaceId(firstWorkspaceId);
      localStorage.setItem(TENANT_WORKSPACE_STORAGE_KEY, firstWorkspaceId);
    }
  }, [activeWorkspaceId, tenantWorkspaces]);

  const access = getTierAccess(baseRoles);

  const availableTiers = useMemo(
    () => (['platform', 'workspace'] as TenancyTier[]).filter((t) => (access[t]?.length > 0) || access.adminTiers.includes(t)),
    [access],
  );

  const urlTier = location.pathname.split('/')[1] as TenancyTier | undefined;
  const isValidTier = urlTier && availableTiers.includes(urlTier);

  const [activeTier, setActiveTier] = useState<TenancyTier>(() => {
    if (isValidTier) return urlTier;
    const stored = localStorage.getItem(TIER_STORAGE_KEY) as TenancyTier | null;
    if (stored && availableTiers.includes(stored)) return stored;
    return availableTiers[0] ?? 'workspace';
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
    const tierDashes = access[tier];
    const isAdminOnly = tierDashes.length === 0 && access.adminTiers.includes(tier);
    const target = isAdminOnly
      ? tier === 'platform' ? '/platform/admin' : '/client/tenant-admin'
      : tierDashes[0] ? `/${tier}/${tierDashes[0]}` : null;
    if (target) navigate(target);
  };

  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');

  const toggleTheme = () => {
    const next = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    document.body.dataset.theme = next;
    localStorage.setItem('platform_theme', next);
    setIsDark(next === 'dark');
  };

  const handleLogout = () => { logout(); navigate('/'); };

  const userName = user?.email?.split('@')[0] || 'user';
  const selectTenantWorkspace = (workspaceId: string) => {
    setActiveWorkspaceId(workspaceId);
    localStorage.setItem(TENANT_WORKSPACE_STORAGE_KEY, workspaceId);
    const storedUser = localStorage.getItem('platform_user');
    if (storedUser) {
      try {
        localStorage.setItem(
          'platform_user',
          JSON.stringify({
            ...JSON.parse(storedUser),
            active_tenant_workspace_id: workspaceId,
          }),
        );
      } catch {
        localStorage.removeItem('platform_user');
      }
    }
    window.dispatchEvent(new Event('tenant-workspace-change'));
    navigate('/login');
  };

  return (
    <nav className={`platform-header role-nav${isProviderAdmin ? ' role-nav-provider' : ''}`}>
      {/* Brand */}
      <div
        className="nav-brand"
        onClick={() => navigate('/')}
        title="Unified Data Security Platform - Return to Home"
      >
        <PlatformBrand subtitle={isProviderAdmin ? 'Platform administration' : undefined} />
      </div>
      {isProviderAdmin && (
        <p className="role-nav-provider-description">
          Register clients and manage their profile, contacts, and lifecycle.
        </p>
      )}
      {!isProviderAdmin && <div className="nav-div" />}

      {/* ── Tier Pill Selector ── */}
      {!isProviderAdmin && availableTiers.length > 1 && (
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
      {!isProviderAdmin && <div className="nav-div" />}

      {/* ── Role Dashboard Tabs (scoped to active tier) ── */}
      {!isProviderAdmin && ROLE_TABS.filter((t) => activeDashboards.includes(t.role)).map((t) => {
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
      {!isProviderAdmin && canAdminThisTier && (
        <button
          id={`dash-tab-${activeTier}-admin`}
          className={`role-tab admin-tab ${activeRole === 'admin' ? 'active' : ''}`}
          onClick={() => navigate(activeTier === 'platform' ? '/platform/admin' : '/client/tenant-admin')}
        >
          <span className="tab-orb" style={{ background: 'var(--violet)' }} />
          {TIER_META[activeTier].label} Admin
        </button>
      )}
      {!isProviderAdmin && baseRoles.includes('tenant-admin') && (
        <button
          className={`role-tab admin-tab ${location.pathname === '/client/tenant-admin' ? 'active' : ''}`}
          onClick={() => navigate('/client/tenant-admin')}
        >
          Tenant Access
        </button>
      )}

      {/* ── Right-side controls ── */}
      <div className="nav-right">
        {tenantWorkspaces.length > 0 && (
          <label className="tenant-workspace-switcher">
            <span className="sr-only">Active tenant</span>
            <select
              aria-label="Active tenant"
              value={activeWorkspace?.workspace_id ?? ''}
              onChange={(event) => selectTenantWorkspace(event.target.value)}
            >
              {tenantWorkspaces.map((workspace) => (
                <option key={workspace.workspace_id} value={workspace.workspace_id}>
                  {workspace.workspace_name}
                </option>
              ))}
            </select>
          </label>
        )}
        <button className="theme-toggle" onClick={toggleTheme}>
          {isDark ? '☀ Light' : '🌙 Dark'}
        </button>
        {demoMode && !isProviderAdmin && (
          <span className="demo-badge" title="Running in demo mode with seeded test data">DEMO</span>
        )}

        {!isProviderAdmin && (
          <span
            className="nav-dept nav-dept--locked"
            title={activeWorkspace ? `Tenant workspace: ${activeWorkspace.workspace_name}` : 'Platform scope'}
          >
            {activeWorkspace?.workspace_name ?? 'Platform'}
          </span>
        )}

        <span className="nav-user">{isProviderAdmin ? 'Hosi Administrator' : userName}</span>
        <button className="logout-btn" onClick={handleLogout}>Sign Out</button>
      </div>

    </nav>
  );
}
