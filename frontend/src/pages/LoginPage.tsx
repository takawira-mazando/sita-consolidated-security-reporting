import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { ADMIN_EMAIL } from '../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('exec@example.com');
  const [password, setPassword] = useState('pass123');
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await login(email, password);
    if (!result.ok) {
      setError(result.error || 'Login failed');
    }
  };

  return (
    <div className="login-overlay">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo-mark">
            <div className="login-diamond"><span>S</span></div>
            <span className="login-org">SITA · Security</span>
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
            <strong style={{ color: 'var(--text-secondary)' }}>Demo accounts — all passwords:</strong> <span className="pw">pass123</span><br />
            <code>exec@</code> · <code>soc@</code> · <code>appsec@</code> · <code>dbsec@</code> · <code>compliance@</code> · <code>sre@example.com</code><br />
            Admin: <code>{ADMIN_EMAIL}</code> / <code>admin123</code> <span style={{ color: 'var(--blue)' }}>— unlocks all dashboards</span>
          </div>
        </form>
      </div>
    </div>
  );
}
