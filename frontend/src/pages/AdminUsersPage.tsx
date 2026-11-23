import { useEffect, useState } from 'react';
import {
  createClientOrganization,
  fetchClientOrganizations,
  provisionClientSuperadmin,
  rotateClientSuperadminPassword,
  updateClientOrganization,
} from '../api/admin';
import type {
  ClientOrganization,
  ClientOrganizationCreate,
  ClientOrganizationUpdate,
} from '../types';
import ClientPortfolio from '../components/multiTenant/ClientPortfolio';
import ClientProfileForm from '../components/multiTenant/ClientProfileForm';

export default function AdminUsersPage() {
  const [clients, setClients] = useState<ClientOrganization[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState<string>();
  const [notice, setNotice] = useState('');
  const [view, setView] = useState<'profiles' | 'create' | 'status'>('profiles');

  const loadClients = async () => {
    setLoading(true);
    setLoadError('');
    try {
      setClients(await fetchClientOrganizations());
    } catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : 'Failed to load client profiles.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadClients();
  }, []);

  const createClient = async (payload: ClientOrganizationCreate) => {
    setBusy(true);
    try {
      const created = await createClientOrganization(payload);
      setClients((items) => [created, ...items]);
      setNotice(`Client profile "${created.name}" created in draft status.`);
      setView('profiles');
    } finally {
      setBusy(false);
    }
  };

  const updateClient = async (clientId: string, updates: ClientOrganizationUpdate) => {
    setBusyId(clientId);
    try {
      const updated = await updateClientOrganization(clientId, updates);
      setClients((items) => items.map((item) => item.id === clientId ? updated : item));
      setNotice(`Client profile "${updated.name}" updated.`);
    } finally {
      setBusyId(undefined);
    }
  };

  const changeStatus = async (client: ClientOrganization, status: string) => {
    await updateClient(client.id, { status });
  };

  const manageSuperadmin = async (client: ClientOrganization, action: 'provision' | 'reset') => {
    setBusyId(client.id);
    try {
      const result = action === 'reset'
        ? await rotateClientSuperadminPassword(client.id)
        : await provisionClientSuperadmin(client.id);
      setClients((items) => items.map((item) => item.id === client.id ? result.client : item));
      setNotice(
        action === 'reset'
          ? `The temporary administrator password was reset for ${client.name}.`
          : `An administrator account was created for ${client.name}.`,
      );
      return {
        email: result.email,
        temporary_password: result.temporary_password,
        email_status: result.email_status,
      };
    } catch (reason) {
      const detail = (reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      throw new Error(detail || (reason instanceof Error ? reason.message : 'Could not provision the administrator.'));
    } finally {
      setBusyId(undefined);
    }
  };

  return (
    <div className="provider-admin-layout">
      <aside className="provider-admin-sidebar" aria-label="Client profile navigation">
        <div className="provider-sidebar-heading">
          <span className="provider-sidebar-kicker">Workspace</span>
          <strong>Client profiles</strong>
        </div>
        <nav className="provider-sidebar-nav" aria-label="Profile sections">
          {([
            ['profiles', 'All profiles', '01'],
            ['create', 'Create profile', '02'],
            ['status', 'Client status', '03'],
          ] as const).map(([key, label, number]) => (
            <button
              key={key}
              type="button"
              className="provider-nav-button"
              aria-current={view === key ? 'page' : undefined}
              onClick={() => setView(key)}
            >
              <span className="provider-nav-number" aria-hidden="true">{number}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="provider-admin-content">
        {notice && <div role="status" className="provider-notice">{notice}</div>}
        {view === 'create' ? (
          <ClientProfileForm
            busy={busy}
            onComplete={createClient}
            onCancel={() => setView('profiles')}
          />
        ) : (
          <ClientPortfolio
            clients={clients}
            mode={view}
            busyId={busyId}
            loading={loading}
            loadError={loadError}
            onReload={() => { void loadClients(); }}
            onCreateProfile={() => setView('create')}
            onChangeStatus={changeStatus}
            onSaveProfile={updateClient}
            onProvisionSuperadmin={manageSuperadmin}
          />
        )}
      </main>
    </div>
  );
}
