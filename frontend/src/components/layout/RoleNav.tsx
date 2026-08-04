import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

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

  const allowedRoles = user?.roles || [];
  const activeRole = location.pathname.replace('/', '') || allowedRoles[0] || '';
  const isDark = document.body.dataset.theme !== 'light';

  const toggleTheme = () => {
    const next = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    document.body.dataset.theme = next;
    localStorage.setItem('sita_theme', next);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userName = user?.email?.split('@')[0] || 'user';

  return (
    <nav className="role-nav">
      <div className="nav-brand">
        <div className="nav-diamond" />
        <div className="nav-brand-text">
          SITA
          <small>Consolidated RBAC</small>
        </div>
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
