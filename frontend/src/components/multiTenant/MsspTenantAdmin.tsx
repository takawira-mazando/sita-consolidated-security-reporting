import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  createMsspTenantWorkspace,
  fetchMsspCockpits,
  fetchMsspTenantWorkspaces,
  searchMsspWorkspaceEmployees,
  updateMsspTenantWorkspace,
} from '../../api/admin';
import type { TenantDirectoryEmployee } from '../../api/admin';
import type {
  MsspCockpit,
  MsspTenantWorkspace,
  MsspTenantWorkspaceConfiguration,
  TenantDirectoryReadiness,
  TenantAccessAssignmentInput,
  TenantAccessRole,
  TenantHierarchyLevel,
  TenantOrganizationUnit,
} from '../../types';
import { useAuth } from '../../hooks/useAuth';
import PlatformBrand from '../layout/PlatformBrand';

type View = 'structure' | 'roles' | 'rbac' | 'admin';

const SETUP_STEPS: Array<{ key: View; label: string; number: string }> = [
  { key: 'structure', label: 'Structure', number: '01' },
  { key: 'roles', label: 'Roles & dashboards', number: '02' },
  { key: 'admin', label: 'Administrator access', number: '03' },
  { key: 'rbac', label: 'RBAC roles', number: '04' },
];

const VIEW_LABELS: Record<View, string> = {
  structure: 'Structure',
  roles: 'Roles & dashboards',
  rbac: 'RBAC roles',
  admin: 'Administrator access',
};

type SetupStepState = {
  completed: View[];
  dirty: View[];
};

function rolesAreProvisioned(workspace: MsspTenantWorkspace): boolean {
  return workspace.roles.length > 0
    && workspace.roles.every((role) => (role.scope_level_keys ?? []).length > 0);
}

function firstIncompleteStep(workspace: MsspTenantWorkspace): View {
  if (!rolesAreProvisioned(workspace)) return 'roles';
  if (
    workspace.administration_model !== 'mssp_managed'
    && !workspace.assignments.some((assignment) => assignment.admin_access)
  ) return 'admin';
  return 'rbac';
}

function accessStatusLabel(status: MsspTenantWorkspace['assignments'][number]['access_status']): string {
  const labels = {
    active: 'Account active',
    account_disabled: 'Account disabled',
    pending_first_sign_in: 'Directory matched · pending first sign-in',
    identity_integration_required: 'Identity integration required',
  };
  return labels[status];
}

const STANDARD_ROLES: Array<{
  id: MsspCockpit['id'];
  name: string;
  description: string;
}> = [
  {
    id: 'exec',
    name: 'Executive',
    description: 'Provides executive, read-only oversight within the assigned tenant or organizational scope. Shows the fused risk score and 30-day trend; open findings and active alerts; application risk heatmap and highest-risk applications; severity distribution; POPIA and ISO 27001 readiness; and consolidated alert summaries across AppScan, Imperva WAF, database activity monitoring, and API Security. Supports CISO-level posture review and prioritization, not incident operations or account administration.',
  },
  {
    id: 'soc',
    name: 'SOC Analyst',
    description: 'Provides security-operations access within the assigned tenant or unit. Shows the unified live alert timeline and queue, active incidents, alert backlog and age, top alert rules, unified findings, MTTD/MTTR trends, and telemetry from AppScan, Imperva WAF/DAM, and API Security. Includes MITRE ATT&CK context (including relevant techniques such as T1190) and D3FEND response guidance for triage, investigation, escalation, and remediation follow-up. Does not grant tenant or user administration.',
  },
  {
    id: 'appsec',
    name: 'AppSec',
    description: 'Provides application and API security access within the assigned tenant or unit. Shows SAST/DAST findings by application and severity, critical vulnerabilities, OWASP Top 10 posture, CWE/CVE context, scan-source categories, exposed APIs, Imperva WAF block summaries, and 30-day fix-rate trends. Supports vulnerability triage, risk prioritization, and remediation tracking; it does not grant tenant or user administration.',
  },
  {
    id: 'dbsec',
    name: 'DB Security',
    description: 'Provides database-security visibility within the assigned tenant or unit. Shows database inventory and DAM coverage, active and critical violations, violation categories and age, and top applications/databases by alert volume. Includes database activity monitoring from supported Imperva/Thales sources, privileged-query and DDL monitoring, SQL-injection indicators, and sensitive datastore access telemetry for investigation and escalation. Does not grant tenant or user administration.',
  },
  {
    id: 'compliance',
    name: 'Compliance',
    description: 'Provides compliance and audit assurance for the assigned tenant or unit. Shows POPIA readiness, ISO 27001 status, open and overdue items, framework coverage, evidence status, regulatory calendar, and trends. Correlates audit records with application vulnerabilities and database violations, including POPIA s.22 notification and GDPR 72-hour reporting context. Supports evidence and control review; legal determinations and account administration remain outside this role.',
  },
  {
    id: 'sre',
    name: 'Service Ops',
    description: 'Provides platform and telemetry-health visibility within the authorized organizational scope. Shows connector and DAM-agent health, degraded sources, ingestion/event throughput, pipeline uptime, system health, connector throughput, error rates, and agent versions; supports monitoring of ingestion failures, dead-letter queues, and rate-limit conditions. Intended for service reliability troubleshooting, restoration, and escalation, not security incident ownership or tenant/user administration.',
  },
];

function slug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function nextSlug(value: string, existing: Set<string>): string {
  const base = slug(value) || 'unit';
  let candidate = base;
  let suffix = 2;
  while (existing.has(candidate)) candidate = `${base}-${suffix++}`;
  return candidate;
}

function apiErrorMessage(error: unknown, fallback: string): string {
  const response = (error as {
    response?: {
      status?: number;
      data?: { detail?: unknown };
    };
  })?.response;
  if (response?.status === 404) {
    return 'Tenant administration API is unavailable. Apply the database migration and restart the backend.';
  }
  const detail = response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && 'msg' in item) {
          return typeof item.msg === 'string' ? item.msg : '';
        }
        return '';
      })
      .filter(Boolean);
    if (messages.length) return messages.join('. ');
  }
  if (detail && typeof detail === 'object' && 'msg' in detail) {
    return typeof detail.msg === 'string' ? detail.msg : fallback;
  }
  return fallback;
}

function configurationOf(workspace: MsspTenantWorkspace): MsspTenantWorkspaceConfiguration {
  const legacyAdminRoleIds = new Set(
    workspace.roles.filter((role) => role.can_manage_members).map((role) => role.id),
  );
  return {
    root_label: workspace.root_label,
    administration_model: workspace.administration_model,
    hierarchy_levels: workspace.hierarchy_levels,
    org_units: workspace.org_units,
    roles: workspace.roles,
    assignments: workspace.assignments.map((assignment) => ({
      id: assignment.id,
      email: assignment.email,
      display_name: assignment.display_name,
      role_ids: assignment.role_ids,
      scope_unit_id: assignment.scope_unit_id,
      admin_access: assignment.admin_access ?? assignment.role_ids.some((roleId) => legacyAdminRoleIds.has(roleId)),
    })),
    status: workspace.status,
  };
}

function configurationForSave(
  configuration: MsspTenantWorkspaceConfiguration,
): MsspTenantWorkspaceConfiguration {
  return {
    root_label: configuration.root_label.trim(),
    administration_model: configuration.administration_model,
    hierarchy_levels: configuration.hierarchy_levels.map((tier) => ({
      key: tier.key,
      label: tier.label.trim(),
      parent_key: tier.parent_key ?? null,
    })),
    org_units: configuration.org_units.map((unit) => ({
      id: unit.id,
      name: unit.name.trim(),
      level_key: unit.level_key,
      parent_id: unit.parent_id ?? null,
    })),
    roles: configuration.roles.map((role) => ({
      id: role.id,
      name: role.name.trim(),
      description: role.description || '',
      cockpit_ids: role.cockpit_ids,
      scope_level_keys: role.scope_level_keys || [],
      can_manage_members: false,
    })),
    assignments: configuration.assignments.map((assignment) => ({
      id: assignment.id,
      email: assignment.email.trim(),
      display_name: assignment.display_name.trim(),
      role_ids: assignment.role_ids,
      scope_unit_id: assignment.scope_unit_id ?? null,
      admin_access: assignment.admin_access ?? false,
    })),
    status: configuration.status,
  };
}

const panelStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border-dim)',
  borderRadius: 14,
  padding: 20,
} as const;

export default function MsspTenantAdmin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');
  const [organizationName, setOrganizationName] = useState('');
  const [directoryReadiness, setDirectoryReadiness] = useState<TenantDirectoryReadiness | null>(null);
  const [workspaces, setWorkspaces] = useState<MsspTenantWorkspace[]>([]);
  const [tenantSearch, setTenantSearch] = useState('');
  const [dashboards, setCockpits] = useState<MsspCockpit[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [view, setView] = useState<View>('structure');
  const [setupStepState, setSetupStepState] = useState<Record<string, SetupStepState>>({});
  const [draft, setDraft] = useState<MsspTenantWorkspaceConfiguration | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    root_label: 'Organization',
  });
  const [newLevelLabel, setNewLevelLabel] = useState('');
  const [newLevelParent, setNewLevelParent] = useState('');
  const [newUnitName, setNewUnitName] = useState('');
  const [newUnitLevel, setNewUnitLevel] = useState('');
  const [newUnitParent, setNewUnitParent] = useState('');
  const [newRole, setNewRole] = useState({
    preset_id: '' as '' | 'custom' | MsspCockpit['id'],
    name: '',
    description: '',
    cockpit_ids: [] as MsspCockpit['id'][],
    scope_level_keys: [] as string[],
    can_manage_members: false,
  });
  const [newAssignment, setNewAssignment] = useState({ email: '', display_name: '', role_ids: [] as string[], scope_unit_id: '' });
  const [newAdminAssignment, setNewAdminAssignment] = useState({ email: '', display_name: '', scope_unit_id: '' });
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [directoryEmployees, setDirectoryEmployees] = useState<TenantDirectoryEmployee[]>([]);
  const [directoryName, setDirectoryName] = useState('');
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [directoryError, setDirectoryError] = useState('');
  const initialLoadStarted = useRef(false);
  const adminHeaderRef = useRef<HTMLElement | null>(null);
  const adminContentRef = useRef<HTMLElement | null>(null);

  const generatedTenantIdentifier = createForm.name.trim()
    ? nextSlug(createForm.name, new Set(workspaces.map((workspace) => workspace.identifier)))
    : '';
  const selected = useMemo(
    () => workspaces.find((workspace) => workspace.id === selectedId) ?? null,
    [workspaces, selectedId],
  );
  const visibleWorkspaces = useMemo(() => {
    const query = tenantSearch.trim().toLowerCase();
    return query
      ? workspaces.filter((workspace) =>
          `${workspace.name} ${workspace.identifier}`.toLowerCase().includes(query),
        )
      : workspaces;
  }, [tenantSearch, workspaces]);

  const currentStepState = selected ? setupStepState[selected.id] : undefined;
  const completedSteps = new Set<View>();
  if (selected) completedSteps.add('structure');
  if (selected && rolesAreProvisioned(selected)) completedSteps.add('roles');
  if (
    selected
    && rolesAreProvisioned(selected)
    && selected.assignments.some((assignment) => assignment.role_ids.length > 0)
  ) {
    completedSteps.add('rbac');
  }
  if (
    selected?.administration_model === 'mssp_managed'
    || selected?.assignments.some((assignment) => assignment.admin_access)
  ) {
    completedSteps.add('admin');
  }
  currentStepState?.completed.forEach((step) => completedSteps.add(step));
  currentStepState?.dirty.forEach((step) => completedSteps.delete(step));
  const nextStepIndex = SETUP_STEPS.findIndex((step) => !completedSteps.has(step.key));

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const workspaceResponse = await fetchMsspTenantWorkspaces();
      setOrganizationName(workspaceResponse.organization_name);
      setDirectoryReadiness(workspaceResponse.directory);
      const cockpitResponse = await fetchMsspCockpits();
      setWorkspaces(workspaceResponse.items);
      setCockpits(cockpitResponse.items);
      const currentWorkspace = workspaceResponse.items.find((workspace) => workspace.id === selectedId)
        ?? workspaceResponse.items[0];
      if (currentWorkspace) setView(firstIncompleteStep(currentWorkspace));
      setSelectedId((current) =>
        workspaceResponse.items.some((workspace) => workspace.id === current)
          ? current
          : workspaceResponse.items[0]?.id ?? '',
      );
    } catch (loadError: unknown) {
      setError(apiErrorMessage(
        loadError,
        'Could not load tenant administration. Check that the client profile is active and try again.',
      ));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialLoadStarted.current) return;
    initialLoadStarted.current = true;
    void load();
  }, []);

  useEffect(() => {
    const header = adminHeaderRef.current;
    const content = adminContentRef.current;
    if (!header || !content) return;

    const updateHeaderHeight = () => {
      content.style.setProperty('--client-admin-header-height', `${header.offsetHeight}px`);
    };
    const observer = new ResizeObserver(updateHeaderHeight);
    observer.observe(header);
    updateHeaderHeight();
    return () => {
      observer.disconnect();
      content.style.removeProperty('--client-admin-header-height');
    };
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timeoutId = window.setTimeout(() => setNotice(''), 3500);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  useEffect(() => {
    setDraft(selected ? configurationOf(selected) : null);
  }, [selected]);

  const patchDraft = (patch: Partial<MsspTenantWorkspaceConfiguration>) => {
    setDraft((current) => current ? { ...current, ...patch } : current);
    if (selected) {
      setSetupStepState((states) => {
        const current = states[selected.id] ?? { completed: [], dirty: [] };
        return {
          ...states,
          [selected.id]: {
            ...current,
            dirty: current.dirty.includes(view) ? current.dirty : [...current.dirty, view],
          },
        };
      });
    }
    setNotice('');
  };

  const toggleTheme = () => {
    const next = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    document.body.dataset.theme = next;
    localStorage.setItem('platform_theme', next);
    setIsDark(next === 'dark');
  };

  const renderSectionSave = (label: string, nextView?: View, blocked = false) => (
    <div className="client-tenant-form-actions">
      <button
        type="button"
        className="provider-create-button"
        onClick={() => void save(label, nextView)}
        disabled={saving || blocked}
      >
        {saving ? 'Saving…' : nextView ? `Save & continue to ${VIEW_LABELS[nextView]}` : `Save ${label}`}
      </button>
    </div>
  );

  const save = async (label?: string, nextView?: View) => {
    if (!selected || !draft) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await updateMsspTenantWorkspace(
        selected.id,
        configurationForSave(draft),
      );
      setWorkspaces((items) => items.map((item) => item.id === updated.id ? updated : item));
      setSetupStepState((states) => {
        const current = states[selected.id] ?? { completed: [], dirty: [] };
        return {
          ...states,
          [selected.id]: {
            completed: current.completed.includes(view) ? current.completed : [...current.completed, view],
            dirty: current.dirty.filter((step) => step !== view),
          },
        };
      });
      setNotice(`${label || 'Tenant configuration'} saved successfully.`);
      if (nextView) setView(nextView);
    } catch (saveError: unknown) {
      setError(apiErrorMessage(saveError, 'Could not save this tenant configuration.'));
    } finally {
      setSaving(false);
    }
  };

  const createWorkspace = async (event: FormEvent) => {
    event.preventDefault();
    const name = createForm.name.trim();
    if (!name) {
      setError('Enter a tenant name.');
      return;
    }

    setSaving(true);
    setError('');
    setNotice('');
    try {
      const workspace = await createMsspTenantWorkspace({
        identifier: nextSlug(name, new Set(workspaces.map((item) => item.identifier))),
        name,
        root_label: createForm.root_label.trim(),
        administration_model: 'mssp_managed',
        hierarchy_levels: [],
      });
      setWorkspaces((items) => [...items, workspace].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedId(workspace.id);
      setCreating(false);
      setView('structure');
      setCreateForm({ name: '', root_label: 'Organization' });
      setNotice('Tenant created. Add optional custom hierarchy tiers.');
    } catch (createError: unknown) {
      setError(apiErrorMessage(createError, 'Could not create this tenant.'));
    } finally {
      setSaving(false);
    }
  };

  const addHierarchyLevel = () => {
    if (!draft || !newLevelLabel.trim()) return;
    if (draft.hierarchy_levels.length > 0 && newLevelParent === '__multiple__') return;
    const key = nextSlug(newLevelLabel, new Set(draft.hierarchy_levels.map((level) => level.key)));
    const level: TenantHierarchyLevel = {
      key,
      label: newLevelLabel.trim(),
      parent_key: draft.hierarchy_levels.length === 0 ? null : (newLevelParent || null),
    };
    patchDraft({ hierarchy_levels: [...draft.hierarchy_levels, level] });
    setNewLevelLabel('');
    setNewLevelParent('');
  };

  const addOrganizationUnit = () => {
    if (!draft || !newUnitName.trim() || !newUnitLevel) return;
    const levelIndex = draft.hierarchy_levels.findIndex((level) => level.key === newUnitLevel);
    const parentId = levelIndex === 0 ? null : newUnitParent || null;
    if (levelIndex > 0 && !parentId) return;
    const unit: TenantOrganizationUnit = {
      id: nextSlug(newUnitName, new Set(draft.org_units.map((item) => item.id))),
      name: newUnitName.trim(),
      level_key: newUnitLevel,
      parent_id: parentId,
    };
    patchDraft({ org_units: [...draft.org_units, unit] });
    setNewUnitName('');
    if (levelIndex > 0) setNewUnitParent('');
  };

  const addRole = () => {
    if (!draft || !newRole.name.trim()) return;
    const scopeLevelKeys = newRole.scope_level_keys.length > 0
      ? newRole.scope_level_keys
      : (draft.hierarchy_levels.length === 0 ? ['root'] : []);
    const validScopeLevels = new Set(['root', ...draft.hierarchy_levels.map((level) => level.key)]);
    if (!scopeLevelKeys.length || scopeLevelKeys.some((key) => !validScopeLevels.has(key))) return;
    const role: TenantAccessRole = {
      id: nextSlug(newRole.name, new Set(draft.roles.map((item) => item.id))),
      name: newRole.name.trim(),
      description: newRole.description.trim(),
      cockpit_ids: newRole.cockpit_ids,
      scope_level_keys: scopeLevelKeys,
      can_manage_members: false,
    };
    patchDraft({ roles: [...draft.roles, role] });
    setNewRole({
      preset_id: '',
      name: '',
      description: '',
      cockpit_ids: [],
      scope_level_keys: draft.hierarchy_levels.length === 0 ? ['root'] : [],
      can_manage_members: false,
    });
  };

  const searchEmployees = async () => {
    if (!selected || employeeSearch.trim().length < 2) {
      setDirectoryError('Enter at least two characters to search the company directory.');
      return;
    }
    setDirectoryLoading(true);
    setDirectoryError('');
    setDirectoryEmployees([]);
    try {
      const result = await searchMsspWorkspaceEmployees(selected.id, employeeSearch.trim());
      setDirectoryEmployees(result.items);
      setDirectoryName(result.directory_name);
      if (result.items.length === 0) setDirectoryError('No matching employees with an email address were found.');
    } catch (searchError: unknown) {
      setDirectoryError(apiErrorMessage(searchError, 'Could not search the company directory.'));
    } finally {
      setDirectoryLoading(false);
    }
  };

  const addAssignment = () => {
    if (!draft || !newAssignment.email.trim() || !newAssignment.display_name.trim() || !newAssignment.role_ids.length) return;
    const email = newAssignment.email.trim().toLowerCase();
    const scope_unit_id = newAssignment.scope_unit_id || null;
    const existing = draft.assignments.find(
      (assignment) => assignment.email.toLowerCase() === email && assignment.scope_unit_id === scope_unit_id,
    );
    const assignments = existing
      ? draft.assignments.map((assignment) => assignment.id === existing.id
        ? { ...assignment, role_ids: Array.from(new Set([...assignment.role_ids, ...newAssignment.role_ids])) }
        : assignment)
      : [...draft.assignments, {
        id: crypto.randomUUID(),
        email,
        display_name: newAssignment.display_name.trim(),
        role_ids: newAssignment.role_ids,
        scope_unit_id,
        admin_access: false,
      }];
    patchDraft({ assignments });
    setNewAssignment((assignment) => ({ ...assignment, role_ids: [], scope_unit_id: '' }));
  };

  const addAdminAccess = () => {
    if (
      !draft
      || draft.administration_model === 'mssp_managed'
      || !newAdminAssignment.email.trim()
      || !newAdminAssignment.display_name.trim()
    ) return;
    const email = newAdminAssignment.email.trim().toLowerCase();
    const scope_unit_id = newAdminAssignment.scope_unit_id || null;
    const existing = draft.assignments.find(
      (assignment) => assignment.email.toLowerCase() === email && assignment.scope_unit_id === scope_unit_id,
    );
    const assignments = existing
      ? draft.assignments.map((assignment) => assignment.id === existing.id
        ? { ...assignment, admin_access: true }
        : assignment)
      : [...draft.assignments, {
        id: crypto.randomUUID(),
        email,
        display_name: newAdminAssignment.display_name.trim(),
        role_ids: [],
        scope_unit_id,
        admin_access: true,
      }];
    patchDraft({ assignments });
  };

  const removeUnit = (unitId: string) => {
    if (!draft) return;
    const hasChildren = draft.org_units.some((unit) => unit.parent_id === unitId);
    const hasAssignments = draft.assignments.some((assignment) => assignment.scope_unit_id === unitId);
    if (hasChildren || hasAssignments) return;
    patchDraft({ org_units: draft.org_units.filter((unit) => unit.id !== unitId) });
  };

  const renderStructure = () => {
    if (!draft) return null;
    const selectedLevelIndex = draft.hierarchy_levels.findIndex((level) => level.key === newUnitLevel);
    const parentLevel = draft.hierarchy_levels[selectedLevelIndex - 1];
    const parentOptions = parentLevel
      ? draft.org_units.filter((unit) => unit.level_key === parentLevel.key)
      : [];
    return (
      <div className="client-tenant-section-stack">
        <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Tiers</h3>
          <p className="client-tenant-help">
            Define reporting tiers and parent relationships. Tiers become scopes for role provisioning and access assignments.
          </p>
          {draft.hierarchy_levels.length === 0 ? (
            <p className="client-tenant-help">No tiers added. The tenant root remains a valid scope.</p>
          ) : (
            <ol className="client-tenant-item-list">
              {draft.hierarchy_levels.map((level, index) => (
                <li key={level.key} className="client-tenant-item-row client-tenant-hierarchy-row">
                  {index + 1}. <input
                    className="client-tenant-input"
                    aria-label={`${level.label} tier name`}
                    value={level.label}
                    onChange={(event) => patchDraft({
                      hierarchy_levels: draft.hierarchy_levels.map((item) => item.key === level.key ? { ...item, label: event.target.value } : item),
                    })}
                  />
                  <button
                    type="button"
                    disabled={
                      draft.hierarchy_levels.some((item) => item.parent_key === level.key)
                      || draft.org_units.some((unit) => unit.level_key === level.key)
                      || draft.roles.some((role) => role.scope_level_keys?.includes(level.key))
                    }
                    onClick={() => patchDraft({
                      hierarchy_levels: draft.hierarchy_levels.filter((item) => item.key !== level.key),
                    })}
                  >
                    Remove tier
                  </button>
                  {draft.org_units.some((unit) => unit.level_key === level.key) && (
                    <span className="client-tenant-item-meta">
                      {draft.org_units.filter((unit) => unit.level_key === level.key).length} configured
                    </span>
                  )}
                  {draft.roles.some((role) => role.scope_level_keys?.includes(level.key)) && (
                    <span className="client-tenant-item-meta">Dashboard roles are assigned to this tier</span>
                  )}
                </li>
              ))}
            </ol>
          )}
          <div className="client-tenant-inline-form">
            <input className="client-tenant-input" aria-label="Hierarchy tier name" placeholder="Tier name (e.g. Branch)" value={newLevelLabel} onChange={(event) => setNewLevelLabel(event.target.value)} />
            {draft.hierarchy_levels.length > 0 && (
              <select
                className="client-tenant-input"
                aria-label="Parent hierarchy tier"
                value={newLevelParent}
                onChange={(event) => setNewLevelParent(event.target.value)}
              >
                <option value="">Under {organizationName || 'organization'} (top tier)</option>
                {draft.hierarchy_levels.map((level) => (
                  <option key={level.key} value={level.key}>Under {level.label}</option>
                ))}
              </select>
            )}
            <button type="button" className="provider-create-button" onClick={addHierarchyLevel} disabled={!newLevelLabel.trim()}>Add tier</button>
          </div>
        </section>
        {draft.hierarchy_levels.length > 0 && (
          <section className="client-tenant-panel" style={panelStyle}>
            <h3 style={{ marginTop: 0 }}>Hierarchy preview</h3>
            <div className="client-hierarchy-schematic" aria-label="Organization hierarchy diagram">
              <div className="client-hierarchy-node client-hierarchy-client">
                <strong>{organizationName || 'Organization'}</strong>
              </div>
              <div className="client-hierarchy-down-connector" aria-hidden="true" />
              {(() => {
                const depths = new Map<string, number>();
                draft.hierarchy_levels.forEach((level, index) => {
                  if (level.parent_key) {
                    const parentDepth = depths.get(level.parent_key);
                    depths.set(level.key, parentDepth !== undefined ? parentDepth + 1 : index);
                  } else if (index > 0) {
                    const previous = draft.hierarchy_levels[index - 1];
                    const previousDepth = depths.get(previous.key) ?? 0;
                    depths.set(level.key, previousDepth + 1);
                  } else {
                    depths.set(level.key, 0);
                  }
                });
                const maxDepth = Math.max(0, ...Array.from(depths.values()));
                return (
                  <div className="client-hierarchy-tree">
                    {Array.from({ length: maxDepth + 1 }, (_, depth) => (
                      <div className="client-hierarchy-depth" key={depth}>
                        {depth > 0 && <div className="client-hierarchy-down-connector" aria-hidden="true" />}
                        <div className="client-hierarchy-row">
                          {draft.hierarchy_levels
                            .filter((level) => (depths.get(level.key) ?? 0) === depth)
                            .map((level) => (
                              <div
                                className={`client-hierarchy-node ${depth === 0 ? 'client-hierarchy-top-tier' : ''}`}
                                key={level.key}
                              >
                                <span className="client-hierarchy-node-label">
                                  {depth === 0 ? 'Top tier' : `Tier ${depth + 1}`}
                                </span>
                                <strong>{level.label}</strong>
                                {level.parent_key && (
                                  <span className="client-tenant-item-meta">
                                    Under {draft.hierarchy_levels.find((item) => item.key === level.parent_key)?.label || organizationName || draft.root_label}
                                  </span>
                                )}
                              </div>
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>
          </section>
        )}
        <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Administration model</h3>
          <label className="client-tenant-field" style={{ maxWidth: 480 }}>
            Who manages tenant users?
            <select
              className="client-tenant-input"
              value={draft.administration_model}
              onChange={(event) => {
                const administration_model = event.target.value as MsspTenantWorkspaceConfiguration['administration_model'];
                patchDraft({ administration_model });
              }}
            >
              <option value="mssp_managed">
                {organizationName ? `${organizationName} manages all users and access` : 'Current company manages all users and access'}
              </option>
              <option value="delegated">
                {selected ? `Delegate scoped administration to ${selected.name} users` : 'Delegate scoped administration to tenant users'}
              </option>
              <option value="shared">
                {organizationName && selected
                  ? `Shared: ${organizationName} retains oversight; ${selected.name} users manage assigned scopes`
                  : 'Shared company oversight with tenant users managing assigned scopes'}
              </option>
            </select>
          </label>
          <p className="client-tenant-help">
            {draft.administration_model === 'mssp_managed'
              ? 'The company manages all users. Dashboard access can still be scoped to individual organizational units.'
              : draft.administration_model === 'delegated'
                ? 'Tenant users granted administrator access can manage members within their assigned scope.'
                : `${organizationName || 'The company'} retains full oversight while ${selected?.name || 'tenant'} users granted administrator access manage members only within their assigned scopes.`}
          </p>
        </section>
        {renderSectionSave('Structure', 'roles')}
      </div>
    );
  };

  const renderRoles = () => {
    if (!draft) return null;
    const duplicateRoleName = draft.roles.some(
      (role) => role.name.toLocaleLowerCase() === newRole.name.trim().toLocaleLowerCase(),
    );
    const provisioningLevels = [
      { key: 'root', label: `Tenant root (${draft.root_label})` },
      ...draft.hierarchy_levels.map((level, index) => ({
        key: level.key,
        label: `${index === 0 ? 'Top tier' : `Tier ${index + 1}`} — ${level.label}`,
      })),
    ];
    const validProvisioningLevels = new Set(provisioningLevels.map((level) => level.key));
    const validProvisioningLevel = newRole.scope_level_keys.length > 0
      && newRole.scope_level_keys.every((key) => validProvisioningLevels.has(key));
    return (
      <div className="client-tenant-section-stack">
        <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Create a role</h3>
          <div className="client-tenant-form-fields">
            <label>
              Role
              <select
                className="client-tenant-input"
                aria-label="Role type"
                value={newRole.preset_id}
                onChange={(event) => {
                  const presetId = event.target.value as '' | 'custom' | MsspCockpit['id'];
                  const preset = STANDARD_ROLES.find((role) => role.id === presetId);
                  setNewRole({
                    preset_id: presetId,
                    name: preset?.name || '',
                    description: preset?.description || '',
                    cockpit_ids: preset ? [preset.id] : [],
                    scope_level_keys: draft.hierarchy_levels.length === 0 ? ['root'] : [],
                    can_manage_members: false,
                  });
                }}
              >
                <option value="">Select a standard role or create a custom role</option>
                {STANDARD_ROLES.map((role) => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
                <option value="custom">Custom role</option>
              </select>
            </label>
            {newRole.preset_id !== '' && (
              <>
                <label>
                  Role name
                  <input
                    className="client-tenant-input"
                    aria-label="Role name"
                    placeholder="Role name"
                    value={newRole.name}
                    readOnly={newRole.preset_id !== 'custom'}
                    onChange={(event) => setNewRole((role) => ({ ...role, name: event.target.value }))}
                  />
                </label>
                <fieldset className="client-tenant-fieldset client-tenant-field-full">
                  <legend>Provisioning tiers for this tenant</legend>
                  {provisioningLevels.map((level) => (
                    <label key={level.key} className="client-tenant-checkbox">
                      <input
                        type="checkbox"
                        checked={newRole.scope_level_keys.includes(level.key)}
                        onChange={(event) => setNewRole((role) => ({
                          ...role,
                          scope_level_keys: event.target.checked
                            ? [...role.scope_level_keys, level.key]
                            : role.scope_level_keys.filter((key) => key !== level.key),
                        }))}
                      />
                      {level.label}
                    </label>
                  ))}
                  <small>
                    Select one or multiple tiers where this role may be provisioned.
                  </small>
                </fieldset>
                <label className="client-tenant-field-full">
                  Role description
                  <textarea
                    className="client-tenant-input"
                    aria-label="Role description"
                    placeholder="Describe this role"
                    value={newRole.description}
                    readOnly={newRole.preset_id !== 'custom'}
                    onChange={(event) => setNewRole((role) => ({ ...role, description: event.target.value }))}
                    rows={5}
                  />
                  {newRole.preset_id !== 'custom' && <small>Standard description and dashboard access are set by the selected role.</small>}
                </label>
              </>
            )}
            <fieldset className="client-tenant-fieldset client-tenant-field-full">
              <legend>{newRole.preset_id === 'custom' ? 'Dashboard access' : 'Standard dashboard access'}</legend>
              {newRole.preset_id === 'custom' ? dashboards.map((dashboard) => (
                <label key={dashboard.id} className="client-tenant-checkbox">
                  <input
                    type="checkbox"
                    checked={newRole.cockpit_ids.includes(dashboard.id)}
                    onChange={(event) => setNewRole((role) => ({
                      ...role,
                      cockpit_ids: event.target.checked
                        ? [...role.cockpit_ids, dashboard.id]
                        : role.cockpit_ids.filter((id) => id !== dashboard.id),
                    }))}
                  /> {dashboard.name}
                </label>
              )) : newRole.preset_id ? (
                <span className="client-tenant-item-meta">
                  {STANDARD_ROLES.find((role) => role.id === newRole.preset_id)?.name}
                </span>
              ) : (
                <span className="client-tenant-item-meta">Select a role to view its dashboard access.</span>
              )}
            </fieldset>
            <button
              className="provider-create-button"
              type="button"
              onClick={addRole}
              disabled={
                !newRole.name.trim()
                || duplicateRoleName
                || !newRole.preset_id
                || !validProvisioningLevel
              }
            >
              Add role
            </button>
            {duplicateRoleName && <span className="client-tenant-help">A role with this name already exists.</span>}
          </div>
        </section>
        <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Configured roles</h3>
          {draft.roles.length === 0 ? <p className="client-tenant-empty-note">No custom roles yet.</p> : (
            <div className="client-tenant-item-list">
              {draft.roles.map((role) => (
                <article key={role.id} className="client-tenant-item-card">
                  <div className="client-tenant-item-heading">
                    <strong>{role.name}</strong>
                    <button
                      type="button"
                      className="provider-secondary-button"
                      onClick={() => {
                        if (draft.assignments.some((assignment) => assignment.role_ids.includes(role.id))) return;
                        patchDraft({ roles: draft.roles.filter((item) => item.id !== role.id) });
                      }}
                      disabled={draft.assignments.some((assignment) => assignment.role_ids.includes(role.id))}
                    >
                      Remove role
                    </button>
                  </div>
                  {role.description && <p>{role.description}</p>}
                  <div className="client-tenant-item-meta">
                    {role.cockpit_ids.map((id) => (
                      STANDARD_ROLES.find((preset) => preset.id === id)?.name
                      || dashboards.find((dashboard) => dashboard.id === id)?.name
                      || id
                    )).join(' · ') || 'No dashboard access'}
                  </div>
                  <div className="client-tenant-item-meta">
                    Provisioning levels in tenant structure: {(role.scope_level_keys || []).map((key) => (
                      key === 'root' ? draft.root_label : draft.hierarchy_levels.find((level) => level.key === key)?.label || key
                    )).join(' · ') || 'Not assigned'}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
        <div className="client-tenant-info-note" style={panelStyle}>
          Role definitions select from the platform’s six supported dashboards; they do not create arbitrary platform permissions.
        </div>
        {renderSectionSave('Roles & dashboards', 'admin')}
      </div>
    );
  };

  const renderEmployeePicker = (grantType: 'rbac' | 'admin') => {
    const assignment = grantType === 'admin' ? newAdminAssignment : newAssignment;
    const setEmployee = (email: string, display_name: string) => {
      if (grantType === 'admin') {
        setNewAdminAssignment({ email, display_name, scope_unit_id: '' });
      } else {
        setNewAssignment({ email, display_name, role_ids: [], scope_unit_id: '' });
      }
      setDirectoryError('');
    };
    const clearEmployee = () => {
      if (grantType === 'admin') {
        setNewAdminAssignment({ email: '', display_name: '', scope_unit_id: '' });
      } else {
        setNewAssignment({ email: '', display_name: '', role_ids: [], scope_unit_id: '' });
      }
    };
    const accessType = grantType === 'admin' ? 'administrator access' : 'RBAC roles';
    return (
      <section className="client-tenant-panel" style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Select an employee for {accessType}</h3>
        <p className="client-tenant-help">
          Search the company directory and choose the employee who will receive {accessType}.
        </p>
        <div className="client-tenant-form-fields">
          <label className="client-tenant-field client-tenant-field-full">
            Find an employee in {organizationName || 'the company'}’s directory
            <div className="client-tenant-inline-form">
              <input
                className="client-tenant-input"
                aria-label={`Search company directory for ${accessType}`}
                placeholder="Search name, username, or email"
                value={employeeSearch}
                onChange={(event) => setEmployeeSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    void searchEmployees();
                  }
                }}
              />
              <button
                type="button"
                className="provider-secondary-button"
                onClick={() => void searchEmployees()}
                disabled={directoryLoading || employeeSearch.trim().length < 2}
              >
                {directoryLoading ? 'Searching…' : 'Search directory'}
              </button>
            </div>
          </label>
          {directoryName && <span className="client-tenant-item-meta">Directory: {directoryName}</span>}
          {directoryError && <p className="client-tenant-alert client-tenant-alert-error" role="alert">{directoryError}</p>}
          {directoryEmployees.length > 0 && (
            <label className="client-tenant-field client-tenant-field-full">
              Select employee
              <select
                className="client-tenant-input"
                value={assignment.email}
                onChange={(event) => {
                  const employee = directoryEmployees.find((item) => item.email === event.target.value);
                  setEmployee(employee?.email || '', employee?.display_name || '');
                }}
              >
                <option value="">Select an employee from the directory</option>
                {directoryEmployees.map((employee) => (
                  <option key={`${employee.username}:${employee.email}`} value={employee.email}>
                    {employee.display_name} — {employee.email} ({employee.position || employee.username})
                  </option>
                ))}
              </select>
            </label>
          )}
          {assignment.email && (
            <div className="client-tenant-item-meta client-tenant-field-full">
              Selected: {assignment.display_name} · {assignment.email}
              <button type="button" className="provider-secondary-button" onClick={clearEmployee}>
                Clear selection
              </button>
            </div>
          )}
        </div>
      </section>
    );
  };

  const renderAccess = () => {
    if (!draft) return null;
    const selectedRoles = draft.roles.filter((role) => newAssignment.role_ids.includes(role.id));
    const selectedRoleScopeKeys = selectedRoles.length > 0
      ? selectedRoles.reduce<string[]>(
          (common, role) =>
            common.filter((key) => (role.scope_level_keys || []).includes(key)),
          selectedRoles[0].scope_level_keys || [],
        )
      : [];
    const provisionableScopeLevels: Array<{ key: string; label: string }> = [];
    if (selectedRoleScopeKeys.includes('root')) {
      provisionableScopeLevels.push({ key: 'root', label: 'Entire tenant' });
    }
    draft.hierarchy_levels
      .filter((level) => selectedRoleScopeKeys.includes(level.key))
      .forEach((level) => provisionableScopeLevels.push({
        key: level.key,
        label: `All ${level.plural_label || `${level.label}s`}`,
      }));
    const adminScopeLevels = [
      { key: 'root', label: 'Entire tenant' },
      ...draft.hierarchy_levels.map((level) => ({
        key: level.key,
        label: `All ${level.plural_label || `${level.label}s`}`,
      })),
    ];
    const administratorAccessAllowed = draft.administration_model !== 'mssp_managed';
    const adminAssignments = draft.assignments.filter((assignment) => assignment.admin_access);
    const rbacAssignments = draft.assignments.filter((assignment) => assignment.role_ids.length > 0);
    const scopeLabel = (scopeUnitId: string | null) => {
      if (!scopeUnitId) return 'Entire tenant';
      const level = draft.hierarchy_levels.find((item) => item.key === scopeUnitId);
      return level ? `All ${level.plural_label || `${level.label}s`}` : 'Unavailable tier';
    };
    const identityStatusLabel = (email: string) => {
      const current = selected?.assignments.find(
        (assignment) => assignment.email.toLowerCase() === email.toLowerCase(),
      );
      if (current) return accessStatusLabel(current.access_status);
      return accessStatusLabel(
        directoryReadiness?.status === 'enabled'
          ? 'pending_first_sign_in'
          : 'identity_integration_required',
      );
    };
    const removeAdminGrant = (assignmentId: string) => {
      patchDraft({
        assignments: draft.assignments.flatMap((assignment) => {
          if (assignment.id !== assignmentId) return [assignment];
          return assignment.role_ids.length ? [{ ...assignment, admin_access: false }] : [];
        }),
      });
    };
    const removeRbacGrant = (assignmentId: string) => {
      patchDraft({
        assignments: draft.assignments.flatMap((assignment) => {
          if (assignment.id !== assignmentId) return [assignment];
          return assignment.admin_access ? [{ ...assignment, role_ids: [] }] : [];
        }),
      });
    };
    const selectedAdminScope = newAdminAssignment.scope_unit_id || null;
    const alreadyGrantedAdminAccess = draft.assignments.some(
      (assignment) => assignment.admin_access
        && assignment.email.toLowerCase() === newAdminAssignment.email.toLowerCase()
        && assignment.scope_unit_id === selectedAdminScope,
    );
    return (
      <div className="client-tenant-section-stack">
        {renderEmployeePicker(view === 'admin' ? 'admin' : 'rbac')}

        {view === 'admin' && <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Grant administrator access</h3>
          <p className="client-tenant-help">
            Grants member-management rights at the selected scope only. It does not grant dashboard roles.
          </p>
          {!administratorAccessAllowed && (
            <p className="client-tenant-help">
              Administrator access is retained by {organizationName || 'the organization'} in MSSP-managed mode. Select delegated or shared administration to grant scoped access.
            </p>
          )}
          <div className="client-tenant-form-fields">
            <label className="client-tenant-field client-tenant-field-full">
              Administrator scope
              <select
                className="client-tenant-input"
                value={newAdminAssignment.scope_unit_id}
                onChange={(event) => setNewAdminAssignment((assignment) => ({
                  ...assignment,
                  scope_unit_id: event.target.value,
                }))}
                disabled={!administratorAccessAllowed}
              >
                {adminScopeLevels.map((level) => (
                  <option key={level.key} value={level.key === 'root' ? '' : level.key}>{level.label}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="provider-create-button client-tenant-field-full"
              onClick={addAdminAccess}
              disabled={
                !administratorAccessAllowed
                || !newAdminAssignment.email.trim()
                || alreadyGrantedAdminAccess
              }
            >
              {alreadyGrantedAdminAccess ? 'Administrator access granted' : 'Grant administrator access'}
            </button>
          </div>
          {adminAssignments.length === 0 ? <p className="client-tenant-empty-note">No administrator access granted.</p> : (
            <ul className="client-tenant-item-list">
              {adminAssignments.map((assignment) => (
                <li key={`admin-${assignment.id}`} className="client-tenant-item-card">
                  <div className="client-tenant-item-heading">
                    <strong>{assignment.display_name}</strong>
                    <button type="button" className="provider-secondary-button" onClick={() => removeAdminGrant(assignment.id)}>
                      Remove administrator access
                    </button>
                  </div>
                  <div className="client-tenant-item-meta">{assignment.email}</div>
                  <div>{scopeLabel(assignment.scope_unit_id)}</div>
                  <span className="client-tenant-status">{identityStatusLabel(assignment.email)}</span>
                </li>
              ))}
            </ul>
          )}
          {administratorAccessAllowed && adminAssignments.length === 0 && (
            <p className="client-tenant-help">Grant at least one administrator before continuing to RBAC roles.</p>
          )}
        </section>}

        {view === 'rbac' && <section className="client-tenant-panel" style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Grant RBAC roles</h3>
          <p className="client-tenant-help">
            Grants dashboard roles at a permitted tier only. It does not grant administrator access.
          </p>
          {draft.roles.length === 0 ? (
            <p className="client-tenant-empty-note">Create dashboard roles in Roles &amp; dashboards before assigning RBAC access.</p>
          ) : (
            <div className="client-tenant-form-fields">
              <fieldset className="client-tenant-fieldset client-tenant-field-full">
                <legend>Dashboard roles</legend>
                {draft.roles.map((role) => (
                  <label key={role.id} className="client-tenant-checkbox">
                    <input
                      type="checkbox"
                      checked={newAssignment.role_ids.includes(role.id)}
                      onChange={(event) => setNewAssignment((assignment) => {
                        const roleIds = event.target.checked
                          ? [...assignment.role_ids, role.id]
                          : assignment.role_ids.filter((id) => id !== role.id);
                        const roles = draft.roles.filter((item) => roleIds.includes(item.id));
                        const common = roles.length
                          ? roles.reduce<string[]>(
                              (keys, item) => keys.filter((key) => (item.scope_level_keys || []).includes(key)),
                              roles[0].scope_level_keys || [],
                            )
                          : [];
                        const nextScope = common[0] === 'root' ? '' : (common[0] || '');
                        return { ...assignment, role_ids: roleIds, scope_unit_id: nextScope };
                      })}
                    />
                    {role.name}
                    <span className="client-tenant-item-meta">
                      {(role.scope_level_keys || []).map((key) =>
                        key === 'root'
                          ? organizationName || draft.root_label
                          : draft.hierarchy_levels.find((level) => level.key === key)?.label || key
                      ).join(' · ') || 'No provisioning tiers'}
                    </span>
                  </label>
                ))}
              </fieldset>
              <label className="client-tenant-field client-tenant-field-full">
                RBAC scope
                <select
                  className="client-tenant-input"
                  value={newAssignment.scope_unit_id}
                  disabled={selectedRoles.length === 0 || provisionableScopeLevels.length === 0}
                  onChange={(event) => {
                    const scope_unit_id = event.target.value;
                    const levelKey = scope_unit_id || 'root';
                    setNewAssignment((assignment) => ({
                      ...assignment,
                      scope_unit_id,
                      role_ids: assignment.role_ids.filter((roleId) => {
                        const role = draft.roles.find((item) => item.id === roleId);
                        return Boolean(levelKey && role?.scope_level_keys?.includes(levelKey));
                      }),
                    }));
                  }}
                >
                  {provisionableScopeLevels.length === 0 ? (
                    <option value="" disabled>Select roles with configured tiers</option>
                  ) : (
                    provisionableScopeLevels.map((level) => (
                      <option key={level.key} value={level.key === 'root' ? '' : level.key}>{level.label}</option>
                    ))
                  )}
                </select>
              </label>
              <button
                className="provider-create-button client-tenant-field-full"
                type="button"
                onClick={addAssignment}
                disabled={!newAssignment.email.trim() || !newAssignment.role_ids.length}
              >
                Grant RBAC roles
              </button>
            </div>
          )}
          {rbacAssignments.length === 0 ? <p className="client-tenant-empty-note">No RBAC role assignments yet.</p> : (
            <ul className="client-tenant-item-list">
              {rbacAssignments.map((assignment) => {
                const names = assignment.role_ids.map((id) => draft.roles.find((role) => role.id === id)?.name || id);
                return (
                  <li key={assignment.id} className="client-tenant-item-card">
                    <div className="client-tenant-item-heading">
                      <strong>{assignment.display_name}</strong>
                      <button type="button" className="provider-secondary-button" onClick={() => removeRbacGrant(assignment.id)}>
                        Remove RBAC roles
                      </button>
                    </div>
                    <div className="client-tenant-item-meta">{assignment.email}</div>
                    <div>{names.join(', ')} · {scopeLabel(assignment.scope_unit_id)}</div>
                    <span className="client-tenant-status">{identityStatusLabel(assignment.email)}</span>
                  </li>
                );
              })}
            </ul>
          )}
          {rbacAssignments.length === 0 && (
            <p className="client-tenant-help">Grant at least one RBAC role before saving this stage.</p>
          )}
          <p className="client-tenant-help">
            Directory-matched accounts are created on their first successful sign-in when the directory is enabled. Grants apply to all units in the selected tier.
          </p>
        </section>}
        {view === 'admin'
          ? renderSectionSave(
              'Administrator access',
              'rbac',
              administratorAccessAllowed && adminAssignments.length === 0,
            )
          : renderSectionSave('RBAC roles', undefined, rbacAssignments.length === 0)}
      </div>
    );
  };

  return (
    <>
      <header ref={adminHeaderRef} className="platform-header client-admin-topbar">
        <div className="client-admin-brand">
          <PlatformBrand />
          <span className="client-admin-organization">{organizationName || (loading ? 'Loading organization…' : 'Organization')}</span>
        </div>
        <div className="client-admin-page-heading">
          <h1>Tenant Access Management Portal</h1>
          <p>Define the hierarchy, configure dashboard roles, grant administrator access, then assign RBAC roles.</p>
        </div>
        <div className="client-admin-account">
          <span>{user?.email}</span>
          <button
            type="button"
            className="theme-toggle"
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            onClick={toggleTheme}
          >
            {isDark ? '☀ Light' : '🌙 Dark'}
          </button>
          <button type="button" className="provider-secondary-button" onClick={() => { logout(); navigate('/login'); }}>Sign out</button>
        </div>
      </header>
      <main ref={adminContentRef} className="client-tenant-admin">
        <div className="provider-admin-layout client-tenant-workspace-layout">
          <aside className="provider-admin-sidebar client-tenant-workspace-sidebar" aria-label="Tenant setup navigation">
            <div className="client-tenant-sidebar-group">
              <div className="provider-admin-sidebar-label">Tenants</div>
              {workspaces.length > 4 && (
                <input
                  className="client-tenant-input client-tenant-search"
                  aria-label="Search tenants"
                  placeholder="Search tenants"
                  value={tenantSearch}
                  onChange={(event) => setTenantSearch(event.target.value)}
                />
              )}
              {visibleWorkspaces.length === 0 ? (
                <p className="client-tenant-empty-note">No matching tenants.</p>
              ) : visibleWorkspaces.map((workspace) => (
                <button
                  className="client-tenant-list-item"
                  key={workspace.id}
                  type="button"
                  onClick={() => {
                    setSelectedId(workspace.id);
                    setCreating(false);
                    setView(firstIncompleteStep(workspace));
                    setNewAssignment({ email: '', display_name: '', role_ids: [], scope_unit_id: '' });
                    setNewAdminAssignment({ email: '', display_name: '', scope_unit_id: '' });
                    setDirectoryEmployees([]);
                    setDirectoryName('');
                    setDirectoryError('');
                    setEmployeeSearch('');
                  }}
                  aria-pressed={workspace.id === selectedId}
                >
                  {workspace.name}
                </button>
              ))}
              <button
                type="button"
                className="provider-secondary-button client-tenant-sidebar-create"
                onClick={() => { setCreating(true); setView('structure'); }}
                disabled={loading}
              >
                + Create tenant
              </button>
            </div>
          </aside>

          <section className="provider-admin-content client-tenant-workspace-main">
            {selected && !creating && directoryReadiness && (
              <p className="client-tenant-directory-readiness">
                Directory {directoryReadiness.status.replace('_', ' ')}
                {directoryReadiness.name ? ` · ${directoryReadiness.name}` : ''}
                {directoryReadiness.status === 'enabled'
                  ? ' · Users are provisioned on first successful sign-in.'
                  : ' · Employee lookup and directory sign-in are unavailable.'}
              </p>
            )}
            {selected && !creating && (
              <ol className="client-tenant-setup-progress" aria-label="Tenant setup progress">
                {SETUP_STEPS.map((step, index) => {
                  const isComplete = completedSteps.has(step.key);
                  const isCurrent = view === step.key;
                  const isNext = index === nextStepIndex;
                  const isDisabled = !isComplete && index > nextStepIndex;
                  const stepStatus = isComplete
                    ? 'Completed'
                    : isCurrent
                      ? 'In progress'
                      : isNext
                        ? 'Next'
                        : 'Upcoming';
                  return (
                    <li
                      key={step.key}
                      className={[
                        'client-tenant-setup-step',
                        isComplete && 'is-complete',
                        isCurrent && 'is-current',
                      ].filter(Boolean).join(' ')}
                    >
                      <button
                        type="button"
                        className="client-tenant-setup-step-button"
                        aria-current={isCurrent ? 'step' : undefined}
                        aria-label={`${step.number} ${step.label}: ${stepStatus}`}
                        disabled={isDisabled}
                        onClick={() => setView(step.key)}
                      >
                        <span className="client-tenant-setup-step-number" aria-hidden="true">
                          {isComplete ? '✓' : step.number}
                        </span>
                        <span className="client-tenant-setup-step-details">
                          <span className="client-tenant-setup-step-label">{step.label}</span>
                          <span className="client-tenant-setup-step-status">{stepStatus}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
            )}
            {error && (
              <div className="client-tenant-alert client-tenant-alert-error" role="alert">
                <span>{error}</span>
                <button type="button" className="provider-secondary-button" onClick={() => void load()}>Retry</button>
              </div>
            )}
            {notice && <div className="client-tenant-alert client-tenant-alert-success" role="status">{notice}</div>}

            {loading && <div className="client-tenant-panel" style={panelStyle}>Loading tenant configuration…</div>}
            {!loading && !error && creating && (
              <form onSubmit={createWorkspace} className="client-tenant-form" style={panelStyle}>
                <header className="client-tenant-form-header">
                  <span className="client-tenant-eyebrow">New tenant</span>
                  <h2>Create tenant</h2>
                </header>
                <div className="client-tenant-form-fields">
                  <label>
                    Tenant name
                    <input
                      className="client-tenant-input"
                      required
                      minLength={2}
                      autoFocus
                      placeholder="e.g. Example Organization"
                      value={createForm.name}
                      onChange={(event) => setCreateForm((form) => ({ ...form, name: event.target.value }))}
                    />
                  </label>
                  <label>
                    Tenant identifier
                    <input
                      className="client-tenant-input"
                      readOnly
                      placeholder="Generated from tenant name"
                      value={generatedTenantIdentifier}
                    />
                    <small>Generated automatically from the tenant name.</small>
                  </label>
                  <label className="client-tenant-field-full">
                    Tenant label
                    <input
                      className="client-tenant-input"
                      required
                      value={createForm.root_label}
                      onChange={(event) => setCreateForm((form) => ({ ...form, root_label: event.target.value }))}
                    />
                  </label>
                </div>
                <div className="client-tenant-form-actions">
                  <button type="button" className="provider-secondary-button" onClick={() => setCreating(false)}>Cancel</button>
                  <button type="submit" className="provider-create-button" disabled={saving}>
                    {saving ? 'Creating…' : 'Create tenant'}
                  </button>
                </div>
              </form>
            )}
            {!loading && !error && !creating && selected && draft && (
              <>
                <section className="client-tenant-selected-header" style={panelStyle}>
                  <div className="client-tenant-selected-summary">
                    <span className="provider-sidebar-kicker">Selected tenant</span>
                    <h2>{selected.name}</h2>
                    <span>
                      {selected.identifier} · {draft.hierarchy_levels.length} tiers · {draft.roles.length} roles · {draft.assignments.length} assignments
                    </span>
                  </div>
                </section>
                {view === 'structure' && renderStructure()}
                {view === 'roles' && renderRoles()}
                {(view === 'rbac' || view === 'admin') && renderAccess()}
              </>
            )}
            {!loading && !error && !creating && !selected && (
              <section className="client-tenant-empty-state">
                <span className="client-tenant-empty-icon" aria-hidden="true">+</span>
                <div>
                  <div className="client-tenant-eyebrow">Getting started</div>
                  <h2>Set up your first tenant</h2>
                  <p>Create a tenant, define its reporting tiers, configure dashboard roles, grant administrator access, then assign RBAC roles to directory employees.</p>
                </div>
                <button type="button" className="provider-create-button client-tenant-create-button" onClick={() => setCreating(true)}>
                  Create tenant
                </button>
              </section>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
