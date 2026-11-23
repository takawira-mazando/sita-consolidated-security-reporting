import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import { useDemoMode } from './context/DemoContext';
import RoleNav from './components/layout/RoleNav';
import { getTierAccess, rolesForTenantWorkspace, TENANT_WORKSPACE_STORAGE_KEY } from './context/AuthContext';
import type { TenancyTier } from './types';
import MsspTenantAdmin from './components/multiTenant/MsspTenantAdmin';
import TenantMemberAdmin from './components/multiTenant/TenantMemberAdmin';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SetClientSuperadminPasswordPage from './pages/SetClientSuperadminPasswordPage';
import AdminUsersPage from './pages/AdminUsersPage';
import ExecDashboard from './pages/ExecDashboard';
import SocDashboard from './pages/SocDashboard';
import AppSecDashboard from './pages/AppSecDashboard';
import DbSecDashboard from './pages/DbSecDashboard';
import ComplianceDashboard from './pages/ComplianceDashboard';
import SreDashboard from './pages/SreDashboard';
import AiIntelPage from './pages/AiIntelPage';

// Dashboard key → component factory (receives tier)
const DASH_COMPONENTS: Record<string, (tier: TenancyTier) => JSX.Element> = {
  exec:       (tier) => <ExecDashboard tier={tier} />,
  soc:        (tier) => <SocDashboard tier={tier} />,
  appsec:     (tier) => <AppSecDashboard tier={tier} />,
  dbsec:      (tier) => <DbSecDashboard tier={tier} />,
  compliance: (tier) => <ComplianceDashboard tier={tier} />,
  sre:        (tier) => <SreDashboard tier={tier} />,
  ai:         (tier) => <AiIntelPage tier={tier} />,
};

function DemoBanner({ demoMode, onDismiss }: { demoMode: boolean; onDismiss: () => void }) {
  if (!demoMode) return null;
  return (
    <div className="demo-banner" onClick={onDismiss}>
      <span>🧪 <strong>DEMO MODE ACTIVE</strong> — Showing seeded test data from AppScan, Imperva WAF &amp; API Security connectors. Click to dismiss.</span>
      <button className="demo-banner-dismiss" onClick={(e) => { e.stopPropagation(); onDismiss(); }} aria-label="Dismiss demo banner">✕</button>
    </div>
  );
}

export default function App() {
  const { user, isLoading, sessionNonce, loginDemo, logout } = useAuth();
  const { demoMode } = useDemoMode();
  const [showDemoBanner, setShowDemoBanner] = useState(demoMode);
  const location = useLocation();
  const navigate = useNavigate();
  const isProviderAdmin = location.pathname.startsWith('/platform/admin');
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(
    () => localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY) || user?.active_tenant_workspace_id || '',
  );

  useEffect(() => {
    const syncWorkspace = () => {
      setActiveWorkspaceId(localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY) || '');
    };
    window.addEventListener('tenant-workspace-change', syncWorkspace);
    return () => window.removeEventListener('tenant-workspace-change', syncWorkspace);
  }, []);

  // Instant execution handler for URL deep links: ?demo_login=<role>&goto=<path>
  useEffect(() => {
    if (location.pathname === '/set-password' || location.pathname === '/client/admin') return;
    const params = new URLSearchParams(window.location.search);
    const demoRole = params.get('demo_login');
    const targetGoto = params.get('goto');
    if (demoRole) {
      loginDemo(demoRole).then((res) => {
        if (res.ok) {
          window.history.replaceState({}, document.title, window.location.pathname);
          if (targetGoto) {
            navigate(targetGoto);
          }
        }
      });
    }
  }, [loginDemo, location.pathname, navigate]);

  if (location.pathname === '/set-password') {
    return <SetClientSuperadminPasswordPage />;
  }

  if (isLoading) {
    return <div className="loading-screen">Loading Security Intelligence Platform...</div>;
  }

  if (!user) {
    return (
      <>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
      </>
    );
  }

  const roles = rolesForTenantWorkspace(user, activeWorkspaceId);

  if (roles.includes('client-admin')) {
    return (
      <div className="app-wrapper">
        <Routes>
          <Route path="/client/admin" element={<MsspTenantAdmin />} />
          <Route path="*" element={<Navigate to="/client/admin" replace />} />
        </Routes>
      </div>
    );
  }

  if (roles.some((role) => ['admin', 'tenant-admin', 'transversal-admin'].includes(role))) {
    return (
      <div className="app-wrapper">
        <RoleNav />
        <TenantMemberAdmin />
      </div>
    );
  }

  const access = getTierAccess(roles);
  const hasAssignedAccess = access.platform.length + access.workspace.length > 0 || access.adminTiers.length > 0;
  if (!hasAssignedAccess) {
    return (
      <main className="loading-screen">
        <p>This account has no active tenant service role. Contact a platform administrator.</p>
        <button onClick={() => { logout(); navigate('/'); }}>Sign out</button>
      </main>
    );
  }

  // Determine the user's primary (first non-empty) tier and default dashboard.
  // Admin-only roles have no security dashboard keys; detect and route to /admin.
  const primaryTier: TenancyTier = (() => {
    if (access.platform.length || access.adminTiers.includes('platform')) return 'platform';
    return 'workspace';
  })();
  const tierDashboards = access[primaryTier] ?? [];
  const isAdminOnly = tierDashboards.length === 0 && access.adminTiers.includes(primaryTier);
  const primaryDash = isAdminOnly ? 'admin' : (tierDashboards[0] || 'exec');

  // Default landing: /<primaryTier>/<primaryDash>
  const defaultPath = `/${primaryTier}/${primaryDash}`;

  return (
    <div className="app-wrapper" key={`${user.sub}:${sessionNonce}`}>
      <RoleNav />
      {showDemoBanner && !isProviderAdmin && <DemoBanner demoMode={demoMode} onDismiss={() => setShowDemoBanner(false)} />}
      <Routes>
        <Route path="/login" element={<Navigate to={defaultPath} />} />
        <Route
          path="/client/tenant-admin"
          element={roles.includes('tenant-admin') ? <TenantMemberAdmin /> : <Navigate to={defaultPath} replace />}
        />

        {/* Workspace dashboard routes use tenant-configured hierarchy scopes. */}
        {access.workspace.map((key) => (
            <Route
              key={`workspace/${key}`}
              path={`/workspace/${key}`}
              element={DASH_COMPONENTS[key]?.('workspace') ?? <Navigate to={defaultPath} />}
            />
        ))}
        {access.adminTiers.includes('platform') && (
          <Route path="/platform/admin" element={<AdminUsersPage />} />
        )}

        {/* Legacy flat dashboard URLs redirect to the generic workspace route. */}
        {(['exec','soc','appsec','dbsec','compliance','sre','ai'] as const).map((key) => (
          <Route key={`legacy-${key}`} path={`/${key}`} element={<Navigate to={`/workspace/${key}`} />} />
        ))}
        <Route path="/platform" element={<Navigate to="/platform/admin" replace />} />
        <Route path="/users" element={<Navigate to="/platform/admin" replace />} />

        <Route path="/" element={<Navigate to={defaultPath} />} />
        <Route path="*" element={<Navigate to={defaultPath} />} />
      </Routes>
    </div>
  );
}
