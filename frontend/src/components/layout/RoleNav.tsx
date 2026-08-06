import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ALL_ROLES } from '../../context/AuthContext';

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

export default function RoleNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const baseRoles = user?.roles || [];
  const allowedRoles = baseRoles.includes('admin') ? ALL_ROLES : baseRoles;
  const canManageUsers = allowedRoles.includes('sre');
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
        <span className="nav-user">{userName}</span>
        <button className="logout-btn" onClick={handleLogout}>Sign Out</button>
      </div>
    </nav>
  );
}
