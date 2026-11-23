import { useMemo, useState, type FormEvent } from 'react';
import type { ClientOrganization, ClientOrganizationUpdate } from '../../types';
import ClientSuperadminProvisionDialog from './ClientSuperadminProvisionDialog';

interface Props {
  clients: ClientOrganization[];
  mode: 'profiles' | 'status';
  busyId?: string;
  loading: boolean;
  loadError: string;
  onReload: () => void;
  onCreateProfile?: () => void;
  onChangeStatus: (client: ClientOrganization, status: string) => Promise<void>;
  onSaveProfile: (clientId: string, updates: ClientOrganizationUpdate) => Promise<void>;
  onProvisionSuperadmin?: (client: ClientOrganization, action: 'provision' | 'reset') => Promise<{
    email: string;
    temporary_password: string;
    email_status: 'sent' | 'not_configured' | 'delivery_failed';
  }>;
}

const fieldStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid var(--border-dim)',
  borderRadius: 10,
  background: 'var(--surface-2)',
  color: 'var(--text-primary)',
  fontSize: 13,
};

function EditProfileDialog({
  client,
  busy,
  onClose,
  onSave,
}: {
  client: ClientOrganization;
  busy: boolean;
  onClose: () => void;
  onSave: (updates: ClientOrganizationUpdate) => Promise<void>;
}) {
  const [name, setName] = useState(client.name);
  const [description, setDescription] = useState(client.description);
  const [clientType, setClientType] = useState(client.client_type);
  const [deploymentModel, setDeploymentModel] = useState(client.deployment_model);
  const [contactName, setContactName] = useState(client.primary_contact_name);
  const [contactEmail, setContactEmail] = useState(client.primary_contact_email);
  const [superadminName, setSuperadminName] = useState(client.superadmin_name);
  const [superadminEmail, setSuperadminEmail] = useState(client.superadmin_email);
  const [error, setError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await onSave({
        name,
        description,
        client_type: clientType,
        deployment_model: deploymentModel,
        primary_contact_name: contactName,
        primary_contact_email: contactEmail,
        superadmin_name: superadminName,
        superadmin_email: superadminEmail,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save this client profile.');
    }
  };

  return (
    <div className="overlay open" role="presentation" onClick={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <form className="overlay-content" onSubmit={submit} aria-labelledby="edit-client-title">
        <button type="button" className="overlay-close" onClick={onClose} aria-label="Close">&times;</button>
        <h2 id="edit-client-title" className="overlay-title">Edit client profile</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Client name
            <input required minLength={2} maxLength={128} value={name} onChange={(event) => setName(event.target.value)} style={fieldStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Client type
            <select value={clientType} onChange={(event) => setClientType(event.target.value)} style={fieldStyle}>
              <option value="enterprise">Enterprise</option>
              <option value="government">Government / public institution</option>
              <option value="institution">Institution</option>
              <option value="mssp">MSSP / managed security provider</option>
              {!['enterprise', 'government', 'institution', 'mssp'].includes(clientType) && <option value={clientType}>{clientType}</option>}
            </select>
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Delivery model
            <select value={deploymentModel} onChange={(event) => setDeploymentModel(event.target.value as ClientOrganization['deployment_model'])} style={fieldStyle}>
              <option value="saas">Managed SaaS</option>
              <option value="on_premises">On-premises deployment</option>
            </select>
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Primary contact
            <input required minLength={2} maxLength={128} value={contactName} onChange={(event) => setContactName(event.target.value)} style={fieldStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Contact email
            <input required type="email" maxLength={254} value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} style={fieldStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Designated client superadmin
            <input required minLength={2} maxLength={128} value={superadminName} onChange={(event) => setSuperadminName(event.target.value)} style={fieldStyle} />
          </label>
          <label style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Superadmin email
            <input required type="email" maxLength={254} value={superadminEmail} onChange={(event) => setSuperadminEmail(event.target.value)} style={fieldStyle} />
          </label>
          <label style={{ gridColumn: '1 / -1', color: 'var(--text-secondary)', fontSize: 12 }}>
            Profile notes
            <textarea maxLength={4000} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} style={{ ...fieldStyle, resize: 'vertical' }} />
          </label>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          Client-side access setup is pending. This form does not configure the client’s roles or tenant hierarchy.
        </p>
        {error && <div className="login-error">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn-mini" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-mini primary" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button>
        </div>
      </form>
    </div>
  );
}

export default function ClientPortfolio({
  clients,
  mode,
  busyId,
  loading,
  loadError,
  onReload,
  onCreateProfile,
  onChangeStatus,
  onSaveProfile,
  onProvisionSuperadmin,
}: Props) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [editing, setEditing] = useState<ClientOrganization | null>(null);
  const [invitingSuperadmin, setInvitingSuperadmin] = useState<ClientOrganization | null>(null);
  const [superadminAction, setSuperadminAction] = useState<'provision' | 'reset'>('provision');
  const [customStatusClient, setCustomStatusClient] = useState<string | null>(null);
  const [customStatus, setCustomStatus] = useState('');
  const [customStatusError, setCustomStatusError] = useState('');

  const filteredClients = useMemo(() => clients.filter((client) => {
    const query = search.trim().toLowerCase();
    const matchesText = !query || [
      client.name,
      client.identifier,
      client.client_type,
      client.primary_contact_email,
    ].some((value) => value.toLowerCase().includes(query));
    return matchesText && (statusFilter === 'all' || client.status === statusFilter);
  }), [clients, search, statusFilter]);

  const profileCount = clients.length;
  const activeCount = clients.filter((client) => client.status === 'active').length;
  const draftCount = clients.filter((client) => client.status === 'draft').length;

  const saveCustomStatus = async (client: ClientOrganization) => {
    const nextStatus = customStatus.trim();
    if (!/^[a-zA-Z0-9][a-zA-Z0-9 _-]{1,63}$/.test(nextStatus)) {
      setCustomStatusError('Use 2–64 letters, numbers, spaces, hyphens, or underscores.');
      return;
    }
    setCustomStatusError('');
    try {
      await onChangeStatus(client, nextStatus);
      setCustomStatus('');
      setCustomStatusClient(null);
    } catch (reason) {
      setCustomStatusError(reason instanceof Error ? reason.message : 'Could not update client status.');
    }
  };

  return (
    <section className="provider-portfolio">
      {loading ? (
        <div className="provider-state-card" role="status">
          <span className="provider-spinner" aria-hidden="true" />
          Loading client profiles…
        </div>
      ) : loadError ? (
        <div className="provider-state-card provider-state-error" role="alert">
          <div>
            <h2>Client profiles could not be loaded</h2>
            <p>{loadError}</p>
          </div>
          <button type="button" className="provider-secondary-button" onClick={onReload}>Try again</button>
        </div>
      ) : mode === 'profiles' ? (
        <>
          <div className="provider-metric-grid">
            {[
              { label: 'Client profiles', value: profileCount, detail: 'Organizations registered' },
              { label: 'Active clients', value: activeCount, detail: 'Ready for client onboarding' },
              { label: 'Draft profiles', value: draftCount, detail: 'Awaiting activation' },
            ].map((metric) => (
              <article key={metric.label} className="provider-metric-card">
                <span className="provider-metric-label">{metric.label}</span>
                <strong className="provider-metric-value">{metric.value}</strong>
                <span className="provider-metric-detail">{metric.detail}</span>
              </article>
            ))}
          </div>
          {clients.length === 0 ? (
            <div className="provider-empty-state">
              <span className="provider-empty-icon" aria-hidden="true">+</span>
              <span className="provider-page-eyebrow">Getting started</span>
              <h2>Add your first client organization</h2>
              <p>Create a client profile to record its contacts and delivery model. Tenant structure and scoped access are configured separately by the client administrator.</p>
              {onCreateProfile && (
                <button type="button" className="provider-create-button" onClick={onCreateProfile}>
                  <span aria-hidden="true">+</span>
                  Create client profile
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="provider-list-toolbar">
                <div>
                  <h2>Client directory</h2>
                  <p>Search and manage organization profiles.</p>
                </div>
                <input
                  type="search"
                  aria-label="Search client profiles"
                  placeholder="Search by name, ID, type, or contact"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="provider-search-input"
                  style={fieldStyle}
                />
              </div>
              <div className="provider-table-card">
                <table className="users-table provider-table">
                  <thead>
                    <tr>
                      <th>Client</th>
                      <th>Type &amp; delivery</th>
                      <th>Client contacts</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredClients.length === 0 ? (
                      <tr><td colSpan={5} className="provider-table-empty">No clients match your search.</td></tr>
                    ) : filteredClients.map((client) => (
                      <tr key={client.id}>
                        <td>
                          <strong>{client.name}</strong>
                          <div className="provider-table-secondary"><code>{client.identifier}</code></div>
                          {client.description && <div title={client.description} className="provider-description">{client.description}</div>}
                        </td>
                        <td>
                          <span className="provider-capitalize">{client.client_type.replace(/_/g, ' ')}</span>
                          <div className="provider-table-secondary">
                            {client.deployment_model === 'saas' ? 'Managed SaaS' : 'On-premises'}
                          </div>
                        </td>
                        <td>
                          <div>{client.primary_contact_name}</div>
                          <div className="provider-table-secondary">{client.primary_contact_email}</div>
                          <div className="provider-superadmin">Superadmin: {client.superadmin_name}</div>
                          <div className="provider-table-secondary">{client.superadmin_email}</div>
                          <div className="provider-access-pending">
                            {client.access_setup_status === 'pending_superadmin_setup'
                              ? 'Superadmin account setup pending'
                              : 'Workspace setup pending'}
                          </div>
                        </td>
                        <td>
                          <span className={`client-status-badge client-status-${client.status.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>{client.status}</span>
                        </td>
                        <td className="provider-table-actions">
                          <button type="button" className="provider-secondary-button" onClick={() => setEditing(client)}>Edit profile</button>
                          {onProvisionSuperadmin && (
                            <button
                              type="button"
                              className="provider-secondary-button"
                              disabled={client.status !== 'active' || busyId === client.id}
                              title={client.status !== 'active' ? 'Activate this client profile before managing its superadmin account.' : undefined}
                              onClick={() => {
                                setSuperadminAction(
                                  client.access_setup_status === 'pending_client_workspace' ? 'reset' : 'provision',
                                );
                                setInvitingSuperadmin(client);
                              }}
                            >
                              {client.access_setup_status === 'pending_client_workspace'
                                ? 'Reset superadmin password'
                                : 'Provision superadmin'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="provider-list-toolbar">
            <div>
              <h2>Client status</h2>
              <p>Review and update each client organization’s lifecycle state.</p>
            </div>
            <input
              type="search"
              aria-label="Search client statuses"
              placeholder="Search clients…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="provider-search-input"
              style={{ ...fieldStyle, maxWidth: 360 }}
            />
          </div>
          <div className="provider-status-filter">
            <label htmlFor="client-status-filter">Filter by status</label>
            <select id="client-status-filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="provider-search-input">
              <option value="all">All statuses</option>
              {Array.from(new Set(clients.map((client) => client.status))).map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </div>
          <div className="provider-table-card">
            <table className="users-table provider-table provider-status-table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Current status</th>
                  <th>Update status</th>
                </tr>
              </thead>
              <tbody>
                {filteredClients.length === 0 ? (
                  <tr><td colSpan={3} className="provider-table-empty">No client profiles match these filters.</td></tr>
                ) : filteredClients.map((client) => (
                  <tr key={client.id}>
                    <td>
                      <strong>{client.name}</strong>
                      <div className="provider-table-secondary"><code>{client.identifier}</code></div>
                    </td>
                    <td>
                      <span className={`client-status-badge client-status-${client.status.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>{client.status}</span>
                    </td>
                    <td className="provider-status-controls">
                      <div>
                        <select
                          aria-label={`Set status for ${client.name}`}
                          value={client.status}
                          disabled={busyId === client.id}
                          onChange={(event) => { void onChangeStatus(client, event.target.value); }}
                          className="provider-search-input"
                        >
                          {client.status_options.map((status) => <option key={status} value={status}>{status}</option>)}
                        </select>
                        <button type="button" className="provider-secondary-button" onClick={() => { setCustomStatusClient(client.id); setCustomStatus(''); setCustomStatusError(''); }}>
                          Add status
                        </button>
                      </div>
                      {customStatusClient === client.id && (
                        <div className="provider-status-custom">
                          <input
                            aria-label={`New status for ${client.name}`}
                            value={customStatus}
                            onChange={(event) => setCustomStatus(event.target.value)}
                            maxLength={64}
                            placeholder="Custom status"
                            className="provider-search-input"
                          />
                          <button type="button" className="provider-create-button" disabled={busyId === client.id} onClick={() => { void saveCustomStatus(client); }}>Save</button>
                          <button type="button" className="provider-secondary-button" onClick={() => setCustomStatusClient(null)}>Cancel</button>
                        </div>
                      )}
                      {customStatusClient === client.id && customStatusError && <div className="login-error" role="alert">{customStatusError}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {editing && (
        <EditProfileDialog
          client={editing}
          busy={busyId === editing.id}
          onClose={() => setEditing(null)}
          onSave={async (updates) => {
            await onSaveProfile(editing.id, updates);
            setEditing(null);
          }}
        />
      )}
      {invitingSuperadmin && onProvisionSuperadmin && (
        <ClientSuperadminProvisionDialog
          client={invitingSuperadmin}
          action={superadminAction}
          busy={busyId === invitingSuperadmin.id}
          onClose={() => setInvitingSuperadmin(null)}
          onProvision={() => onProvisionSuperadmin(invitingSuperadmin, superadminAction)}
        />
      )}
    </section>
  );
}
