import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  fetchManagedTenantMembers,
  searchManagedTenantEmployees,
  TenantDirectoryEmployee,
  updateManagedTenantMembers,
} from '../../api/admin';
import type {
  ManagedTenantMembers,
} from '../../api/admin';
import type { TenantAccessAssignment, TenantRbacAssignmentInput } from '../../types';

const WORKSPACE_KEY = 'platform_active_tenant_workspace';

function errorMessage(error: unknown): string {
  const detail = (error as {
    response?: { data?: { detail?: unknown } };
  })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'The request could not be completed.';
}

function scopeLabel(scopeId: string | null, workspace: ManagedTenantMembers): string {
  if (!scopeId) return 'Entire tenant';
  const level = workspace.hierarchy_levels.find((item) => item.key === scopeId);
  return level ? `All ${level.plural_label || `${level.label}s`}` : 'Unavailable tier';
}

function statusLabel(status: TenantAccessAssignment['access_status']): string {
  switch (status) {
    case 'active':
      return 'Account active';
    case 'account_disabled':
      return 'Account disabled';
    case 'pending_first_sign_in':
      return 'Pending first sign-in';
    default:
      return 'Identity integration required';
  }
}

export default function TenantMemberAdmin() {
  const [workspaceId, setWorkspaceId] = useState(
    () => localStorage.getItem(WORKSPACE_KEY) || '',
  );
  const [workspace, setWorkspace] = useState<ManagedTenantMembers | null>(null);
  const [assignments, setAssignments] = useState<TenantAccessAssignment[]>([]);
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [employees, setEmployees] = useState<TenantDirectoryEmployee[]>([]);
  const [directoryName, setDirectoryName] = useState('');
  const [selectedEmployeeEmail, setSelectedEmployeeEmail] = useState('');
  const [scopeId, setScopeId] = useState('');
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const selectedEmployee = employees.find((employee) => employee.email === selectedEmployeeEmail);
  const scopeOptions = useMemo(() => {
    if (!workspace) return [];
    const options: Array<{ value: string; label: string }> = [];
    if (workspace.allowed_scope_level_keys.includes('root')) {
      options.push({ value: '', label: 'Entire tenant' });
    }
    workspace.hierarchy_levels
      .filter((level) => workspace.allowed_scope_level_keys.includes(level.key))
      .forEach((level) => options.push({
        value: level.key,
        label: `All ${level.plural_label || `${level.label}s`}`,
      }));
    return options;
  }, [workspace]);

  const rolesAtScope = useMemo(() => {
    const key = scopeId || 'root';
    return (workspace?.roles ?? []).filter(
      (role) => !role.scope_level_keys?.length || role.scope_level_keys.includes(key),
    );
  }, [scopeId, workspace]);

  useEffect(() => {
    const syncWorkspace = () => setWorkspaceId(localStorage.getItem(WORKSPACE_KEY) || '');
    window.addEventListener('tenant-workspace-change', syncWorkspace);
    return () => window.removeEventListener('tenant-workspace-change', syncWorkspace);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    if (!workspaceId) {
      setWorkspace(null);
      setAssignments([]);
      setError('No tenant workspace is selected for this account.');
      setLoading(false);
      return () => { cancelled = true; };
    }
    fetchManagedTenantMembers(workspaceId)
      .then((result) => {
        if (cancelled) return;
        setWorkspace(result);
        setAssignments(result.assignments);
        setScopeId((current) => (
          scopeOptionsFor(result).some((option) => option.value === current)
            ? current
            : scopeOptionsFor(result)[0]?.value ?? ''
        ));
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(errorMessage(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [workspaceId]);

  const searchEmployees = async (event: FormEvent) => {
    event.preventDefault();
    if (!workspaceId || employeeSearch.trim().length < 2) return;
    setError('');
    setNotice('');
    try {
      const result = await searchManagedTenantEmployees(workspaceId, employeeSearch.trim());
      setDirectoryName(result.directory_name);
      setEmployees(result.items);
      setSelectedEmployeeEmail('');
    } catch (searchError: unknown) {
      setError(errorMessage(searchError));
    }
  };

  const addAssignment = () => {
    if (!workspace || !selectedEmployee || roleIds.length === 0) return;
    const next: TenantAccessAssignment = {
      id: crypto.randomUUID(),
      email: selectedEmployee.email.toLowerCase(),
      display_name: selectedEmployee.display_name,
      role_ids: roleIds,
      scope_unit_id: scopeId || null,
      access_status: 'pending_first_sign_in',
    };
    setAssignments((current) => {
      const existing = current.findIndex(
        (assignment) => assignment.email.toLowerCase() === next.email
          && assignment.scope_unit_id === next.scope_unit_id,
      );
      if (existing < 0) return [...current, next];
      return current.map((assignment, index) => (
        index === existing
          ? { ...next, id: assignment.id, access_status: assignment.access_status }
          : assignment
      ));
    });
    setSelectedEmployeeEmail('');
    setRoleIds([]);
    setNotice('RBAC assignment staged. Save to apply it.');
  };

  const saveAssignments = async () => {
    if (!workspace) return;
    setSaving(true);
    setError('');
    setNotice('');
    const payload: TenantRbacAssignmentInput[] = assignments.map((assignment) => ({
      id: assignment.id,
      email: assignment.email,
      display_name: assignment.display_name,
      role_ids: assignment.role_ids,
      scope_unit_id: assignment.scope_unit_id,
    }));
    try {
      const result = await updateManagedTenantMembers(workspace.workspace_id, payload);
      setAssignments(result.assignments);
      setNotice('RBAC assignments saved.');
    } catch (saveError: unknown) {
      setError(errorMessage(saveError));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <main className="loading-screen">Loading tenant member access…</main>;
  }

  return (
    <main className="provider-admin-layout tenant-member-admin">
      <header className="provider-page-header">
        <div>
          <h1>Tenant member access</h1>
          <p>
            Manage RBAC roles within your assigned tier. Administrator access is granted separately by the organization.
          </p>
        </div>
      </header>
      {workspace && (
        <div className="client-tenant-directory-readiness">
          <strong>{workspace.workspace_name}</strong>
          <span>
            {' · '}
            {workspace.directory.status === 'enabled'
              ? `Directory enabled${directoryName || workspace.directory.name ? ` · ${directoryName || workspace.directory.name}` : ''}. Accounts are provisioned on first successful sign-in.`
              : 'Directory integration is unavailable. Employee search and first-sign-in provisioning are disabled.'}
          </span>
        </div>
      )}
      {error && <div className="provider-notice provider-state-error" role="alert">{error}</div>}
      {notice && <div className="provider-notice" role="status">{notice}</div>}

      {workspace && (
        <>
          <section className="client-tenant-panel">
            <h2>Grant RBAC roles</h2>
            <form className="tenant-member-search" onSubmit={searchEmployees}>
              <input
                className="client-tenant-input"
                aria-label="Search directory employees"
                placeholder="Search directory employees"
                value={employeeSearch}
                onChange={(event) => setEmployeeSearch(event.target.value)}
                minLength={2}
              />
              <button
                className="provider-secondary-button"
                type="submit"
                disabled={employeeSearch.trim().length < 2}
              >
                Search
              </button>
            </form>
            {employees.length > 0 && (
              <label className="client-tenant-field">
                Employee
                <select
                  className="client-tenant-input"
                  value={selectedEmployeeEmail}
                  onChange={(event) => setSelectedEmployeeEmail(event.target.value)}
                >
                  <option value="">Select an employee</option>
                  {employees.map((employee) => (
                    <option key={employee.email} value={employee.email}>
                      {employee.display_name} · {employee.email}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {selectedEmployee && (
              <div className="tenant-member-grant-form">
                <label className="client-tenant-field">
                  RBAC scope
                  <select
                    className="client-tenant-input"
                    value={scopeId}
                    onChange={(event) => {
                      setScopeId(event.target.value);
                      setRoleIds([]);
                    }}
                  >
                    {scopeOptions.map((option) => (
                      <option key={option.value || 'root'} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <fieldset className="client-tenant-fieldset">
                  <legend>Dashboard roles</legend>
                  {rolesAtScope.map((role) => (
                    <label className="client-tenant-checkbox" key={role.id}>
                      <input
                        type="checkbox"
                        checked={roleIds.includes(role.id)}
                        onChange={(event) => setRoleIds((current) => (
                          event.target.checked
                            ? [...current, role.id]
                            : current.filter((id) => id !== role.id)
                        ))}
                      />
                      <span>
                        <strong>{role.name}</strong>
                        <small>{role.cockpit_ids.join(' · ')}</small>
                      </span>
                    </label>
                  ))}
                  {rolesAtScope.length === 0 && (
                    <p className="client-tenant-empty-note">No RBAC roles are configured for this tier.</p>
                  )}
                </fieldset>
                <button
                  className="provider-create-button"
                  type="button"
                  onClick={addAssignment}
                  disabled={!roleIds.length}
                >
                  Add RBAC assignment
                </button>
              </div>
            )}
          </section>

          <section className="client-tenant-panel">
            <div className="tenant-member-list-heading">
              <div>
                <h2>RBAC assignments</h2>
                <p className="client-tenant-help">Scope is tier-wide and includes all units at that tier.</p>
              </div>
              <button
                className="provider-create-button"
                type="button"
                onClick={saveAssignments}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save RBAC assignments'}
              </button>
            </div>
            {assignments.length === 0 ? (
              <p className="client-tenant-empty-note">No RBAC assignments in your managed scope.</p>
            ) : (
              <ul className="client-tenant-item-list">
                {assignments.map((assignment) => (
                  <li className="client-tenant-item-card" key={assignment.id}>
                    <div className="client-tenant-item-heading">
                      <strong>{assignment.display_name}</strong>
                      <button
                        className="provider-secondary-button"
                        type="button"
                        onClick={() => setAssignments((current) => (
                          current.filter((item) => item.id !== assignment.id)
                        ))}
                      >
                        Remove RBAC access
                      </button>
                    </div>
                    <div className="client-tenant-item-meta">{assignment.email}</div>
                    <div>
                      {assignment.role_ids
                        .map((id) => workspace.roles.find((role) => role.id === id)?.name || id)
                        .join(', ')}
                      {' · '}
                      {scopeLabel(assignment.scope_unit_id, workspace)}
                    </div>
                    <span className="client-tenant-status">{statusLabel(assignment.access_status)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function scopeOptionsFor(workspace: ManagedTenantMembers): Array<{ value: string; label: string }> {
  const options: Array<{ value: string; label: string }> = [];
  if (workspace.allowed_scope_level_keys.includes('root')) {
    options.push({ value: '', label: 'Entire tenant' });
  }
  workspace.hierarchy_levels
    .filter((level) => workspace.allowed_scope_level_keys.includes(level.key))
    .forEach((level) => options.push({
      value: level.key,
      label: `All ${level.plural_label || `${level.label}s`}`,
    }));
  return options;
}
