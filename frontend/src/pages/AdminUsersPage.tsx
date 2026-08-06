import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Chip from '../components/dashboard/Chip';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { fetchUsers, createUser, updateUser, deleteUser, AdminUser } from '../api/admin';
import type { Tone } from '../data/mappers';

const ROLE_OPTIONS = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'admin'];

const ROLE_TONE: Record<string, Tone> = {
  exec: 'severe',
  soc: 'med',
  appsec: 'high',
  dbsec: 'ok',
  compliance: 'closed',
  sre: 'half',
  admin: 'severe',
};

interface FormState {
  email: string;
  display_name: string;
  password: string;
  roles: string[];
  is_active: boolean;
}

const EMPTY_FORM: FormState = {
  email: '',
  display_name: '',
  password: '',
  roles: [],
  is_active: true,
};

type Modal = { mode: 'create' } | { mode: 'edit'; user: AdminUser } | null;

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString();
}

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const users = useApi(() => fetchUsers());
  const [modal, setModal] = useState<Modal>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const items = users.data?.items || [];

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setError('');
    setModal({ mode: 'create' });
  };

  const openEdit = (user: AdminUser) => {
    setForm({
      email: user.email,
      display_name: user.display_name || '',
      password: '',
      roles: [...user.roles],
      is_active: user.is_active,
    });
    setError('');
    setModal({ mode: 'edit', user });
  };

  const toggleRole = (role: string) => {
    setForm((f) => ({
      ...f,
      roles: f.roles.includes(role) ? f.roles.filter((r) => r !== role) : [...f.roles, role],
    }));
  };

  const submit = async () => {
    if (!form.roles.length) {
      setError('Select at least one role.');
      return;
    }
    if (modal?.mode === 'create' && !form.password) {
      setError('Set an initial password (min 8 characters).');
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (modal?.mode === 'create') {
        await createUser({
          email: form.email,
          display_name: form.display_name || undefined,
          password: form.password,
          roles: form.roles,
        });
        setNotice(`Created ${form.email}`);
      } else if (modal?.mode === 'edit' && modal.user) {
        await updateUser(modal.user.id, {
          display_name: form.display_name || undefined,
          roles: form.roles,
          is_active: form.is_active,
          password: form.password || undefined,
        });
        setNotice(`Updated ${modal.user.email}`);
      }
      setModal(null);
      users.refresh();
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Operation failed.'
      );
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (user: AdminUser) => {
    if (!window.confirm(`Delete ${user.email}? This cannot be undone.`)) return;
    setError('');
    try {
      await deleteUser(user.id);
      setNotice(`Deleted ${user.email}`);
      users.refresh();
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Delete failed.'
      );
    }
  };

  return (
    <div className="dash">
      <DashHeader
        title="User Access & RBAC"
        subtitle="Create and manage users, assign roles and access"
        badge={{ label: 'rbac', color: 'var(--violet)', bg: 'var(--violet-dim)' }}
        consolidatedTag="identity · roles · least privilege"
        onExplain={() => {}}
        onLayman={() => {}}
      >
        <button className="btn-add" onClick={openCreate}>+ New User</button>
      </DashHeader>

      {notice && (
        <div className="dash-banner ok" onClick={() => setNotice('')}>
          {notice}
        </div>
      )}
      {error && (
        <div className="dash-banner err" onClick={() => setError('')}>
          {error}
        </div>
      )}

      {users.loading ? (
        <div className="dash-loading"><span className="spin" />Loading users…</div>
      ) : users.error ? (
        <div className="dash-error">{users.error}</div>
      ) : (
        <div className="panel users-panel">
          <div className="panel-b" style={{ padding: 0 }}>
            <table className="users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Roles</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.length ? items.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="users-name">{u.display_name || u.email.split('@')[0]}</div>
                      <div className="users-email">{u.email}</div>
                    </td>
                    <td>
                      <div className="users-roles">
                        {u.roles.map((r) => (
                          <Chip key={r} tone={ROLE_TONE[r] || 'med'}>{r}</Chip>
                        ))}
                      </div>
                    </td>
                    <td>
                      <Chip tone={u.is_active ? 'ok' : 'closed'}>{u.is_active ? 'active' : 'disabled'}</Chip>
                    </td>
                    <td className="users-created">{formatDate(u.created_at)}</td>
                    <td>
                      <div className="users-actions">
                        <button className="btn-mini" onClick={() => openEdit(u)}>Edit</button>
                        {u.id !== me?.sub && (
                          <button className="btn-mini danger" onClick={() => handleDelete(u)}>Delete</button>
                        )}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={5}><div className="panel-empty">No users found.</div></td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modal && (
        <div className="overlay open" onClick={(e) => { if (e.target === e.currentTarget) setModal(null); }}>
          <div className="overlay-content">
            <button type="button" className="overlay-close" onClick={() => setModal(null)} aria-label="Close">&times;</button>
            <div className="overlay-title">
              {modal.mode === 'create' ? 'Create User' : `Edit ${modal.user.email}`}
            </div>
            <div className="form-field">
              <label className="form-label" htmlFor="uemail">Email address</label>
              <input
                type="email"
                id="uemail"
                className="form-input"
                value={form.email}
                disabled={modal.mode === 'edit'}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@example.com"
              />
            </div>
            <div className="form-row">
              <div className="form-field">
                <label className="form-label" htmlFor="uname">Display name</label>
                <input
                  type="text"
                  id="uname"
                  className="form-input"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div className="form-field">
                <label className="form-label" htmlFor="upw">
                  {modal.mode === 'edit' ? 'Reset password (leave blank to keep)' : 'Initial password'}
                </label>
                <input
                  type="password"
                  id="upw"
                  className="form-input"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Min 8 characters"
                  autoComplete="new-password"
                />
              </div>
            </div>
            <div className="form-field">
              <span className="form-label">Roles</span>
              <div className="role-check-list">
                {ROLE_OPTIONS.map((role) => {
                  const checked = form.roles.includes(role);
                  return (
                    <button
                      key={role}
                      type="button"
                      className={`role-check${checked ? ' checked' : ''}`}
                      onClick={() => toggleRole(role)}
                    >
                      <span className="role-check-box">{checked ? '✓' : ''}</span>
                      {role}
                    </button>
                  );
                })}
              </div>
            </div>
            {modal.mode === 'edit' && (
              <div className="form-field">
                <label className="form-check">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  <span>Account active</span>
                </label>
              </div>
            )}
            {error && <div className="login-error">{error}</div>}
            <div className="modal-actions">
              <button className="btn-mini" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn-mini primary" onClick={submit} disabled={busy}>
                {busy ? 'Saving…' : modal.mode === 'create' ? 'Create User' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
