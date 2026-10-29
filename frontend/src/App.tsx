import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import { useDemoMode } from './context/DemoContext';
import RoleNav from './components/layout/RoleNav';
import { getTierAccess } from './context/AuthContext';
import type { TenancyTier } from './types';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import AdminUsersPage from './pages/AdminUsersPage';
import ExecDashboard from './pages/ExecDashboard';
import SocDashboard from './pages/SocDashboard';
import AppSecDashboard from './pages/AppSecDashboard';
import DbSecDashboard from './pages/DbSecDashboard';
import ComplianceDashboard from './pages/ComplianceDashboard';
import SreDashboard from './pages/SreDashboard';
import AiIntelPage from './pages/AiIntelPage';
import DemoTourGuide from './components/layout/DemoTourGuide';

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
  const { user, isLoading, sessionNonce, loginDemo } = useAuth();
  const { demoMode } = useDemoMode();
  const [showDemoBanner, setShowDemoBanner] = useState(demoMode);
  const navigate = useNavigate();

  // Instant execution handler for URL deep links: ?demo_login=<role>&goto=<path>
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const demoRole = params.get('demo_login');
    const branch = params.get('branch');
    const targetGoto = params.get('goto');
    if (demoRole) {
      const scope = branch ? { department_id: 'home-affairs-digital', branch_id: branch, province_id: null } : undefined;
      loginDemo(demoRole, scope).then((res) => {
        if (res.ok) {
          window.history.replaceState({}, document.title, window.location.pathname);
          if (targetGoto) {
            navigate(targetGoto);
          }
        }
      });
    }
  }, [loginDemo, navigate]);

  if (isLoading) {
    return <div className="loading-screen">Loading SITA Platform...</div>;
  }

  if (!user) {
    return (
      <>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
        <DemoTourGuide />
      </>
    );
  }

  const roles = user.roles?.length ? user.roles : ['exec'];
  const access = getTierAccess(roles);

  // Determine the user's primary (first non-empty) tier and default dashboard.
  // Admin-only roles have no security dashboard keys; detect and route to /admin.
  const primaryTier: TenancyTier = (() => {
    if (access.sita?.length && access.isSitaSuperadmin) return 'sita';
    if (access.national.length) return 'national';
    if (access.dept.length) return 'dept';
    if (access.branch.length) return 'branch';
    // No dashboard tabs at all — find the highest admin tier
    const adminOrder: TenancyTier[] = ['sita', 'national', 'dept', 'branch'];
    return adminOrder.find((t) => access.adminTiers.includes(t)) ?? 'national';
  })();
  const tierDashboards = access[primaryTier] ?? [];
  const isAdminOnly = tierDashboards.length === 0 && access.adminTiers.includes(primaryTier);
  const primaryDash = isAdminOnly ? 'admin' : (tierDashboards[0] || 'exec');

  // Default landing: /<primaryTier>/<primaryDash>
  const defaultPath = `/${primaryTier}/${primaryDash}`;

  return (
    <div className="app-wrapper" key={`${user.sub}:${sessionNonce}`}>
      <RoleNav />
      {showDemoBanner && <DemoBanner demoMode={demoMode} onDismiss={() => setShowDemoBanner(false)} />}
      <Routes>
        <Route path="/login" element={<Navigate to={defaultPath} />} />

        {/* Tier-scoped dashboard + admin routes */}
        {(['sita', 'national', 'dept', 'branch'] as const).flatMap((tier) => {
          const dashboards = (tier === 'sita' ? access.sita : access[tier]) ?? [];
          const canAdmin = access.adminTiers.includes(tier);
          const routes = dashboards.map((key) => (
            <Route
              key={`${tier}/${key}`}
              path={`/${tier}/${key}`}
              element={DASH_COMPONENTS[key]?.(tier) ?? <Navigate to={defaultPath} />}
            />
          ));
          if (canAdmin) {
            routes.push(
              <Route
                key={`${tier}/admin`}
                path={`/${tier}/admin`}
                element={<AdminUsersPage adminTier={tier} />}
              />
            );
          }
          return routes;
        })}

        {/* Legacy flat routes → redirect to tiered equivalents */}
        {(['exec','soc','appsec','dbsec','compliance','sre','ai'] as const).map((key) => (
          <Route key={`legacy-${key}`} path={`/${key}`} element={<Navigate to={`/${primaryTier}/${key}`} />} />
        ))}
        <Route path="/users" element={<Navigate to={`/${primaryTier}/admin`} />} />

        <Route path="/" element={<Navigate to={defaultPath} />} />
        <Route path="*" element={<Navigate to={defaultPath} />} />
      </Routes>
      <DemoTourGuide />
    </div>
  );
}
