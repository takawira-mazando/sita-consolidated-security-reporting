import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

interface LoginPageProps {
  onClose?: () => void;
}

export default function LoginPage({ onClose }: LoginPageProps) {
  const { login, loginDemo, demoAccounts } = useAuth();
  const [email, setEmail] = useState('exec@example.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await login(email, password);
    if (result.ok) {
      document.body.style.overflow = '';
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const loginAs = async (role: string) => {
    setError('');
    const result = await loginDemo(role);
    if (result.ok) {
      document.body.style.overflow = '';
    } else {
      setError(result.error || 'Login failed');
    }
  };

  return (
    <div
      className={`login-overlay${onClose ? ' as-modal' : ''}`}
      onClick={(e) => {
        if (onClose && e.target === e.currentTarget) onClose();
      }}
    >
      <div className="login-card">
        {onClose && (
          <button type="button" className="overlay-close" onClick={onClose} aria-label="Close">&times;</button>
        )}
        <div className="login-header">
          <div className="login-logo-mark">
            <img className="login-logo-img" src="/sita-logo.gif" alt="SITA" />
          </div>
          <div className="login-title">Unified Intelligence Platform</div>
          <div className="login-sub">Consolidated RBAC security reporting — sign in to continue</div>
        </div>
        <form className="login-body" onSubmit={handleLogin}>
          <div className="form-field">
            <label className="form-label" htmlFor="loginEmail">Email address</label>
            <input
              type="email"
              className="form-input"
              id="loginEmail"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="loginPassword">Password</label>
            <input
              type="password"
              className="form-input"
              id="loginPassword"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="login-btn">Sign In to Dashboard</button>
          <div className="login-error" id="loginError">{error}</div>
          <div className="login-hint">
            <strong style={{ color: 'var(--text-secondary)' }}>Demo accounts — one-click:</strong>
            <span className="login-demo-chips">
              {demoAccounts.map((account) => (
                <button
                  key={account.role}
                  type="button"
                  className="login-demo-chip"
                  title={`Sign in as ${account.label}`}
                  onClick={() => loginAs(account.role)}
                >
                  {account.email.split('@')[0]}@
                </button>
              ))}
            </span>
            <span className="login-demo-line">
              <code>admin@example.com / admin123</code> unlocks all dashboards
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
