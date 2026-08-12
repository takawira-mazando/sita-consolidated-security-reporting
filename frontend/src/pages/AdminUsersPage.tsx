import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Chip from '../components/dashboard/Chip';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { fetchUsers, createUser, updateUser, deleteUser, AdminUser } from '../api/admin';
import { fetchTenancy, TenancyDepartment } from '../api/auth';
import type { Tone } from '../data/mappers';

const ROLE_OPTIONS = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'admin', 'transversal-admin', 'dept-admin', 'branch-admin', 'province-soc-lead', 'province-dept-admin', 'local-appsec'];
const DEPARTMENT_ROLES = new Set(['soc', 'appsec', 'dbsec', 'dept-admin', 'branch-admin', 'province-soc-lead', 'province-dept-admin', 'local-appsec']);
const PROVINCIAL_ROLES = new Set(['province-soc-lead', 'province-dept-admin', 'local-appsec']);
const BRANCH_REQUIRED_ROLES = new Set(['branch-admin']);

// Mirrors backend GRANTABLE_ROLES: roles a delegated admin may grant, by tier.
const GRANTABLE_ROLES: Record<string, string[]> = {
  'transversal-admin': ['soc', 'appsec', 'dbsec', 'province-soc-lead', 'local-appsec', 'dept-admin', 'branch-admin', 'province-dept-admin'],
  'dept-admin': ['soc', 'appsec', 'dbsec', 'province-soc-lead', 'local-appsec', 'branch-admin'],
  'province-dept-admin': ['soc', 'appsec', 'dbsec', 'province-soc-lead', 'local-appsec'],
  'branch-admin': ['soc', 'appsec', 'dbsec', 'province-soc-lead', 'local-appsec'],
};

const ROLE_TONE: Record<string, Tone> = {
  exec: 'severe',
  soc: 'med',
  appsec: 'high',
  dbsec: 'ok',
  compliance: 'closed',
  sre: 'half',
  admin: 'severe',
  'transversal-admin': 'severe',
  'dept-admin': 'severe',
  'branch-admin': 'high',
  'province-soc-lead': 'med',
  'province-dept-admin': 'severe',
  'local-appsec': 'high',
};

interface FormState {
  email: string;
  display_name: string;
  password: string;
  roles: string[];
  department_ids: string[];
  branch_ids: string[];
  province_ids: string[];
  is_active: boolean;
}

const EMPTY_FORM: FormState = {
  email: '',
  display_name: '',
  password: '',
  roles: [],
  department_ids: [],
  branch_ids: [],
  province_ids: [],
  is_active: true,
};

type Modal = { mode: 'create' } | { mode: 'edit'; user: AdminUser } | null;

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString();
}

interface BranchRef {
  name: string;
  department_id: string;
}

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const users = useApi(() => fetchUsers());
  const tenancy = useApi(() => fetchTenancy());
  const [modal, setModal] = useState<Modal>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const items = users.data?.items || [];
  const departments: TenancyDepartment[] = tenancy.data?.departments || [];
  const counts = tenancy.data?.counts;

  const myDepts = me?.department_ids || [];
  const myBranches = me?.branch_ids || [];
  const myProvinces = me?.province_ids || [];
  const isSystemAdmin = me?.roles?.includes('admin');
  const isScopedAdmin = !isSystemAdmin && (me?.roles?.some((r) => ['dept-admin', 'branch-admin', 'province-dept-admin'].includes(r)) || myDepts.length > 0);
  const grantableOptions = isSystemAdmin || me?.roles?.includes('sre')
    ? ROLE_OPTIONS
    : Array.from(new Set((me?.roles || []).flatMap((r) => GRANTABLE_ROLES[r] || [])));
  const pickable = isScopedAdmin
    ? departments.filter((d) => myDepts.length === 0 || myDepts.includes(d.id))
    : departments;
  const provinces = tenancy.data?.provinces || [];
  const pickableProvinces = isScopedAdmin
    ? provinces.filter((p) => myProvinces.length === 0 || myProvinces.includes(p.id))
    : provinces;
  const pickableBranches = (d: TenancyDepartment) => {
    if (!isScopedAdmin || myBranches.length === 0) return d.branches;
    if (!myDepts.includes(d.id)) return [];
    return d.branches.filter((b) => myBranches.includes(b.id));
  };

  const branchMap = new Map<string, BranchRef>();
  pickable.forEach((d) => {
    d.branches.forEach((b) => branchMap.set(b.id, { name: b.name, department_id: d.id }));
  });

  const deptName = (id?: string | null) => departments.find((d) => d.id === id)?.name || '—';
  const provinceName = (id?: string | null) => provinces.find((p) => p.id === id)?.name || '—';
  const branchName = (id: string) => branchMap.get(id)?.name || '—';

  const branchGroups = pickable.filter((d) => form.department_ids.includes(d.id));

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
      department_ids: [...(user.department_ids || [])],
      branch_ids: [...(user.branch_ids || [])],
      province_ids: [...(user.province_ids || [])],
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

  const toggleDepartment = (id: string) => {
    setForm((f) => {
      const next = f.department_ids.includes(id)
        ? f.department_ids.filter((d) => d !== id)
        : [...f.department_ids, id];
      const orphaned = f.branch_ids.filter((b) => branchMap.get(b)?.department_id !== id);
      return { ...f, department_ids: next, branch_ids: orphaned };
    });
  };

  const toggleProvince = (id: string) => {
    setForm((f) => {
      const next = f.province_ids.includes(id)
        ? f.province_ids.filter((p) => p !== id)
        : [...f.province_ids, id];
      return { ...f, province_ids: next };
    });
  };

  const toggleBranch = (id: string) => {
    setForm((f) => ({
      ...f,
      branch_ids: f.branch_ids.includes(id)
        ? f.branch_ids.filter((b) => b !== id)
        : [...f.branch_ids, id],
    }));
  };

  const needsDepartment = form.roles.some((r) => DEPARTMENT_ROLES.has(r));
  const needsProvince = form.roles.some((r) => PROVINCIAL_ROLES.has(r));
  const needsBranch = form.roles.some((r) => BRANCH_REQUIRED_ROLES.has(r));

  const submit = async () => {
    if (!form.roles.length) {
      setError('Select at least one role.');
      return;
    }
    if (needsDepartment && !form.department_ids.length && !form.province_ids.length) {
      setError('Department-scoped roles require at least one assigned department or province.');
      return;
    }
    if (needsProvince && !form.province_ids.length && !form.department_ids.length) {
      setError('Provincial roles (province-soc-lead/province-dept-admin/local-appsec) require at least one assigned province or department.');
      return;
    }
    if (needsBranch && !form.branch_ids.length) {
      setError('Role branch-admin requires at least one assigned branch.');
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
          department_ids: form.department_ids,
          branch_ids: form.branch_ids,
          province_ids: form.province_ids,
        });
        setNotice(`Created ${form.email}`);
      } else if (modal?.mode === 'edit' && modal.user) {
        await updateUser(modal.user.id, {
          display_name: form.display_name || undefined,
          roles: form.roles,
          department_ids: form.department_ids,
          branch_ids: form.branch_ids,
          province_ids: form.province_ids,
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
        subtitle={
          counts
            ? `National + provincial estate — ${counts.departments} national departments · ${counts.provincial_departments ?? '—'} provincial · ${counts.branches} branches`
            : 'Create and manage users, assign roles and access'
        }
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

      {users.loading || tenancy.loading ? (
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
                  <th>Tenant scope</th>
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
                      {(u.province_ids || []).length ? (
                        <div className="users-email">
                          {(u.province_ids || []).map((id) => (
                            <div key={id} style={{ marginBottom: 2 }}>
                              {provinceName(id)}
                            </div>
                          ))}
                        </div>
                      ) : (u.department_ids || []).length ? (
                        <div className="users-email">
                          {(u.department_ids || []).map((id) => {
                            const branchNames = (u.branch_ids || [])
                              .filter((b) => branchMap.get(b)?.department_id === id)
                              .map(branchName);
                            return (
                              <div key={id} style={{ marginBottom: 2 }}>
                                {deptName(id)}
                                {branchNames.length > 0 && (
                                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                    ↳ {branchNames.join(', ')}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="users-email">National (whole estate)</div>
                      )}
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
                  <tr><td colSpan={6}><div className="panel-empty">No users found.</div></td></tr>
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
                {grantableOptions.map((role) => {
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
              {needsDepartment && (
                <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                  soc / appsec / dbsec / dept-admin / branch-admin / provincial roles require at least one assigned department or province.
                </div>
              )}
            </div>
            <div className="form-field">
              <span className="form-label">Provinces (provincial tenant scope)</span>
              <div className="role-check-list">
                {pickableProvinces.length ? pickableProvinces.map((p) => {
                  const checked = form.province_ids.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      type="button"
                      className={`role-check${checked ? ' checked' : ''}`}
                      onClick={() => toggleProvince(p.id)}
                    >
                      <span className="role-check-box">{checked ? '✓' : ''}</span>
                      {p.name}
                      <span className="scope-count">{p.department_count}</span>
                    </button>
                  );
                }) : (
                  <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                    Loading provincial hierarchy…
                  </div>
                )}
              </div>
              <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                Province scope expands to every provincial department inside the province. province-soc-lead / province-dept-admin / local-appsec must select at least one.
              </div>
            </div>
            <div className="form-field">
              <span className="form-label">Departments (tenant scope)</span>
              <div className="role-check-list">
                {pickable.length ? pickable.map((d) => {
                  const checked = form.department_ids.includes(d.id);
                  return (
                    <button
                      key={d.id}
                      type="button"
                      className={`role-check${checked ? ' checked' : ''}`}
                      onClick={() => toggleDepartment(d.id)}
                    >
                      <span className="role-check-box">{checked ? '✓' : ''}</span>
                      {d.name}
                      <span className="scope-count">{d.branch_count}</span>
                    </button>
                  );
                }) : (
                  <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                    Loading national hierarchy…
                  </div>
                )}
              </div>
              <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                Empty selection = National (whole estate). soc / appsec / dbsec / dept-admin / branch-admin must select at least one.
              </div>
            </div>
            {branchGroups.length > 0 && (
              <div className="form-field">
                <span className="form-label">Branches (optional narrowing)</span>
                {branchGroups.map((d) => {
                  const branches = pickableBranches(d);
                  if (!branches.length) return null;
                  return (
                    <div key={d.id} className="branch-group">
                      <div className="branch-group-title">{d.name}</div>
                      <div className="role-check-list">
                        {branches.map((b) => {
                          const checked = form.branch_ids.includes(b.id);
                          return (
                            <button
                              key={b.id}
                              type="button"
                              className={`role-check${checked ? ' checked' : ''}`}
                              onClick={() => toggleBranch(b.id)}
                            >
                              <span className="role-check-box">{checked ? '✓' : ''}</span>
                              {b.name}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
                <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                  Empty selection = all branches within the assigned departments.
                </div>
              </div>
            )}
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
