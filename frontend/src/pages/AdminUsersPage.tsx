import { useEffect, useRef, useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Chip from '../components/dashboard/Chip';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import {
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  AdminUser,
  fetchPersons,
  PersonRecord,
  lookupExternalHR,
  ExternalHRIdentity,
} from '../api/admin';
import { fetchTenancy, TenancyDepartment } from '../api/auth';
import type { Tone } from '../data/mappers';
import type { TenancyTier } from '../types';

// Per-tier grantable role restrictions (what a superadmin at each tier may assign)
const TIER_GRANTABLE_ROLES: Record<TenancyTier, string[]> = {
  sita:     ['admin', 'operator', 'transversal-admin', 'exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'dept-admin', 'branch-admin', 'province-dept-admin', 'province-soc-lead', 'local-appsec'],
  national: ['transversal-admin', 'dept-admin', 'province-dept-admin', 'province-soc-lead', 'exec', 'compliance', 'sre', 'branch-admin', 'soc', 'appsec', 'dbsec', 'local-appsec'],
  dept:     ['branch-admin', 'soc', 'appsec', 'dbsec', 'local-appsec'],
  branch:   ['local-appsec', 'soc', 'appsec', 'dbsec'],
};

const TIER_TITLES: Record<TenancyTier, { title: string; subtitle: string; badge: string }> = {
  sita: {
    title: 'SITA Command Center — Transversal Superadmin #1 (Control Plane)',
    subtitle: 'Tier 4 Control Plane · SITA Superadmin created by Platform Developers · Primary client contact · Transversal ICT provider provisioning National Gov Transversal Superadmin (#2) and National Data Plane Cockpits',
    badge: 'tier-4-control-plane',
  },
  national: {
    title: 'National Security Estate — National Gov Transversal Superadmin #2 (Control Plane)',
    subtitle: 'Tier 3 Control Plane · Created by SITA Superadmin #1 · Sovereign Transversal Oversight across National & Provincial Departments · Provisions Department Superadmins (Tier 2)',
    badge: 'tier-3-control-plane',
  },
  dept: {
    title: 'Department Superadmin — Home Affairs Testbed (Tier 2 Control Plane)',
    subtitle: 'Tier 2 Control Plane · Created by National Gov Transversal Superadmin #2 · Provisions Branch Admins and DHA Security Specialists strictly within its Home Affairs PFMA tenancy',
    badge: 'tier-2-control-plane',
  },
  branch: {
    title: 'Branch Admin — DDG Operational Branch (Tier 1 Control Plane)',
    subtitle: 'Tier 1 Control Plane · Created by DHA Department Superadmin · Provisions Operational Security Specialists (AppSec, SOC, DBSec) strictly within its branch scope',
    badge: 'tier-1-control-plane',
  },
};

const DEPARTMENT_ROLES = new Set(['soc', 'appsec', 'dbsec', 'dept-admin', 'branch-admin', 'province-soc-lead', 'province-dept-admin', 'local-appsec']);
const PROVINCIAL_ROLES = new Set(['province-soc-lead', 'province-dept-admin', 'local-appsec']);
const BRANCH_REQUIRED_ROLES = new Set(['branch-admin']);

// Mirrors backend GRANTABLE_ROLES: roles each tier may grant. The cascade is
// SITA (operator) -> SITA Superadmin (admin) -> Transversal Superadmin -> Dept Admin (DHA) -> Branch Admin (DDG) -> Ops.
const GRANTABLE_ROLES: Record<string, string[]> = {
  'operator': ['admin', 'operator'],
  'admin': ['transversal-admin', 'dept-admin', 'branch-admin', 'exec', 'compliance', 'sre', 'soc', 'appsec', 'dbsec', 'province-dept-admin', 'province-soc-lead', 'local-appsec'],
  'transversal-admin': ['dept-admin', 'branch-admin', 'transversal-admin', 'exec', 'compliance', 'sre', 'soc', 'appsec', 'dbsec', 'province-dept-admin', 'province-soc-lead', 'local-appsec'],
  'dept-admin': ['branch-admin', 'soc', 'appsec', 'dbsec', 'local-appsec'],
  'deptadmin-ha': ['branch-admin', 'soc', 'appsec', 'dbsec', 'local-appsec'],
  'province-dept-admin': ['branch-admin', 'soc', 'appsec', 'dbsec', 'local-appsec'],
  'branch-admin': ['local-appsec', 'soc', 'appsec', 'dbsec'],
  'branchadmin-ha': ['local-appsec', 'soc', 'appsec', 'dbsec'],
  'sre': ['soc', 'appsec', 'dbsec', 'province-soc-lead', 'local-appsec'],
};

const ROLE_DISPLAY_INFO: Record<string, { label: string; tierLabel: string }> = {
  'admin':               { label: 'SITA Platform Superadmin',       tierLabel: 'Tier 4 · SITA Command Center' },
  'operator':            { label: 'Platform Provider Root',         tierLabel: 'Tier 4 · SITA Command Center' },
  'transversal-admin':   { label: 'Transversal Superadmin',         tierLabel: 'Tier 3 · National Estate' },
  'exec':                { label: 'National Executive',             tierLabel: 'Tier 3 · National Estate' },
  'compliance':          { label: 'Compliance & AG Officer',        tierLabel: 'Tier 3 · National Estate' },
  'sre':                 { label: 'Service Reliability Engineer',   tierLabel: 'Tier 3 · National Estate' },
  'dept-admin':          { label: 'Department Superadmin',          tierLabel: 'Tier 2 · Department' },
  'province-dept-admin': { label: 'Provincial Department Admin',    tierLabel: 'Tier 2 · Provincial' },
  'province-soc-lead':   { label: 'Provincial SOC Lead',            tierLabel: 'Tier 2 · Provincial' },
  'branch-admin':        { label: 'Branch Superadmin',              tierLabel: 'Tier 1 · Branch' },
  'local-appsec':        { label: 'Branch AppSec Specialist',       tierLabel: 'Tier 1 · Branch' },
  'soc':                 { label: 'SOC Security Analyst',           tierLabel: 'Operational' },
  'appsec':              { label: 'AppSec Engineer',                tierLabel: 'Operational' },
  'dbsec':               { label: 'Database Security Specialist',   tierLabel: 'Operational' },
};

const ROLE_TONE: Record<string, Tone> = {
  exec: 'severe',
  soc: 'med',
  appsec: 'high',
  dbsec: 'ok',
  compliance: 'closed',
  sre: 'half',
  admin: 'severe',
  operator: 'severe',
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
  person_id: string;
  identifier_scheme: string;
  identifier_value: string;
  external_label?: string;
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
  person_id: '',
  identifier_scheme: '',
  identifier_value: '',
  external_label: '',
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

export default function AdminUsersPage({ adminTier = 'national' }: { adminTier?: TenancyTier }) {
  const tierMeta = TIER_TITLES[adminTier];
  const tierGrantable = TIER_GRANTABLE_ROLES[adminTier];
  const { user: me } = useAuth();
  const users = useApi(() => fetchUsers());
  const tenancy = useApi(() => fetchTenancy());
  const [modal, setModal] = useState<Modal>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [personResults, setPersonResults] = useState<PersonRecord[]>([]);
  const [personSearch, setPersonSearch] = useState('');
  const [personLoading, setPersonLoading] = useState(false);
  const personSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // External Authoritative HR System Integration (SITA SAP HCM & National Treasury PERSAL)
  const [externalSystem, setExternalSystem] = useState<'sita' | 'persal'>('persal');
  const [externalQuery, setExternalQuery] = useState('');
  const [externalResults, setExternalResults] = useState<ExternalHRIdentity[]>([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [showExternalHr, setShowExternalHr] = useState(true);
  const externalTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runPersonSearch = async (q: string) => {
    setPersonLoading(true);
    try {
      const res = await fetchPersons(q || undefined);
      setPersonResults(res.items || []);
    } catch {
      setPersonResults([]);
    } finally {
      setPersonLoading(false);
    }
  };

  const runExternalLookup = async (sys: 'sita' | 'persal', q: string) => {
    setExternalLoading(true);
    try {
      const res = await lookupExternalHR(sys, undefined, q || undefined);
      setExternalResults(res.items || []);
    } catch {
      setExternalResults([]);
    } finally {
      setExternalLoading(false);
    }
  };

  const onExternalQueryChange = (val: string, sys = externalSystem) => {
    setExternalQuery(val);
    if (externalTimer.current) clearTimeout(externalTimer.current);
    externalTimer.current = setTimeout(() => runExternalLookup(sys, val), 250);
  };

  const switchExternalSystem = (sys: 'sita' | 'persal') => {
    setExternalSystem(sys);
    setExternalQuery('');
    runExternalLookup(sys, '');
  };

  useEffect(() => {
    runPersonSearch('');
    const defaultSys = adminTier === 'sita' ? 'sita' : 'persal';
    setExternalSystem(defaultSys);
    runExternalLookup(defaultSys, '');
    return () => {
      if (personSearchTimer.current) clearTimeout(personSearchTimer.current);
      if (externalTimer.current) clearTimeout(externalTimer.current);
    };
  }, [adminTier]);

  const selectedPerson = personResults.find((p) => p.id === form.person_id);

  const items = users.data?.items || [];
  const departments: TenancyDepartment[] = tenancy.data?.departments || [];
  const counts = tenancy.data?.counts;

  const myDepts = me?.department_ids || [];
  const myBranches = me?.branch_ids || [];
  const myProvinces = me?.province_ids || [];
  const isSystemAdmin = me?.roles?.some((r) => ['admin', 'operator', 'transversal-admin'].includes(r));
  const isScopedAdmin = !isSystemAdmin && (me?.roles?.some((r) => ['dept-admin', 'branch-admin', 'province-dept-admin', 'deptadmin-ha', 'branchadmin-ha'].includes(r)) || myDepts.length > 0);

  // ── Tier-aware tenancy scoping ─────────────────────────────────────────────
  // adminTier drives which departments and branches appear in the Create User form and user table.
  //   sita             → Tier 4 SITA Command Center: Platform Superadmin (#1) delegating to Transversal #2
  //   national         → Tier 3 National Estate: Sovereign Transversal Superadmin (#2) delegating to Dept Admins
  //   dept             → Tier 2 Department: Locked to Home Affairs tenancy; provisions Branch Admins & DHA roles
  //   branch           → Tier 1 Branch: Locked to specific DDG branch; provisions operational specialists

  // Target department for Tier 2/1 (Home Affairs testbed)
  const targetDeptId = myDepts.length > 0 ? myDepts[0] : 'home-affairs-digital';
  const targetBranchId = myBranches.length > 0 ? myBranches[0] : 'dha-immigration';

  // National departments: filter out provincial sub-departments (eastern-cape-*, etc.)
  const nationalDepts = departments.filter((d) =>
    !d.id.startsWith('eastern-cape-') &&
    !d.id.startsWith('free-state-') &&
    !d.id.startsWith('gauteng-') &&
    !d.id.startsWith('kwazulu-natal-') &&
    !d.id.startsWith('limpopo-') &&
    !d.id.startsWith('mpumalanga-') &&
    !d.id.startsWith('north-west-') &&
    !d.id.startsWith('northern-cape-') &&
    !d.id.startsWith('western-cape-')
  );

  // Pickable departments according to tier
  const pickable: TenancyDepartment[] = (() => {
    if (adminTier === 'dept' || adminTier === 'branch') {
      const match = departments.filter((d) => d.id === targetDeptId);
      return match.length > 0 ? match : departments.filter((d) => d.id === 'home-affairs-digital');
    }
    return nationalDepts;
  })();

  const deptIsLocked = adminTier === 'dept' || adminTier === 'branch';
  const branchIsLocked = adminTier === 'branch';
  const showProvinces = adminTier === 'sita' || adminTier === 'national';

  const provinces = tenancy.data?.provinces || [];
  const pickableProvinces = isScopedAdmin
    ? provinces.filter((p) => myProvinces.length === 0 || myProvinces.includes(p.id))
    : provinces;

  const pickableBranches = (d: TenancyDepartment) => {
    if (branchIsLocked) {
      return d.branches.filter((b) => b.id === targetBranchId);
    }
    if (isScopedAdmin && myBranches.length > 0 && myDepts.includes(d.id)) {
      return d.branches.filter((b) => myBranches.includes(b.id));
    }
    return d.branches;
  };

  // Intersection of what the logged-in user's own role grants AND what this tier allows
  const grantableOptions = Array.from(new Set(
    (me?.roles || []).flatMap((r) => GRANTABLE_ROLES[r] || [])
  )).filter((r) => tierGrantable.includes(r));

  const branchMap = new Map<string, BranchRef>();
  departments.forEach((d) => {
    d.branches.forEach((b) => branchMap.set(b.id, { name: b.name, department_id: d.id }));
  });

  const deptName = (id?: string | null) => departments.find((d) => d.id === id)?.name || '—';
  const provinceName = (id?: string | null) => provinces.find((p) => p.id === id)?.name || '—';
  const branchName = (id: string) => branchMap.get(id)?.name || '—';

  // Filter user list to align with the tier's tenancy boundary
  const filteredItems = items.filter((u) => {
    if (adminTier === 'dept') {
      const uDepts = u.department_ids || [];
      if (!uDepts.includes(targetDeptId)) return false;
      if (u.roles.some((r) => ['operator', 'admin', 'transversal-admin'].includes(r))) return false;
      return true;
    }
    if (adminTier === 'branch') {
      const uDepts = u.department_ids || [];
      const uBranches = u.branch_ids || [];
      if (!uDepts.includes(targetDeptId)) return false;
      if (uBranches.length > 0 && !uBranches.includes(targetBranchId)) return false;
      if (u.roles.some((r) => ['operator', 'admin', 'transversal-admin', 'dept-admin'].includes(r))) return false;
      return true;
    }
    if (adminTier === 'national') {
      if (u.roles.includes('operator')) return false;
      if (u.roles.includes('admin') && (!u.department_ids || u.department_ids.length === 0)) return false;
      return true;
    }
    if (adminTier === 'sita') {
      return true;
    }
    return true;
  });

  const branchGroups = pickable.filter((d) => form.department_ids.includes(d.id));

  const openCreate = () => {
    // Pre-fill department_ids and branch_ids when tier is scoped (dept/branch admin)
    const prefilledDepts = deptIsLocked ? [targetDeptId] : [];
    const prefilledBranches = branchIsLocked ? [targetBranchId] : [];
    setForm({
      ...EMPTY_FORM,
      department_ids: prefilledDepts,
      branch_ids: prefilledBranches,
    });
    setError('');
    setPersonSearch('');
    const defaultSys = adminTier === 'sita' ? 'sita' : 'persal';
    setExternalSystem(defaultSys);
    setExternalQuery('');
    setShowExternalHr(true);
    runExternalLookup(defaultSys, '');
    runPersonSearch('');
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
      person_id: user.person_id || '',
      identifier_scheme: '',
      identifier_value: '',
      external_label: '',
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

  const selectPerson = (p: PersonRecord) => {
    const inPick = pickable.some((d) => d.id === p.department_id);
    setForm((f) => ({
      ...f,
      person_id: p.id,
      identifier_scheme: '',
      identifier_value: '',
      external_label: '',
      email: p.email || f.email,
      display_name: p.display_name || f.display_name,
      department_ids: deptIsLocked
        ? f.department_ids
        : (inPick && p.department_id ? [p.department_id] : f.department_ids),
    }));
  };

  const selectExternalIdentity = (item: ExternalHRIdentity) => {
    const inPick = pickable.some((d) => d.id === item.department_id);
    const resolvedDisplayName = item.display_name || (item.surname ? `${item.initials ? item.initials + ' ' : ''}${item.surname}`.trim() : '');
    setForm((f) => ({
      ...f,
      person_id: '',
      identifier_scheme: item.scheme,
      identifier_value: item.employee_code,
      external_label: `${resolvedDisplayName || item.surname} (${item.employee_code} · ${item.source_system})`,
      email: item.email || f.email,
      display_name: resolvedDisplayName || f.display_name,
      department_ids: deptIsLocked
        ? f.department_ids
        : (inPick && item.department_id ? [item.department_id] : f.department_ids),
      branch_ids: branchIsLocked
        ? f.branch_ids
        : (item.branch_id ? [item.branch_id] : f.branch_ids),
    }));
  };

  const onPersonSearchChange = (value: string) => {
    setPersonSearch(value);
    if (personSearchTimer.current) clearTimeout(personSearchTimer.current);
    personSearchTimer.current = setTimeout(() => runPersonSearch(value), 300);
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
    if (!form.email || !form.email.includes('@')) {
      setError('Please provide a valid email address.');
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
          person_id: form.person_id || undefined,
          identifier_scheme: form.identifier_scheme || undefined,
          identifier_value: form.identifier_value || undefined,
        });
        setNotice(`Successfully provisioned ${form.email} with role(s) [${form.roles.join(', ')}]`);
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
        title={tierMeta.title}
        subtitle={
          adminTier === 'dept'
            ? `${tierMeta.subtitle} — Department of Home Affairs · ${pickable[0]?.branches.length || 8} operational branches`
            : adminTier === 'branch'
            ? `${tierMeta.subtitle} — DHA Immigration Services · Operational Branch Scope`
            : adminTier === 'national'
            ? `${tierMeta.subtitle} — Sovereign Estate: ${counts?.departments || 173} Organs of State (National & Provincial Departments across 9 Provincial Administrations)`
            : `${tierMeta.subtitle} — Transversal Mandate: ${counts?.departments || 173} Organs of State across National & Provincial Administrations`
        }
        badge={{ label: tierMeta.badge, color: 'var(--violet)', bg: 'var(--violet-dim)' }}
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
                {filteredItems.length ? filteredItems.map((u) => (
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
            {modal.mode === 'create' && (
              <div style={{
                background: 'rgba(99, 102, 241, 0.08)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: 8,
                padding: '12px 14px',
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 10
              }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    ⚡ Real-Time Demo Assistant · {tierMeta.title.split('—')[0].trim()}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {adminTier === 'sita' && 'Auto-fill National Gov Transversal Superadmin #2 credentials (sovereign estate oversight)'}
                    {adminTier === 'national' && 'Auto-fill Department Superadmin (Tier 2) credentials for Department of Home Affairs'}
                    {adminTier === 'dept' && 'Auto-fill Branch Admin (Tier 1) credentials for DHA Immigration Services Branch'}
                    {adminTier === 'branch' && 'Auto-fill Branch AppSec Specialist credentials for operational security enforcement'}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-flare"
                  style={{ fontSize: 12, padding: '6px 14px', height: 'auto' }}
                  onClick={() => {
                    if (adminTier === 'sita') {
                      // Tier 4: SITA Command Center provisions National Gov Transversal Superadmin #2
                      setForm({
                        email: 'transversal.superadmin@gov.za',
                        display_name: 'Nomvula Mokonyane',
                        password: 'Password123!',
                        roles: ['transversal-admin'],
                        department_ids: [],
                        branch_ids: [],
                        province_ids: [],
                        person_id: '',
                        identifier_scheme: 'persal',
                        identifier_value: '80124901',
                        external_label: 'Nomvula Mokonyane (80124901 · PERSAL Master)',
                        is_active: true,
                      });
                      setError('');
                    } else if (adminTier === 'national') {
                      // Tier 3: Sovereign National Transversal Superadmin #2 provisions Department Superadmin (Tier 2)
                      setForm({
                        email: 'dha.superadmin@dha.gov.za',
                        display_name: 'Lindiwe Mazibuko',
                        password: 'Password123!',
                        roles: ['dept-admin'],
                        department_ids: ['home-affairs-digital'],
                        branch_ids: [],
                        province_ids: [],
                        person_id: '',
                        identifier_scheme: 'persal',
                        identifier_value: '80491024',
                        external_label: 'Lindiwe Mazibuko (80491024 · PERSAL Master)',
                        is_active: true,
                      });
                      setError('');
                    } else if (adminTier === 'dept') {
                      // Tier 2: DHA Department Superadmin provisions Branch Admin (Tier 1)
                      setForm({
                        email: 'dha.immigration.admin@dha.gov.za',
                        display_name: 'Nkosinathi Dlamini',
                        password: 'Password123!',
                        roles: ['branch-admin'],
                        department_ids: ['home-affairs-digital'],
                        branch_ids: ['dha-immigration'],
                        province_ids: [],
                        person_id: '',
                        identifier_scheme: 'persal',
                        identifier_value: '80512891',
                        external_label: 'Nkosinathi Dlamini (80512891 · PERSAL Master)',
                        is_active: true,
                      });
                      setError('');
                    } else if (adminTier === 'branch') {
                      // Tier 1: DHA Branch Admin provisions Branch Security Specialists (Data Plane)
                      setForm({
                        email: 'dha.immigration.appsec@dha.gov.za',
                        display_name: 'Willem Botha',
                        password: 'Password123!',
                        roles: ['local-appsec'],
                        department_ids: ['home-affairs-digital'],
                        branch_ids: ['dha-immigration'],
                        province_ids: [],
                        person_id: '',
                        identifier_scheme: 'persal',
                        identifier_value: '80621430',
                        external_label: 'Willem Botha (80621430 · PERSAL Master)',
                        is_active: true,
                      });
                      setError('');
                    }
                  }}
                >
                  ⚡ Auto-Fill Demo Credentials
                </button>
              </div>
            )}

            {modal.mode === 'create' && (
              <div style={{
                background: 'var(--panel-header-bg)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                padding: '12px 14px',
                marginBottom: 16
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span>🔗 Authoritative External HR Integration</span>
                    <span style={{ fontSize: 10, background: 'rgba(34,197,94,0.15)', color: '#4ade80', padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
                      POPIA s.10/13 Minimized
                    </span>
                  </div>
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', fontSize: 11, textDecoration: 'underline' }}
                    onClick={() => setShowExternalHr(!showExternalHr)}
                  >
                    {showExternalHr ? 'Hide Gateway' : 'Show Gateway'}
                  </button>
                </div>

                {form.external_label || form.identifier_value ? (
                  <div style={{ fontSize: 12, color: 'var(--ok)', background: 'rgba(34,197,94,0.08)', padding: '8px 12px', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <strong>Linked HR Identity:</strong> {form.external_label || `${form.identifier_scheme}:${form.identifier_value}`}
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        ✓ Upstream HR verified. Sensitive master fields (national ID number, salary notch, address) are strictly excluded under POPIA.
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setForm(f => ({ ...f, identifier_scheme: '', identifier_value: '', external_label: '', person_id: '' }))}
                      style={{ background: 'none', border: 'none', color: 'var(--amber)', cursor: 'pointer', fontSize: 11, textDecoration: 'underline', padding: 0 }}
                    >
                      [Change Link]
                    </button>
                  </div>
                ) : showExternalHr && (
                  <div>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                      <button
                        type="button"
                        className={`btn ${externalSystem === 'sita' ? 'btn-primary' : 'btn-ghost'}`}
                        style={{ fontSize: 11, padding: '4px 10px', height: 'auto' }}
                        onClick={() => switchExternalSystem('sita')}
                      >
                        🏢 SITA Employee System (SAP HCM)
                      </button>
                      <button
                        type="button"
                        className={`btn ${externalSystem === 'persal' ? 'btn-primary' : 'btn-ghost'}`}
                        style={{ fontSize: 11, padding: '4px 10px', height: 'auto' }}
                        onClick={() => switchExternalSystem('persal')}
                      >
                        🏛️ National Treasury PERSAL
                      </button>
                    </div>

                    <input
                      type="search"
                      className="form-input"
                      style={{ fontSize: 12, padding: '6px 10px' }}
                      value={externalQuery}
                      onChange={(e) => onExternalQueryChange(e.target.value)}
                      placeholder={externalSystem === 'sita'
                        ? 'Search SITA SAP HCM by code (SIT-00101) or surname (Mthembu, Govender)...'
                        : 'Search PERSAL by 8-digit number (80491024) or surname (Mazibuko, Botha)...'}
                    />

                    {externalLoading && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                        Querying authoritative {externalSystem === 'sita' ? 'SITA SAP HCM Gateway' : 'National Treasury PERSAL API'}...
                      </div>
                    )}

                    <div className="person-list" style={{ maxHeight: 140, overflowY: 'auto', marginTop: 6 }}>
                      {externalResults.map((item) => {
                        const isSelected = form.identifier_value === item.employee_code && form.identifier_scheme === item.scheme;
                        const name = item.display_name || `${item.initials ? item.initials + ' ' : ''}${item.surname}`;
                        return (
                          <button
                            key={`${item.scheme}-${item.employee_code}`}
                            type="button"
                            className={`person-option${isSelected ? ' selected' : ''}`}
                            onClick={() => selectExternalIdentity(item)}
                          >
                            <span className="person-option-name">
                              {isSelected ? '✓ ' : ''}{name}
                            </span>
                            <span className="person-meta">
                              {[item.employee_code, item.position, item.source_system].filter(Boolean).join(' · ')}
                            </span>
                            {item.email && <span className="person-meta">{item.email}</span>}
                          </button>
                        );
                      })}
                      {externalResults.length === 0 && !externalLoading && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '6px 8px' }}>
                          No matches found in {externalSystem === 'sita' ? 'SITA Employee Master' : 'PERSAL Master'}.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="form-field">
              <label className="form-label" htmlFor="uemail">Email address</label>
              <input
                type="email"
                id="uemail"
                className="form-input"
                value={form.email}
                disabled={modal.mode !== 'create'}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="e.g. user@dha.gov.za"
              />
              <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                {modal.mode === 'create'
                  ? 'Official government/SITA email bound to authoritative personnel records above.'
                  : 'Updating account credentials and tenancy permissions.'}
              </div>
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
              <span className="form-label">Roles &amp; Superadmin Entitlements (Cascaded from {tierMeta.title.split('—')[0].trim()})</span>
              <div className="role-check-list">
                {grantableOptions.map((role) => {
                  const checked = form.roles.includes(role);
                  const info = ROLE_DISPLAY_INFO[role];
                  return (
                    <button
                      key={role}
                      type="button"
                      className={`role-check${checked ? ' checked' : ''}`}
                      onClick={() => toggleRole(role)}
                      title={info ? `${info.label} (${info.tierLabel})` : role}
                    >
                      <span className="role-check-box">{checked ? '✓' : ''}</span>
                      <span style={{ fontWeight: 600 }}>{role}</span>
                      {info && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>
                          — {info.label} <small style={{ opacity: 0.85, color: 'var(--accent)' }}>[{info.tierLabel}]</small>
                        </span>
                      )}
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
            {/* ── Province picker: sita/national tier only ──────────────────────────── */}
            {showProvinces && (
              <div className="form-field">
                <span className="form-label">Provincial Administrations (Scopes to the 113 Provincial Line Departments)</span>
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
                        <span className="scope-count">{p.department_count} depts</span>
                      </button>
                    );
                  }) : (
                    <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                      Loading provincial hierarchy…
                    </div>
                  )}
                </div>
                <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                  Province scope delegates authority across all 113 Provincial Line Departments within the selected Provincial Administrations.
                  Required for <strong>province-soc-lead</strong> / <strong>province-dept-admin</strong> / <strong>local-appsec</strong> roles.
                </div>
              </div>
            )}

            {/* ── Department picker: locked at dept/branch tier, open at sita/national ─ */}
            <div className="form-field">
              {deptIsLocked ? (
                /* Dept/Branch tier: department is fixed to the admin's tenancy node */
                <>
                  <span className="form-label">Tenant Scope — Department (PFMA Accounting Entity)</span>
                  <div style={{
                    background: 'rgba(99,102,241,0.08)',
                    border: '1px solid rgba(99,102,241,0.25)',
                    borderRadius: 8,
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                  }}>
                    <span style={{ fontSize: 16 }}>🏢</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {pickable.map((d) => d.name).join(', ') || deptName(myDepts[0])}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        🔒 Locked to your tenancy — new users will be scoped to this department only.
                        This cannot be changed at {adminTier === 'dept' ? 'Department' : 'Branch'} Admin tier.
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                /* Sita/National tier: choose from national departments */
                <>
                  <span className="form-label">National Departments (~60 National Organs of State)</span>
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
                          <span className="scope-count">{d.branch_count} branches</span>
                        </button>
                      );
                    }) : (
                      <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                        Loading national hierarchy…
                      </div>
                    )}
                  </div>
                  <div className="form-hint" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                    Empty selection = Whole National Estate (all National &amp; Provincial Departments).
                    <strong>soc / appsec / dbsec / dept-admin / branch-admin</strong> must select at least one department.
                  </div>
                </>
              )}
            </div>
            {branchIsLocked ? (
              <div className="form-field">
                <span className="form-label">Tenant Scope — Branch</span>
                <div style={{
                  background: 'rgba(99,102,241,0.08)',
                  border: '1px solid rgba(99,102,241,0.25)',
                  borderRadius: 8,
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}>
                  <span style={{ fontSize: 16 }}>📍</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                      {branchName(targetBranchId)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                      🔒 Locked to your branch tenancy — operational specialists will be scoped to this branch only.
                      This cannot be changed at Branch Admin tier.
                    </div>
                  </div>
                </div>
              </div>
            ) : branchGroups.length > 0 && (
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
