import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import RoleNav from './components/layout/RoleNav';
import { ALL_ROLES } from './context/AuthContext';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import AdminUsersPage from './pages/AdminUsersPage';
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
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    );
  }

  const baseRoles = user.roles?.length ? user.roles : ALL_ROLES;
  const allowedRoles = baseRoles.includes('admin') ? ALL_ROLES : baseRoles;
  const defaultRole = allowedRoles[0];
  const canManageUsers = allowedRoles.includes('sre');

  return (
    <div className="app-wrapper">
      <RoleNav />
      <Routes>
        <Route path="/login" element={<Navigate to={`/${defaultRole}`} />} />
        {allowedRoles.map((role) => (
          <Route key={role} path={`/${role}`} element={DASHBOARDS[role]?.element || <Navigate to={`/${defaultRole}`} />} />
        ))}
        {canManageUsers && <Route path="/users" element={<AdminUsersPage />} />}
        <Route path="/" element={<Navigate to={`/${defaultRole}`} />} />
        <Route path="*" element={<Navigate to={`/${defaultRole}`} />} />
      </Routes>
    </div>
  );
}
