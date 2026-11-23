import { useState, type FormEvent } from 'react';
import type { ClientOrganization } from '../../types';

interface Props {
  client: ClientOrganization;
  action: 'provision' | 'reset';
  busy: boolean;
  onClose: () => void;
  onProvision: () => Promise<{
    email: string;
    temporary_password: string;
    email_status: 'sent' | 'not_configured' | 'delivery_failed';
  }>;
}

export default function ClientSuperadminProvisionDialog({ client, action, busy, onClose, onProvision }: Props) {
  const [error, setError] = useState('');
  const [credentials, setCredentials] = useState<{
    email: string;
    temporary_password: string;
    email_status: 'sent' | 'not_configured' | 'delivery_failed';
  } | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!client.superadmin_name.trim() || !client.superadmin_email.trim()) return;
    setError('');
    try {
      setCredentials(await onProvision());
    } catch (reason) {
      const detail = (reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || (reason instanceof Error ? reason.message : 'Could not provision the superadmin.'));
    }
  };

  return (
    <div
      className="overlay open"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <form className="overlay-content" onSubmit={submit} aria-labelledby="client-superadmin-provision-title">
        <button type="button" className="overlay-close" onClick={onClose} aria-label="Close" disabled={busy}>
          &times;
        </button>
        <h2 id="client-superadmin-provision-title" className="overlay-title">
          {action === 'reset' ? 'Reset' : 'Provision'} {client.name} superadmin
        </h2>
        <div
          className="provider-state-card"
          style={{ display: 'grid', minHeight: 0, gap: 6, margin: '16px 0', padding: '14px 16px' }}
        >
          <span className="provider-metric-label">Superadmin</span>
          <strong>{client.superadmin_name}</strong>
          <span className="provider-metric-label">Email</span>
          <span>{client.superadmin_email}</span>
        </div>
        {credentials && (
          <div role="status" style={{ border: '1px solid var(--border-dim)', borderRadius: 10, padding: 12 }}>
            <strong>Client superadmin credentials</strong>
            <p style={{ marginBottom: 6 }}>Email: <code>{credentials.email}</code></p>
            <p style={{ marginBottom: 6 }}>Temporary password: <code>{credentials.temporary_password}</code></p>
            {credentials.email_status !== 'sent' && (
              <p>Email delivery: {credentials.email_status === 'not_configured' ? 'SMTP is not configured' : 'delivery failed'}.</p>
            )}
            <p>Provide these credentials securely. The superadmin should change the temporary password after first sign-in.</p>
          </div>
        )}
        {error && <div className="login-error" role="alert">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn-mini" onClick={onClose} disabled={busy}>Cancel</button>
          {!credentials && (
            <button
              type="submit"
              className="btn-mini primary"
              disabled={!client.superadmin_name.trim() || !client.superadmin_email.trim() || busy}
            >
              {busy
                ? (action === 'reset' ? 'Resetting password…' : 'Creating account…')
                : (action === 'reset' ? 'Generate temporary password' : 'Create superadmin account')}
            </button>
          )}
          {credentials && (
            <button type="button" className="btn-mini primary" onClick={onClose}>Done</button>
          )}
        </div>
      </form>
    </div>
  );
}
