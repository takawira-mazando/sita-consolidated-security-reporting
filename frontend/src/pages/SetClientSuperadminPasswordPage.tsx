import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { completeClientSuperadminInvitation } from '../api/auth';
import PlatformBrand from '../components/layout/PlatformBrand';

export default function SetClientSuperadminPasswordPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [token, setToken] = useState(() => location.hash.startsWith('#') ? location.hash.slice(1) : '');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!location.hash) return;
    setToken(location.hash.slice(1));
    navigate({ pathname: location.pathname, search: location.search, hash: '' }, { replace: true });
  }, [location.hash, location.pathname, location.search, navigate]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!token) {
      setError('This setup link is missing its invitation token. Request a new invitation from HOSI Technologies.');
      return;
    }
    if (password !== confirmation) {
      setError('The passwords do not match.');
      return;
    }
    if (password.length < 12) {
      setError('Choose a password with at least 12 characters.');
      return;
    }

    setBusy(true);
    try {
      await completeClientSuperadminInvitation(token, password);
      setComplete(true);
      setPassword('');
      setConfirmation('');
    } catch (reason) {
      const detail = (reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Could not complete account setup. Request a new invitation if this link has expired.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-overlay">
      <section className="login-card" aria-labelledby="client-superadmin-password-title">
        <div className="login-header">
          <div className="login-logo-mark">
            <PlatformBrand className="platform-brand-login" />
          </div>
          <div className="login-title" id="client-superadmin-password-title">
            {complete ? 'Account setup complete' : 'Set up your client superadmin account'}
          </div>
          <p className="login-sub">
            {complete
              ? 'Your account is ready. Sign in with your email and new password.'
              : 'Create a password to access your organization’s tenant and access administration.'}
          </p>
        </div>
        {complete ? (
          <div className="login-body">
            <button type="button" className="login-submit" onClick={() => navigate('/login', { replace: true })}>
              Continue to sign in
            </button>
          </div>
        ) : (
          <form className="login-body" onSubmit={submit}>
            <label className="form-field">
              <span className="form-label">New password</span>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
              />
            </label>
            <label className="form-field">
              <span className="form-label">Confirm new password</span>
              <input
                type="password"
                className="form-input"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
              />
            </label>
            <p className="login-client-hint">Use at least 12 characters. This setup link is valid once and expires after 24 hours.</p>
            {!token && (
              <div className="login-error" role="alert">
                This setup link is missing its invitation token. Request a new invitation from HOSI Technologies.
              </div>
            )}
            {error && <div className="login-error" role="alert">{error}</div>}
            <button type="submit" className="login-submit" disabled={busy || !token}>
              {busy ? 'Setting password…' : 'Set password'}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
