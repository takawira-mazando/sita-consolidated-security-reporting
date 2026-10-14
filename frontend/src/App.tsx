import { Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
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
  const { user, isLoading, sessionNonce } = useAuth();
  const { demoMode } = useDemoMode();
  const [showDemoBanner, setShowDemoBanner] = useState(demoMode);

  if (isLoading) {
    return <div className="loading-screen">Loading SITA Platform...</div>;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    );
  }

  const roles = user.roles?.length ? user.roles : ['exec'];
  const access = getTierAccess(roles);

  // Determine the user's primary (first non-empty) tier and default dashboard
  const primaryTier: TenancyTier =
    (access.sita?.length && access.isSitaSuperadmin) ? 'sita' :
    access.national.length ? 'national' :
    access.dept.length     ? 'dept'     :
    'branch';
  const primaryDash = (access[primaryTier]?.[0]) || 'exec';

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
    </div>
  );
}
