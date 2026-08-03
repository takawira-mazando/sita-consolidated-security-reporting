import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import RoleNav from './components/layout/RoleNav';
import { ALL_ROLES } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import ExecDashboard from './pages/ExecDashboard';
import SocDashboard from './pages/SocDashboard';
import AppSecDashboard from './pages/AppSecDashboard';
import DbSecDashboard from './pages/DbSecDashboard';
import ComplianceDashboard from './pages/ComplianceDashboard';
import SreDashboard from './pages/SreDashboard';

const DASHBOARDS: Record<string, { element: JSX.Element }> = {
  exec: { element: <ExecDashboard /> },
  soc: { element: <SocDashboard /> },
  appsec: { element: <AppSecDashboard /> },
  dbsec: { element: <DbSecDashboard /> },
  compliance: { element: <ComplianceDashboard /> },
  sre: { element: <SreDashboard /> },
};

export default function App() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="loading-screen">Loading SITA Platform...</div>;
  }

  if (!user) {
    return <LoginPage />;
  }

  const allowedRoles = user.roles?.length ? user.roles : ALL_ROLES;
  const defaultRole = allowedRoles[0];

  return (
    <div className="app-wrapper">
      <RoleNav />
      <Routes>
        <Route path="/login" element={<Navigate to={`/${defaultRole}`} />} />
        {allowedRoles.map((role) => (
          <Route key={role} path={`/${role}`} element={DASHBOARDS[role]?.element || <Navigate to={`/${defaultRole}`} />} />
        ))}
        <Route path="/" element={<Navigate to={`/${defaultRole}`} />} />
        <Route path="*" element={<Navigate to={`/${defaultRole}`} />} />
      </Routes>
    </div>
  );
}
