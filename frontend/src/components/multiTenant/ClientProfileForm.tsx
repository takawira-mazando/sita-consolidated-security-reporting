import { useState, type FormEvent } from 'react';
import type { ClientOrganizationCreate } from '../../types';

interface Props {
  busy?: boolean;
  onComplete: (profile: ClientOrganizationCreate) => Promise<void>;
  onCancel: () => void;
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid var(--border-dim)',
  borderRadius: 10,
  background: 'var(--surface-2)',
  color: 'var(--text-primary)',
  fontSize: 13,
  marginTop: 5,
};

export default function ClientProfileForm({ busy = false, onComplete, onCancel }: Props) {
  const [name, setName] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [description, setDescription] = useState('');
  const [clientType, setClientType] = useState('enterprise');
  const [deploymentModel, setDeploymentModel] = useState<'saas' | 'on_premises'>('saas');
  const [primaryContactName, setPrimaryContactName] = useState('');
  const [primaryContactEmail, setPrimaryContactEmail] = useState('');
  const [superadminName, setSuperadminName] = useState('');
  const [superadminEmail, setSuperadminEmail] = useState('');
  const [error, setError] = useState('');

  const updateName = (value: string) => {
    setName(value);
    if (!identifier || identifier === name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')) {
      setIdentifier(value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 64));
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await onComplete({
        identifier,
        name,
        description,
        client_type: clientType,
        deployment_model: deploymentModel,
        primary_contact_name: primaryContactName,
        primary_contact_email: primaryContactEmail,
        superadmin_name: superadminName,
        superadmin_email: superadminEmail,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not create the client profile.');
    }
  };

  return (
    <form className="panel provider-profile-form" onSubmit={submit} style={{ width: '100%', padding: 24, margin: 0 }}>
      <header style={{ marginBottom: 22 }}>
        <h2 style={{ margin: 0, color: 'var(--text-primary)', fontSize: 20 }}>Create client profile</h2>
        <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
          Register the organization and its delivery model. Tenant structure and role configuration belong to the client’s workspace.
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
        <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
          Client organization name
          <input required minLength={2} maxLength={128} value={name} onChange={(event) => updateName(event.target.value)} placeholder="e.g. SITA" style={inputStyle} />
        </label>
        <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
          Profile identifier
          <input required minLength={2} maxLength={64} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="e.g. sita" style={inputStyle} />
        </label>
        <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
          Client type
          <select value={clientType} onChange={(event) => setClientType(event.target.value)} style={inputStyle}>
            <option value="enterprise">Enterprise</option>
            <option value="government">Government / public institution</option>
            <option value="institution">Institution</option>
            <option value="mssp">MSSP / managed security provider</option>
            <option value="other">Other</option>
          </select>
        </label>
        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Delivery model</legend>
          <div style={{ display: 'flex', gap: 8, marginTop: 5 }}>
            {([
              ['saas', 'Managed SaaS'],
              ['on_premises', 'On-premises'],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={deploymentModel === value}
                onClick={() => setDeploymentModel(value)}
                style={{
                  flex: 1,
                  padding: '9px 10px',
                  border: `1px solid ${deploymentModel === value ? '#D67D4A' : 'var(--border-dim)'}`,
                  borderRadius: 6,
                  background: deploymentModel === value ? 'rgba(214,125,74,0.12)' : 'var(--surface-2)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>
        <label style={{ gridColumn: '1 / -1', color: 'var(--text-secondary)', fontSize: 12 }}>
          Profile notes
          <textarea maxLength={4000} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Optional context about this client" style={{ ...inputStyle, resize: 'vertical' }} />
        </label>
      </div>

      <section style={{ marginTop: 22 }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15, color: 'var(--text-primary)' }}>Client contacts</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Primary contact name
            <input required minLength={2} maxLength={128} value={primaryContactName} onChange={(event) => setPrimaryContactName(event.target.value)} style={inputStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Primary contact email
            <input required type="email" maxLength={254} value={primaryContactEmail} onChange={(event) => setPrimaryContactEmail(event.target.value)} style={inputStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Designated client superadmin
            <input required minLength={2} maxLength={128} value={superadminName} onChange={(event) => setSuperadminName(event.target.value)} style={inputStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Superadmin email
            <input required type="email" maxLength={254} value={superadminEmail} onChange={(event) => setSuperadminEmail(event.target.value)} style={inputStyle} />
          </label>
        </div>
        <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>
          The designated superadmin is recorded for onboarding. Access remains pending until the client workspace and scoped invitation flow are ready; this does not create platform roles or permissions.
        </p>
      </section>

      {error && <div className="login-error" role="alert" style={{ marginTop: 16 }}>{error}</div>}
      <footer className="provider-form-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 22 }}>
        <button type="button" className="provider-secondary-button" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="submit" className="provider-create-button" disabled={busy}>{busy ? 'Creating…' : 'Create client profile'}</button>
      </footer>
    </form>
  );
}
